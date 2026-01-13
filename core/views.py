from django.shortcuts import render
from rest_framework import viewsets,filters,generics,mixins,permissions
from rest_framework.pagination import PageNumberPagination
import django_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import ProductsSerializer,CartSerializer,AddCartSerializer,CartItemSerializer
from .models import CustomUser,Category,Product,Cart,CartItem,Order,OrderItem
from .filters import ProductFilter


class ProductView(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductsSerializer
    filter_backends = [filters.SearchFilter,DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['name']
    filterset_class = ProductFilter
    ordering_fields = ['price']
    ordering = ['-price']


class CartView(viewsets.ModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self,request,*args, **kwargs):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], serializer_class=AddCartSerializer)
    def add(self,request):
        serializer = AddCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product.id']
        quantity = serializer.validated_data_get('quantity', 1)

        product = get_object_or_404(Product,id=product_id)
        cart, _ = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(cart=cart,product=product)

        if not created:
            cart_item.quantity += quantity
            cart_item.save()
            return Response({"message": "Produkt sani kobeydi"}, status=status.HTTP_200_OK)
        
        cart_item.quantity = quantity
        cart_item.save()
        return Response({"message": "Product sebetke qosildi"}, status=status.HTTP_201_CREATED)
    
    @action(detail=False,methods=['delete'], url_path=r'remove/(?P<id>\d+)') #Bul jerde d+ tek gana sanlardi uslap al degeni.
    def remove_item(self, request, item_id=None):
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()
        return Response({'message':'Produkt sebetten oshirildi'}, status=status.HTTP_204_NO_CONTENT)
    






    


