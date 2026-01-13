from rest_framework import serializers
from .models import CustomUser,Category,Product,Cart,CartItem,Order,OrderItem

class ProductsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class AddCartSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()

    class Meta:
        model = CartItem
        fields = ['product_id', 'quantity']


class CartItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(source="product.name",read_only=True)
    product_price = serializers.DecimalField(source="product.price",max_digits=12, decimal_places=2,read_only=True)
    total_price = serializers.DecimalField(source='get_total_price',max_digits=12, decimal_places=2,read_only=True)


    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'product_price', 'quantity', 'total_price']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'final_price']

    def get_final_price(self, obj):
        return sum(item.get_total_price() for item in obj.items.all())
    