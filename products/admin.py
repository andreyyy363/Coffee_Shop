from django.contrib import admin
from .models import Country, RoastLevel, BeanType, Weight, Product, Favorite


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(RoastLevel)
class RoastLevelAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(BeanType)
class BeanTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Weight)
class WeightAdmin(admin.ModelAdmin):
    list_display = ('grams', 'price_multiplier')
    ordering = ('grams',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_price', 'roast_level', 'is_active', 'average_rating', 'created_at')
    list_filter = ('is_active', 'roast_level', 'countries')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('countries', 'available_bean_types', 'available_weights')

    fieldsets = (
        (None, {'fields': ('name', 'slug', 'image')}),
        ('Description', {'fields': ('short_description', 'description', 'taste_profile')}),
        ('Pricing', {'fields': ('base_price',)}),
        ('Characteristics', {'fields': ('countries', 'roast_level', 'available_bean_types', 'available_weights')}),
        ('Status', {'fields': ('is_active',)}),
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'product__name')
