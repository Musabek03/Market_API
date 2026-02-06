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
from rest_framework.exceptions import ValidationError
from django.core.cache import cache
from drf_spectacular.utils import extend_schema_field


class CategorySerializer(serializers.ModelSerializer):
    #children = serializers.SerializerMethodField()
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]

    # def get_children(self,obj):
        
    #     children = obj.child.all()

    #     return [ 
    #         {"id": child.id,
    #          "name": child.name,
    #          "slug": child.slug
    #          }
    #          for child in children
    #             ]

class CategoryShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]



class ProductsSerializer(serializers.ModelSerializer):
    category = CategoryShortSerializer(read_only=True)
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


# class CartSerializer(serializers.ModelSerializer):

#     items = CartItemSerializer(many=True, read_only=True)
#     total_price = serializers.SerializerMethodField()

#     def get_total_price(self, obj):

#         items = obj.items.all()
#         prices = []

#         for item in items:
#             prices.append(item.get_total_price())

#         return sum(prices)

#     class Meta:
#         model = Cart
#         fields = ["id", "user", "items", "total_price"]


class CartAddSerializer(serializers.Serializer):

    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1)



class CartGetSerializer(serializers.ModelSerializer):
    cart_item_ids = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['cart_item_ids', 'total_price']

    @extend_schema_field(serializers.IntegerField())  
    def get_total_price(self, obj):

        items = obj.items.all()
        prices = []

        for item in items:
            prices.append(item.get_total_price())

        return sum(prices)
    
    @extend_schema_field(serializers.ListField(child=serializers.IntegerField()))
    def get_cart_item_ids(self, obj):
        return obj.items.values_list("id", flat=True)



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
    password = serializers.CharField(write_only=True, style={'input_type':'password'}, help_text="Parol")
    confirm_password = serializers.CharField(write_only=True, required=True,style={'input_type':'password'},help_text='Paroldi tastiyqlaw')
    code = serializers.CharField(write_only=True, required=True,help_text="Telegram bot jibergen 6 xanali san")

    class Meta:
        model = CustomUser
        fields = ["username", "phone_number", "password", "confirm_password", "code"]

    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')

        if password != confirm_password:
            raise ValidationError({'confirm_password':'Paroller saykes emes,qaytadan jazin!'})
        
        code = attrs.get('code')
        phone_number = attrs.get('phone_number')
        cache_data = cache.get(f"auth_code_{code}")

        if not cache_data:
            raise ValidationError({'code':'Kod qate yamasa muddeti pitken(Bot arqali jana kod alin)'})
        
        cached_phone = cache_data.get('phone_number')

        if cached_phone != phone_number:
            raise ValidationError({"phone_number": f"Bul kod basqa nomer ushin berilgen, siz {phone_number} kiritip atirsiz."})
        
        attrs['telegram_chat_id'] = cache_data.get('chat_id')

        return attrs

    def create(self, validated_data):

        #Confirm_password ham code bazaga kerek emes, qiyip taslaymiz
        validated_data.pop('confirm_password')
        validated_data.pop('code')

        chat_id = validated_data.pop('telegram_chat_id', None)

        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            phone_number=validated_data["phone_number"],
        )

        user.is_verified = True
        user.telegram_chat_id = chat_id
        user.save()

        return user
    

class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'phone_number', 'Address', 'email']
        read_only_fields = ['id', 'phone_number']


class SetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'}, help_text="Jana Parol")
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'paassword'}, help_text="Paroldi tasiytqlaw")

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Paroller saykes kelmeydi'})
        return attrs


#Swagger ushin
class TelegramLoginSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, help_text="Telegram bot jibergen 6 xanali kod")


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "user", "product", "text", "rating", "created_at"]
