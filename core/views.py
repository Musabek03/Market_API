from django.shortcuts import render
from rest_framework import viewsets, filters, permissions, status, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from .serializers import (
    ProductsSerializer,
    CartSerializer,
    OrderSerializer,
    UserRegisterSerializer,
    ReviewSerializer,
    CartAddSerializer,
    CheckoutSerializer,
    CategorySerializer,
    UserProfileSerializer,
    TelegramLoginSerializer,
    SetPasswordSerializer,
)
from .models import CustomUser, Product, Cart, CartItem, Order, OrderItem, Review, Category
from .filters import ProductFilter
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from .permissions import IsAdminOrReadOnly
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




class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    pagination_class = None
    search_fields = ['name', 'slug']


    def get_queryset(self):
        queryset =  Category.objects.filter(parent__isnull =True).prefetch_related('child')

        search_query = self.request.query_params.get('search', None)

        if search_query:
            return queryset
        else:
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
    ordering_fields = ["price"]
    ordering = ["-price"]


class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).prefetch_related(
            "items__product"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(request=CartAddSerializer)
    @action(detail=False, methods=["post"])
    def add(self, request):
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        product = get_object_or_404(
            Product, id=product_id
        )  # Sol onim barma joqpa soni tekserip atirmiz

        if product.stock < quantity:  # Bazada jeterli product barma tekserip atirmiz
            return Response(
                {"error": "bazadan bunsha product joq"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart, created = Cart.objects.get_or_create(user=request.user)

        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart, product=product
        )

        if item_created:
            cart_item.quantity = quantity
        else:
            cart_item.quantity += quantity

        cart_item.save()

        return Response(
            {"success": "Product sebetke qosildi"}, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["delete"])
    def remove(self, request, pk=None):
        cart_item = get_object_or_404(CartItem, id=pk, cart__user=self.request.user)
        cart_item.delete()

        return Response(
            {"Success": "Product sebetten oshirildi"}, status=status.HTTP_204_NO_CONTENT
        )


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

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
                            "error": f"{item.product.name} onim bazada jetkiliksiz, Bazada: {item.product.stock} dana produckt bar"
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


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        product_id = self.request.data.get("product")

        product = get_object_or_404(Product, id=product_id)
        statuslar = ["tolendi", "jiberildi"]
        satip_alingan = OrderItem.objects.filter(
            order__user=user, product=product, order__status__in=statuslar
        ).exists()

        if not satip_alingan:
            raise ValidationError("Siz bul onimdi satip almagansiz")

        serializer.save(user=user, product=product)



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


#Telegram bot API

class TelegramWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        update = request.data
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            
            # 1. /start
            if "text" in message and message["text"] == "/start":
                self.send_contact_request(chat_id)
            
            # 2. CONTACT jiberilgende
            elif "contact" in message:
                phone_number = message["contact"]["phone_number"]
                if not phone_number.startswith('+'):
                    phone_number = '+' + phone_number
                
                first_name = message["from"].get("first_name", "")
                last_name = message["from"].get("last_name", "")
                
                # Kod jaratiw
                code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                
                # CACHE-ke saqlaw (Chat ID qosildi)
                cache_data = {
                    "phone_number": phone_number,
                    "first_name": first_name,
                    "last_name": last_name,
                    "chat_id": chat_id  # <--- Chat ID ni da saqlaymiz
                }
                
                # 5 minutqa saqlaymiz
                cache.set(f"auth_code_{code}", cache_data, timeout=300)
                
                self.send_message(chat_id, f"Sizdin tastiyqlaw kodiniz: {code}\n(Bul kod 5 minut aktiv)")
        
        return Response({"status": "ok"})

    def send_contact_request(self, chat_id):
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "Dizimnen otiw ushin telefon nomerinizdi jiberin:",
            "reply_markup": {
                "keyboard": [[{"text": "Telefon nomerdi jiberiw", "request_contact": True}]],
                "one_time_keyboard": True,
                "resize_keyboard": True
            }
        }
        requests.post(url, json=payload)

    def send_message(self, chat_id, text):
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": {"remove_keyboard": True}
        }
        requests.post(url, json=payload)


class LoginWithCodeView(APIView):
    authentication_classes = []
    permission_classes = []

    # Swaggerge aytamiz: Bul view "TelegramLoginSerializer" isletedi
    @extend_schema(request=TelegramLoginSerializer) 
    def post(self, request):
        # Serializer arqali validaciya (Swaggerde endi 'code' maydani shigadi)
        serializer = TelegramLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        
        # Cache tekseriw
        cache_data = cache.get(f"auth_code_{code}")
        if not cache_data:
            return Response({"error": "Kod qate yamasa muddeti otken"}, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = cache_data.get("phone_number")
        first_name = cache_data.get("first_name", "")
        last_name = cache_data.get("last_name", "")
        chat_id = cache_data.get("chat_id")
        
        # Login yamasa Register (Avtomat)
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                'username': phone_number,
                'first_name': first_name,
                'last_name': last_name,
                'telegram_chat_id': chat_id,
                'is_verified': True
            }
        )
        
        # Eger user aldin bar bolip, biraq verified bolmasa
        if not user.is_verified:
            user.is_verified = True
            user.telegram_chat_id = chat_id
            user.save()

        # Kodti oshiremiz
        cache.delete(f"auth_code_{code}")
        
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "phone_number": phone_number,
            "is_new_user": created,
            "message": "Xosh keldiniz!"
        })