from rest_framework.routers import DefaultRouter
from .views import ProductViewSet,CartViewSet,OrderViewSet
router = DefaultRouter()

router.register(r"products", ProductViewSet, basename="product")
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"orders", OrderViewSet,basename="Orders")


urlpatterns = router.urls