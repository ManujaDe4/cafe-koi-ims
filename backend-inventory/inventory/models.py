from django.db import models


class Ingredient(models.Model):
    UNIT_CHOICES = [
        ("g",   "Grams"),
        ("ml",  "Millilitres"),
        ("pcs", "Pieces"),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=3, choices=UNIT_CHOICES)
    current_stock = models.DecimalField(max_digits=10, decimal_places=3)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=4)
    reorder_threshold = models.DecimalField(max_digits=10, decimal_places=3)

    def __str__(self):
        return f"{self.name} ({self.unit})"

    class Meta:
        ordering = ["name"]


class Recipe(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    slice_count = models.PositiveIntegerField()
    version = models.PositiveIntegerField(default=1)
    archived = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} (v{self.version})"

    class Meta:
        ordering = ["name", "-version"]


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT,
        related_name="recipe_ingredients",
    )
    quantity_required = models.DecimalField(max_digits=10, decimal_places=3)

    def __str__(self):
        return (
            f"{self.recipe.name} — {self.ingredient.name}: "
            f"{self.quantity_required}{self.ingredient.unit}"
        )

    class Meta:
        unique_together = [("recipe", "ingredient")]


class CakeBatch(models.Model):
    id = models.AutoField(primary_key=True)
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.PROTECT,
        related_name="batches",
    )
    recipe_version_snapshot = models.JSONField(
        help_text="Snapshot of recipe + ingredients at time of baking"
    )
    quantity_baked = models.PositiveIntegerField(
        help_text="Number of whole cakes baked in this batch"
    )
    baked_by = models.CharField(max_length=100)
    baked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Batch #{self.id} — {self.recipe.name} x{self.quantity_baked}"

    class Meta:
        ordering = ["-baked_at"]
        verbose_name_plural = "cake batches"
