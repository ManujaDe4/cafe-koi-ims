from decimal import Decimal
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import Ingredient, RecipeIngredient


def deduct_recipe_stock(recipe, batch_quantity):
    """
    Deduct ingredient stock for `batch_quantity` runs of `recipe`.
    Collects ALL shortfalls before raising so the caller sees every problem at once.
    Must be called inside a transaction.atomic() block.
    Returns a snapshot dict to store on CakeBatch.recipe_version_snapshot.
    """
    ingredient_ids = list(
        RecipeIngredient.objects.filter(recipe=recipe).values_list("ingredient_id", flat=True)
    )
    locked = {
        ing.id: ing
        for ing in Ingredient.objects.filter(id__in=ingredient_ids).select_for_update()
    }
    ri_rows = RecipeIngredient.objects.filter(recipe=recipe).select_related("ingredient")

    shortfalls = []
    deductions = []

    for ri in ri_rows:
        needed = ri.quantity_required * Decimal(str(batch_quantity))
        ingredient = locked[ri.ingredient_id]
        if ingredient.current_stock < needed:
            short = needed - ingredient.current_stock
            shortfalls.append(
                f"{ingredient.name}: requires {needed:.3f}{ingredient.unit}, "
                f"available {ingredient.current_stock:.3f}{ingredient.unit}, "
                f"short by {short:.3f}{ingredient.unit}"
            )
        else:
            deductions.append((ingredient, needed))

    if shortfalls:
        raise ValidationError({"stock_shortfall": shortfalls})

    total_cost = Decimal("0")
    snapshot_ingredients = []
    for ingredient, needed in deductions:
        cost = needed * ingredient.cost_per_unit
        total_cost += cost
        snapshot_ingredients.append({
            "ingredient_id": ingredient.id,
            "name": ingredient.name,
            "unit": ingredient.unit,
            "quantity_used": str(needed),
            "cost_per_unit": str(ingredient.cost_per_unit),
            "line_cost": str(cost.quantize(Decimal("0.0001"))),
        })

    for ingredient, needed in deductions:
        ingredient.current_stock -= needed
        ingredient.save(update_fields=["current_stock"])

    return {
        "recipe_id": recipe.id,
        "recipe_name": recipe.name,
        "recipe_version": recipe.version,
        "batch_quantity": batch_quantity,
        "captured_at": timezone.now().isoformat(),
        "total_batch_cost": str(total_cost.quantize(Decimal("0.0001"))),
        "ingredients": snapshot_ingredients,
    }
