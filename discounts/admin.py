from django.contrib import admin
from .models import DiscountSettings, CustomerDiscount, PromoCode, PromoCodeUsage, DiscountHistory


@admin.register(DiscountSettings)
class DiscountSettingsAdmin(admin.ModelAdmin):
    """Admin for discount system settings."""

    fieldsets = (
        ('RFM Weights', {
            'fields': ('weight_recency', 'weight_frequency', 'weight_monetary'),
            'description': 'Weights must sum to 1.0'
        }),
        ('Discount Rates', {
            'fields': ('base_discount_rate', 'max_discount_rate', 'curve_exponent'),
        }),
        ('Score Normalization', {
            'fields': ('recency_max_days', 'frequency_target', 'monetary_target'),
        }),
        ('Special Bonuses', {
            'fields': ('first_purchase_discount', 'birthday_discount', 'birthday_discount_days'),
        }),
        ('System', {
            'fields': ('is_active', 'max_total_discount'),
        }),
    )

    def has_add_permission(self, request):
        # Only allow one instance
        return not DiscountSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CustomerDiscount)
class CustomerDiscountAdmin(admin.ModelAdmin):
    """Admin for customer discount profiles."""

    list_display = ('user', 'total_orders', 'total_spent', 'rfm_score', 'base_discount_percent', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('user__email', 'user__username')
    readonly_fields = (
        'recency_score', 'frequency_score', 'monetary_score',
        'rfm_score', 'base_discount_percent', 'created_at', 'updated_at'
    )

    fieldsets = (
        ('Customer', {
            'fields': ('user',)
        }),
        ('Raw Metrics', {
            'fields': ('total_orders', 'total_spent', 'last_order_date'),
        }),
        ('Calculated Scores', {
            'fields': ('recency_score', 'frequency_score', 'monetary_score', 'rfm_score'),
        }),
        ('Discount', {
            'fields': ('base_discount_percent',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    """Admin for promo codes."""

    list_display = ('code', 'discount_type', 'discount_value', 'is_active', 'times_used', 'valid_from', 'valid_until')
    list_filter = ('is_active', 'discount_type', 'created_at')
    search_fields = ('code', 'description')
    readonly_fields = ('times_used', 'created_at')

    fieldsets = (
        ('Code', {
            'fields': ('code', 'description')
        }),
        ('Discount', {
            'fields': ('discount_type', 'discount_value'),
        }),
        ('Restrictions', {
            'fields': ('min_order_amount', 'max_uses', 'max_uses_per_user'),
        }),
        ('Validity', {
            'fields': ('is_active', 'valid_from', 'valid_until'),
        }),
        ('Statistics', {
            'fields': ('times_used', 'created_at'),
        }),
    )


@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    """Admin for promo code usage tracking."""

    list_display = ('promo_code', 'user', 'discount_applied', 'used_at')
    list_filter = ('used_at', 'promo_code')
    search_fields = ('user__email', 'promo_code__code')
    readonly_fields = ('promo_code', 'user', 'order', 'discount_applied', 'used_at')


@admin.register(DiscountHistory)
class DiscountHistoryAdmin(admin.ModelAdmin):
    """Admin for discount history."""

    list_display = ('user', 'order', 'discount_type', 'discount_percent', 'discount_amount', 'created_at')
    list_filter = ('discount_type', 'created_at')
    search_fields = ('user__email',)
    readonly_fields = ('order', 'user', 'discount_type', 'discount_percent',
                       'discount_amount', 'rfm_score_snapshot', 'calculation_details', 'created_at')
