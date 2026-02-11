from django.shortcuts import render
from rest_framework import viewsets, filters, permissions, status, generics,mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from rest_framework.throttling import ScopedRateThrottle
from .serializers import (
    ProductsSerializer,
    CartItemSerializer,
    OrderSerializer,
    UserRegisterSerializer,
    ReviewSerializer,
    CartAddSerializer,
    CheckoutSerializer,
    CategorySerializer,
    UserProfileSerializer,
    TelegramLoginSerializer,
    SetPasswordSerializer,
    CartGetSerializer
)
from .models import CustomUser, Product, Cart, CartItem, Order, OrderItem, Review, Category
from .filters import ProductFilter,CategoryFilter, ReviewFilter
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from .permissions import IsAdminOrReadOnly, IsOwnerOrReadOnly
import random
import requests
from django.core.cache import cache
from django.conf import settings
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()




class CategoryViewSet(mixins.ListModelMixin, GenericViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_class = CategoryFilter 
    pagination_class = None
    search_fields = ['name', 'slug']


    def get_queryset(self):
        queryset =  Category.objects.all().prefetch_related('child')

        search_query = self.request.query_params.get('search', None)
        parent_id = self.request.query_params.get('parent_id', None)

        if search_query or parent_id:
            return queryset 
        
        return queryset.filter(parent__isnull=True)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related("category")
    serializer_class = ProductsSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [
        filters.SearchFilter,
        DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    search_fields = ["name"]
    filterset_class = ProductFilter 
    ordering_fields = ["price", "name",]
    ordering = ["-price"]
    http_method_names = ['get']


class CartViewSet(GenericViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartGetSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=["get"])
    def my_cart(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(cart)
        cart_qs = Cart.objects.filter(id=cart.id).prefetch_related('items__product').first()
        serializer = CartGetSerializer(cart_qs)
        return Response(serializer.data)

    
    @extend_schema(request=CartAddSerializer)
    @action(detail=False, methods=["post"])
    def add(self, request):
        serializer = CartAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data["product_id"]
        quantity = serializer.validated_data["quantity"]

        product = get_object_or_404(Product, id=product_id)

        cart, _ = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product
        )

        new_quantity = quantity if created else cart_item.quantity + quantity

        if product.stock < new_quantity:
            return Response(
                {"error": "bazadan bunsha product joq"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_item.quantity = new_quantity
        cart_item.save()

        return Response(
            {"success": "Product sebetke qosildi"},
            status=status.HTTP_201_CREATED
        )

    
class CartItemsViewSet(mixins.ListModelMixin,mixins.DestroyModelMixin, mixins.UpdateModelMixin, GenericViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'delete', 'patch']

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)
    
    def perform_update(self, serializer):
        cart_item = self.get_object()
        product = cart_item.product

        new_quantity = serializer.validated_data.get('quantity')

        if new_quantity:

            if product.stock < new_quantity:
                raise ValidationError(
                    {"quantity": f"Bazada jetkiliksiz"}
                )
            
            if new_quantity < 1:
                raise ValidationError({"quantity": "Sani 1 den kem bolmawi kerek."})

        serializer.save()
    
   


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('orderitems__product')
    

    @extend_schema(request=CheckoutSerializer, responses=OrderSerializer)
    @action(detail=False, methods=["post"])
    def checkout(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)   

        user = request.user
        address = serializer.validated_data["address"]
        cart_item_ids = serializer.validated_data.get("cart_items")

        cart = get_object_or_404(Cart, user=user)


        with transaction.atomic():

            if cart_item_ids:
                cart_items = cart.items.select_related('product').select_for_update(of=('product',)).filter(id__in=cart_item_ids)

                if cart_items.count() != len(cart_item_ids):
                    return Response(
                    {"error": "Ayirim onimler tabilmadi yamasa sizge tiyisli emes"},
                    status=status.HTTP_400_BAD_REQUEST)
            
            else:
                cart_items = cart.items.select_related('product').select_for_update(of=('product',)).all()
                
            if not cart_items.exists():
                    return Response({"error": "Sebet bos!"}, status=400)    

            total_price = 0

            for item in cart_items:
                if item.product.stock < item.quantity:
                    return Response(
                        {
                            "error": f"{item.product.name} Onim bazada jetkiliksiz"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                total_price += item.get_total_price()

            order = Order.objects.create(
                user=user, total_price=total_price, status="kutilmekte", address=address
            )

            for item in cart_items:

                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.get_active_price(),
                )
                item.product.stock -= item.quantity
                item.product.save()

            cart_items.delete()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None,responses=OrderSerializer)
    @action(detail=True,methods=['post'])
    def pay(self,request, pk=None):
        order = self.get_object()

        if order.status != 'kutilmekte':
            return Response({'error': 'Bul buyirtpa ushin tolem qiliw mumkin emes(yamasa tolenip bolingan buytirpa)'}, status=status.HTTP_400_BAD_REQUEST)
        
        order.status = 'tolendi'
        order.save()

        return Response({
            "order_id": order.id,
            "status": order.status,
            "message": "Tolem tabisli tolendi!"
        }, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch']

    def get_object(self):
        return self.request.user


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReviewFilter 
    http_method_names = ['get', 'post', 'patch','delete']

    def perform_create(self, serializer):
        user = self.request.user
        product_id = self.request.data.get("product")

        product = get_object_or_404(Product, id=product_id)
        statuslar = ["tolendi", "jiberildi"]
        satip_alingan = OrderItem.objects.filter(
            order__user=user, product=product, order__status__in=statuslar
        ).exists()

        if not satip_alingan:
            raise ValidationError("Siz bul onimdi satip almagansiz yaki ele tolem qilmagansiz")

        serializer.save(user=user, product=product)




#Telegram bot API
class TelegramWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'telegram_webhook  '

    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        try:
            update = request.data
            
            if "message" in update:
                message = update["message"]
                chat_id = message["chat"]["id"]
                
                # 1. TEXT XABARLAR
                if "text" in message:
                    text = message["text"]
                    
                    if text == "/start":
                        self.send_contact_request(chat_id)
                    
                    # Login komandasi yamasa Knopka
                    elif text == "/login" or text == "🔐 Kiriw kodın alıw":
                        self.handle_login_request(chat_id)

                # 2. CONTACT
                elif "contact" in message:
                    self.handle_contact(message, chat_id)
            
            return Response({"status": "ok"})
        except Exception as e:
            print(f"Telegram Error: {e}")
            return Response({"status": "ok"})

    # --- RATE LIMIT LOGIKASI ---

    def check_rate_limit(self, chat_id):
        """
        Eger user sońǵı 3 minutta kod alǵan bolsa True qaytaradı.
        """
        is_limited = cache.get(f"rate_limit_{chat_id}")
        if is_limited:
            self.send_message(chat_id, "⚠️ Siz aldınǵı kodtı jaqında aldıńız.\nIltimas, 3 minut kútiń.")
            return True
        return False

    def set_rate_limit(self, chat_id):
        """
        Userdi 3 minutqa (180 sekund) bloklaw
        """
        cache.set(f"rate_limit_{chat_id}", "true", timeout=180)

    # --- REQUEST HANDLERS ---

    def handle_login_request(self, chat_id):
        # 1. Rate Limit Tekseriw
        if self.check_rate_limit(chat_id):
            return

        try:
            # Userdi chat_id arqali tabamiz (Nomer soraw shart emes)
            user = User.objects.get(telegram_chat_id=str(chat_id))
            
            code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            cache_data = {
                "phone_number": user.phone_number,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "chat_id": chat_id
            }
            cache.set(f"auth_code_{code}", cache_data, timeout=300) 
            
            # 2. Limit qoyıw & Kod jiberiw
            self.set_rate_limit(chat_id)
            self.send_message(chat_id, f"🔑 Kiriw kodıńız: {code}\n(5 minut aktiv)")
            
        except User.DoesNotExist:
            self.send_message(chat_id, "Siz ele dizimnen ótpegensiz. Iltimas, 'Telefon nomerdi jiberiw' túymesin basıń.")
            self.send_contact_request(chat_id)

    def handle_contact(self, message, chat_id):
        # 1. Rate Limit Tekseriw
        if self.check_rate_limit(chat_id):
            return

        phone_number = message["contact"]["phone_number"]
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        first_name = message["from"].get("first_name", "")
        last_name = message["from"].get("last_name", "")
        
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        cache_data = {
            "phone_number": phone_number,
            "first_name": first_name,
            "last_name": last_name,
            "chat_id": chat_id
        }
        
        cache.set(f"auth_code_{code}", cache_data, timeout=300)
        
        # 2. Limit qoyiw & Kod jiberiw
        self.set_rate_limit(chat_id)
        self.send_message(chat_id, f"Sizdiń tastıyqlaw kodıńız: {code}\n(5 minut aktiv)")

    # --- XABAR JIBERIW ---

    def send_contact_request(self, chat_id):
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "Saytqa kiriw ushın telefon nomerińizdi jiberiń:",
            "reply_markup": {
                "keyboard": [
                    [{"text": "📱 Telefon nomerdi jiberiw", "request_contact": True}],
                    [{"text": "🔐 Kiriw kodın alıw"}] # Login knopkası
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        }
        requests.post(url, json=payload)

    def send_message(self, chat_id, text):
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": {
                "keyboard": [
                    [{"text": "🔐 Kiriw kodın alıw"}] # Turaqli knopka
                ],
                "resize_keyboard": True
            }
        }
        requests.post(url, json=payload)


class LoginWithCodeView(APIView):
    authentication_classes = []
    permission_classes = []

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'telegram_login'

    @extend_schema(request=TelegramLoginSerializer) 
    def post(self, request):
        serializer = TelegramLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        
        # 1. Kodti Cache-ten tekseremiz
        cache_data = cache.get(f"auth_code_{code}")
        if not cache_data:
            return Response({"error": "Kod qáte yamasa múddeti ótken"}, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = cache_data.get("phone_number")
        first_name = cache_data.get("first_name", "")
        last_name = cache_data.get("last_name", "")
        chat_id = cache_data.get("chat_id")
        
        # 2. Userdi bazadan tabamiz yamasa jaratamiz
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                'username': phone_number,
                'first_name': first_name,
                'last_name': last_name,
                'telegram_chat_id': str(chat_id),
                'is_verified': True
            }
        )
        
        # 3. Chat ID ni janalaw (Eger aldin basqa telefondan kirgen bolsa yamasa bos bolsa)
        if str(chat_id) and user.telegram_chat_id != str(chat_id):
            user.telegram_chat_id = str(chat_id)
            user.is_verified = True
            user.save()

        # 4. Kodti oshiremiz
        cache.delete(f"auth_code_{code}")
        
        # 5. Token beremiz
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "phone_number": phone_number,
            "is_new_user": created,
            "message": "Xosh keldiniz!"
        })
    

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer



class SetPasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=SetPasswordSerializer,responses={200:None})
    def post(self,request):
        serializer = SetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password']) #Paroldi shifrlaydi
            user.save()
            
            return Response({'message':'Parol ornatildi!'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   