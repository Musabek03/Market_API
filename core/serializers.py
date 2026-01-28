from rest_framework import serializers
from .models import (
    CustomUser,
    Category,
    Product,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Review,
)
from django.utils.text import slugify


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "children"]

    def get_children(self,obj):
        
        children = obj.child.all()

        return [ 
            {"id": child.id,
             "name": child.name,
             "slug": child.slug
             }
             for child in children
                ]


class ProductsSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category", write_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "category_id",
            "name",
            "description",
            "price",
            "discount_price",
            "image",
        ]

    def create(self, validated_data):
        validated_data["slug"] = slugify(validated_data["name"])
        return super().create(validated_data)


class CartItemSerializer(serializers.ModelSerializer):

    product = ProductsSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product", write_only=True
    )

    class Meta:
        model = CartItem
        fields = ["id", "product", "product_id", "quantity"]


class CartSerializer(serializers.ModelSerializer):

    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    def get_total_price(self, obj):

        items = obj.items.all()
        prices = []

        for item in items:
            prices.append(item.get_total_price())

        return sum(prices)

    class Meta:
        model = Cart
        fields = ["id", "user", "items", "total_price"]


class CartAddSerializer(serializers.Serializer):

    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1)


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductsSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "price"]


class OrderSerializer(serializers.ModelSerializer):
    orderitems = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "orderitems",
            "total_price",
            "status",
            "address",
            "created_at",
        ]


class CheckoutSerializer(serializers.Serializer):

    address = serializers.CharField(max_length=450, required=True)
    cart_items = serializers.ListField(child=serializers.IntegerField(), required=False)


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ["username", "phone_number", "password"]

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            phone_number=validated_data["phone_number"],
        )

        return user
    

class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'phone_number', 'Address', 'email']
        read_only_fields = ['id', 'phone_number']


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "user", "product", "text", "rating", "created_at"]
