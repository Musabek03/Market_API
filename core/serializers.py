from rest_framework import serializers
from .models import CustomUser,Category,Product,Cart,CartItem,Order,OrderItem

class ProductsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"

