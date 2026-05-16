from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    IngredientViewSet,
    RecipeViewSet,
    RecipeIngredientViewSet,
    CakeBatchViewSet,
    BakeView,
)

router = DefaultRouter()
router.register(r"ingredients",        IngredientViewSet,       basename="ingredient")
router.register(r"recipes",            RecipeViewSet,           basename="recipe")
router.register(r"recipe-ingredients", RecipeIngredientViewSet, basename="recipe-ingredient")
router.register(r"cake-batches",       CakeBatchViewSet,        basename="cake-batch")

urlpatterns = [
    path("", include(router.urls)),
    path("production/bake/", BakeView.as_view(), name="production-bake"),
]
