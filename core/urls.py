from rest_framework.routers import DefaultRouter
from .views import ProductView,CartView

router = DefaultRouter()

router.register(r"products", ProductView, basename="product")


urlpatterns = router.urls