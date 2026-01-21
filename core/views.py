from django.shortcuts import render
from rest_framework import viewsets,filters,permissions,status,generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from .serializers import ProductsSerializer, CartSerializer, OrderSerializer, UserRegisterSerializer
from .models import CustomUser,Category, Product, Cart, CartItem, Order, OrderItem
from .filters import ProductFilter
from rest_framework import permissions
from .permissions import IsAdminOrReadOnly


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductsSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['name']
    filterset_class = ProductFilter
    ordering_fields = ['price']
    ordering = ['-price']



class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)
    
    def perform_create(self,serializer):
        serializer.save(user=self.request.user)
    
    
    
    @action(detail=False, methods=['post'])
    def add(self, request):
        product_id = request.data.get('product_id')    
        quantity = int(request.data.get('quantity',1))


        product = get_object_or_404(Product,id=product_id) #Sol onim barma joqpa soni tekserip atirmiz

        if product.stock < quantity:  #Bazada jeterli product barma tekserip atirmiz
            return Response({'error': "bazadan bunsha product joq"}, status=status.HTTP_400_BAD_REQUEST)
        
        cart, created = Cart.objects.get_or_create(user=request.user)

        cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)

        if  item_created:
            cart_item.quantity = quantity
        else:
            cart_item.quantity += quantity
        
        cart_item.save()

        return Response({'success': "Product sebetke qosildi"}, status=status.HTTP_201_CREATED)
    

    @action(detail=True, methods=['delete'])
    def remove(self,request, pk=None):
        cart_item = get_object_or_404(CartItem, id=pk, cart__user=self.request.user)
        cart_item.delete()

        return Response({'Success': 'Product sebetten oshirildi'}, status=status.HTTP_204_NO_CONTENT)
    

            
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]


    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
    @action(detail=False,methods=['post'])
    def checkout(self,request):
        user = request.user
        address = request.data.get('address') #adresti klient jiberiw kerek
        cart_item_ids = request.data.get('cart_items', [])

        if not address:
            return Response({'error':'Jetkerip beriw adresi kiritilmegen'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not cart_item_ids:
            return Response({'error':'Product tanlanbagan'}, status=status.HTTP_400_BAD_REQUEST)


        cart  =  get_object_or_404(Cart,user=user)      #Cart.objects.get(user=user)  

        cart_items = cart.items.filter(id__in=cart_item_ids)
        

        if not cart_items.exists():
            return Response({'error':'Sebet bos'}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():  

            total_price = 0

            
            for item in cart_items:
                if item.product.stock <item.quantity:
                    return Response({'error': f"{item.product.name} onim bazada jetkiliksiz, Bazada: {item.product.stock} dana produckt bar"}, status=status.HTTP_400_BAD_REQUEST)
                
                total_price += item.get_total_price()    



            order = Order.objects.create(user=user,total_price = total_price, status = 'kutilmekte', address= address)

            for item in cart_items:
                
                OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.product.price)
                item.product.stock -= item.quantity
                item.product.save()
            
            cart_items.delete()

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer


