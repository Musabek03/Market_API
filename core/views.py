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
)
from .models import CustomUser, Product, Cart, CartItem, Order, OrderItem, Review, Category
from .filters import ProductFilter
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from .permissions import IsAdminOrReadOnly



class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]

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
