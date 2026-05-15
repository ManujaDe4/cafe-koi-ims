from django.db.models import F
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Ingredient, Recipe, RecipeIngredient, CakeBatch
from .serializers import (
    IngredientSerializer,
    RecipeSerializer,
    RecipeIngredientSerializer,
    CakeBatchSerializer,
)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "current_stock", "cost_per_unit"]

    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        """Ingredients where current_stock is at or below reorder_threshold."""
        qs = self.get_queryset().filter(current_stock__lte=F("reorder_threshold"))
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.prefetch_related("recipe_ingredients__ingredient").all()
    serializer_class = RecipeSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "version"]

    def get_queryset(self):
        qs = super().get_queryset()
        archived = self.request.query_params.get("archived", "false")
        if archived.lower() != "true":
            qs = qs.filter(archived=False)
        return qs


class RecipeIngredientViewSet(viewsets.ModelViewSet):
    queryset = RecipeIngredient.objects.select_related("recipe", "ingredient").all()
    serializer_class = RecipeIngredientSerializer


class CakeBatchViewSet(viewsets.ModelViewSet):
    queryset = CakeBatch.objects.select_related("recipe").all()
    serializer_class = CakeBatchSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["baked_at", "quantity_baked"]
    http_method_names = ["get", "post", "head", "options"]
