from django.db import transaction
from django.db.models import F
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Ingredient, Recipe, RecipeIngredient, CakeBatch
from .serializers import (
    IngredientSerializer,
    AdjustmentSerializer,
    RecipeSerializer,
    RecipeIngredientSerializer,
    CakeBatchSerializer,
)
from .services import deduct_recipe_stock


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "current_stock", "cost_per_unit"]

    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        qs = self.get_queryset().filter(current_stock__lte=F("reorder_threshold"))
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="adjust")
    def adjust(self, request, pk=None):
        ingredient = self.get_object()
        serializer = AdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        delta = serializer.validated_data["delta"]
        Ingredient.objects.filter(pk=ingredient.pk).update(
            current_stock=F("current_stock") + delta
        )
        ingredient.refresh_from_db()
        return Response(IngredientSerializer(ingredient).data)


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


class BakeView(APIView):
    @transaction.atomic
    def post(self, request):
        recipe_id = request.data.get("recipe_id")
        batch_quantity = request.data.get("batch_quantity")
        baked_by = request.data.get("baked_by", "")

        if not recipe_id:
            return Response(
                {"error": "recipe_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            batch_quantity = int(batch_quantity)
            if batch_quantity < 1:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"error": "batch_quantity must be a positive integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({"error": "Recipe not found"}, status=status.HTTP_404_NOT_FOUND)

        if recipe.archived:
            return Response(
                {"error": "Cannot bake from an archived recipe"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        snapshot = deduct_recipe_stock(recipe, batch_quantity)

        batch = CakeBatch.objects.create(
            recipe=recipe,
            recipe_version_snapshot=snapshot,
            quantity_baked=batch_quantity,
            baked_by=baked_by,
        )
        return Response(CakeBatchSerializer(batch).data, status=status.HTTP_201_CREATED)
