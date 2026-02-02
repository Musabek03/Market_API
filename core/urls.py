from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet,
    CartViewSet,
    OrderViewSet,
    RegisterView,
    ReviewViewSet,
    CategoryViewSet,
    UserProfileView,
    TelegramWebhookView,
    LoginWithCodeView,
    SetPasswordView,
    CartItemsViewSet
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()

router.register(r"categories",CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"cart-items", CartItemsViewSet, basename="cart-items") 
router.register(r"orders", OrderViewSet, basename="Orders")
router.register(r"reviews", ReviewViewSet, basename="reviews")


urlpatterns = [
    path("", include(router.urls)),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('telegram-webhook/', TelegramWebhookView.as_view(),name='telegram-webhook'),
    path('auth/telegram/', LoginWithCodeView.as_view(), name='telegram-login'),
    #path("register/", RegisterView.as_view(), name="register"),
    #path("login/", TokenObtainPairView.as_view(), name="login"),
    #path('profile/set-password/', SetPasswordView.as_view(), name='set-password')
]
