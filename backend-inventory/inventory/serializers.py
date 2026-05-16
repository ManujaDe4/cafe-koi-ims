from rest_framework import serializers
from .models import Ingredient, Recipe, RecipeIngredient, CakeBatch


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = "__all__"


class AdjustmentSerializer(serializers.Serializer):
    delta = serializers.DecimalField(max_digits=10, decimal_places=3)
    reason = serializers.ChoiceField(choices=["restock", "waste", "correction"])


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


class RecipeIngredientInputSerializer(serializers.Serializer):
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    quantity_required = serializers.DecimalField(
        max_digits=10, decimal_places=3, min_value="0.001"
    )


class RecipeSerializer(serializers.ModelSerializer):
    recipe_ingredients = RecipeIngredientSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientInputSerializer(many=True, write_only=True, required=False)

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
            "ingredients",
        ]

    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients", [])
        recipe = Recipe.objects.create(**validated_data)
        for item in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=item["ingredient"],
                quantity_required=item["quantity_required"],
            )
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("ingredients", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            for item in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=item["ingredient"],
                    quantity_required=item["quantity_required"],
                )
        return instance


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
