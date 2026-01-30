from django.contrib import admin
from .models import Category, Product, Order, Notification, CustomUser
from django.contrib.auth.admin import UserAdmin


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "description",
        "price",
    )
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description", "price")
    list_filter = ("is_active", "created_at", "stock")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("user", "total_price", "status", "address", "created_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
     list_display = ('username', 'first_name', 'last_name', 'phone_number', 'role', 'is_staff', 'is_verified')

     fieldsets = (
        (None, {'fields': ('username', 'password')}), 
        ('Jeke Magliwmatlar', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'Address')}),
        ('Telegram Info', {'fields': ('telegram_chat_id', 'is_verified')}), 
        ('Ruxsatlar (Permissions)', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Waqitlar', {'fields': ('last_login', 'date_joined')}),
    )
