from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('unit_price', 'total_price')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'total_items', 'subtotal', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('user__email',)
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'weight', 'bean_type', 'quantity', 'unit_price', 'total_price')


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('status', 'comment', 'changed_by', 'created_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'full_name', 'status', 'total', 'created_at')
    list_filter = ('status', 'payment_type', 'created_at')
    search_fields = ('order_number', 'user__email', 'full_name', 'phone')
    readonly_fields = ('order_number', 'subtotal', 'total', 'created_at', 'updated_at')
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    
    fieldsets = (
        ('Order', {'fields': ('order_number', 'user', 'status')}),
        ('Contact Information', {'fields': ('full_name', 'address', 'phone')}),
        ('Payment', {'fields': ('payment_type', 'subtotal', 'shipping', 'total')}),
        ('Comment', {'fields': ('manager_comment',)}),
        ('Dates', {'fields': ('created_at', 'updated_at')}),
    )
    
    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            # Create status history entry
            OrderStatusHistory.objects.create(
                order=obj,
                status=obj.status,
                changed_by=request.user
            )
        super().save_model(request, obj, form, change)
