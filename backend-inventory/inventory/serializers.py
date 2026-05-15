from rest_framework import serializers
from .models import Ingredient, Recipe, RecipeIngredient, CakeBatch


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = "__all__"


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)
    ingredient_unit = serializers.CharField(source="ingredient.unit", read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = [
            "id",
            "ingredient",
            "ingredient_name",
            "ingredient_unit",
            "quantity_required",
        ]


class RecipeSerializer(serializers.ModelSerializer):
    recipe_ingredients = RecipeIngredientSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "id",
            "name",
            "description",
            "slice_count",
            "version",
            "archived",
            "recipe_ingredients",
        ]


class CakeBatchSerializer(serializers.ModelSerializer):
    recipe_name = serializers.CharField(source="recipe.name", read_only=True)

    class Meta:
        model = CakeBatch
        fields = [
            "id",
            "recipe",
            "recipe_name",
            "recipe_version_snapshot",
            "quantity_baked",
            "baked_by",
            "baked_at",
        ]
        read_only_fields = ["baked_at"]
