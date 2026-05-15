from django.contrib import admin
from .models import Ingredient, Recipe, RecipeIngredient, CakeBatch


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ["name", "version", "slice_count", "archived"]
    list_filter = ["archived"]
    inlines = [RecipeIngredientInline]


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["name", "unit", "current_stock", "reorder_threshold", "cost_per_unit"]
    list_filter = ["unit"]


@admin.register(CakeBatch)
class CakeBatchAdmin(admin.ModelAdmin):
    list_display = ["id", "recipe", "quantity_baked", "baked_by", "baked_at"]
    readonly_fields = ["baked_at", "recipe_version_snapshot"]
