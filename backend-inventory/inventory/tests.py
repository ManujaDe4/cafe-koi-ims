from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from .models import Ingredient, Recipe, RecipeIngredient, CakeBatch
from .services import deduct_recipe_stock


def _make_ingredient(name, unit="g", stock="1000.000", cost="0.0100", reorder="100.000"):
    return Ingredient.objects.create(
        name=name,
        unit=unit,
        current_stock=Decimal(stock),
        cost_per_unit=Decimal(cost),
        reorder_threshold=Decimal(reorder),
    )


def _make_recipe(name="Croissant", slice_count=8):
    return Recipe.objects.create(name=name, slice_count=slice_count)


class DeductRecipeStockTests(TestCase):
    def setUp(self):
        self.flour = _make_ingredient("Flour", stock="500.000")
        self.butter = _make_ingredient("Butter", stock="300.000")
        self.recipe = _make_recipe()
        RecipeIngredient.objects.create(
            recipe=self.recipe, ingredient=self.flour, quantity_required=Decimal("200.000")
        )
        RecipeIngredient.objects.create(
            recipe=self.recipe, ingredient=self.butter, quantity_required=Decimal("100.000")
        )

    def test_successful_deduction(self):
        snapshot = deduct_recipe_stock(self.recipe, 1)
        self.flour.refresh_from_db()
        self.butter.refresh_from_db()
        self.assertEqual(self.flour.current_stock, Decimal("300.000"))
        self.assertEqual(self.butter.current_stock, Decimal("200.000"))
        self.assertEqual(snapshot["batch_quantity"], 1)
        self.assertEqual(snapshot["recipe_id"], self.recipe.id)
        self.assertEqual(len(snapshot["ingredients"]), 2)

    def test_negative_stock_guard_full_rollback(self):
        self.flour.current_stock = Decimal("100.000")
        self.flour.save()
        self.butter.current_stock = Decimal("50.000")
        self.butter.save()
        with self.assertRaises(ValidationError) as ctx:
            deduct_recipe_stock(self.recipe, 1)
        errors = ctx.exception.detail["stock_shortfall"]
        self.assertEqual(len(errors), 2)
        self.flour.refresh_from_db()
        self.butter.refresh_from_db()
        self.assertEqual(self.flour.current_stock, Decimal("100.000"))
        self.assertEqual(self.butter.current_stock, Decimal("50.000"))


class AdjustEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.ingredient = _make_ingredient("Sugar", stock="200.000")

    def test_adjust_restock(self):
        url = f"/api/v1/ingredients/{self.ingredient.pk}/adjust/"
        response = self.client.post(url, {"delta": "50.000", "reason": "restock"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.current_stock, Decimal("250.000"))

    def test_adjust_waste(self):
        url = f"/api/v1/ingredients/{self.ingredient.pk}/adjust/"
        response = self.client.post(url, {"delta": "-30.000", "reason": "waste"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.current_stock, Decimal("170.000"))


class BakeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.flour = _make_ingredient("Flour", stock="1000.000")
        self.recipe = _make_recipe()
        RecipeIngredient.objects.create(
            recipe=self.recipe, ingredient=self.flour, quantity_required=Decimal("300.000")
        )

    def test_bake_endpoint_e2e(self):
        response = self.client.post(
            "/api/v1/production/bake/",
            {"recipe_id": self.recipe.pk, "batch_quantity": 2, "baked_by": "test_baker"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["quantity_baked"], 2)
        self.assertEqual(data["baked_by"], "test_baker")
        self.flour.refresh_from_db()
        self.assertEqual(self.flour.current_stock, Decimal("400.000"))
        self.assertEqual(CakeBatch.objects.count(), 1)
