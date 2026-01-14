from django.shortcuts import render
from rest_framework import viewsets,filters,generics,mixins,permissions
from rest_framework.pagination import PageNumberPagination
import django_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import ProductsSerializer,CartSerializer,AddCartSerializer
from .models import CustomUser,Category,Product,Cart,CartItem,Order,OrderItem
from .filters import ProductFilter


class ProductView(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductsSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter,DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ['name']
    filterset_class = ProductFilter
    ordering_fields = ['price']
    ordering = ['-price']

