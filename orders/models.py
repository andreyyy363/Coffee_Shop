from django.db import models
from django.conf import settings
from products.models import Product, Weight, BeanType
from decimal import Decimal


class Cart(models.Model):
    """Shopping cart."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                                 related_name='cart', null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
    
    def __str__(self):
        if self.user:
            return f"Cart: {self.user.email}"
        return f"Cart (session: {self.session_key[:8]}...)"
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())
    
    @property
    def shipping(self):
        return Decimal('2.00')  # Fixed shipping cost
    
    @property
    def total(self):
        return self.subtotal + self.shipping


class CartItem(models.Model):
    """Item in shopping cart."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    weight = models.ForeignKey(Weight, on_delete=models.CASCADE)
    bean_type = models.ForeignKey(BeanType, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ['cart', 'product', 'weight', 'bean_type']
    
    def __str__(self):
        return f"{self.product.name} ({self.weight.grams}g, {self.bean_type.name}) x {self.quantity}"
    
    @property
    def unit_price(self):
        return self.product.get_price_for_weight(self.weight, self.bean_type)
    
    @property
    def total_price(self):
        return self.unit_price * self.quantity


class Order(models.Model):
    """Customer order."""
    
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('packing', 'Packing'),
        ('shipping', 'Shipping'),
        ('completed', 'Completed'),
        ('cancelled_user', 'Cancelled by User'),
        ('cancelled_manager', 'Cancelled by Manager'),
    ]
    
    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('bank', 'Bank Transfer'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                             null=True, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, verbose_name='Order Number')
    
    # Contact info at time of order
    full_name = models.CharField(max_length=200, verbose_name='Full Name')
    address = models.TextField(verbose_name='Delivery Address')
    phone = models.CharField(max_length=20, verbose_name='Phone')
    
    payment_type = models.CharField(max_length=20, choices=PAYMENT_CHOICES, verbose_name='Payment Method')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing', verbose_name='Status')
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Subtotal')
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('2.00'), verbose_name='Shipping')
    
    # Discount fields
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Discount Percent'
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Discount Amount'
    )
    promo_code_used = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='Promo Code Used'
    )
    
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total')
    
    manager_comment = models.TextField(blank=True, verbose_name='Manager Comment')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number
            import random
            self.order_number = str(random.randint(1000, 9999))
            while Order.objects.filter(order_number=self.order_number).exists():
                self.order_number = str(random.randint(1000, 9999))
        super().save(*args, **kwargs)
    
    @property
    def can_cancel(self):
        """Check if order can be cancelled by user."""
        return self.status in ['processing', 'packing']
    
    @property
    def status_display_class(self):
        """CSS class for status badge."""
        classes = {
            'processing': 'bg-warning',
            'packing': 'bg-info',
            'shipping': 'bg-primary',
            'completed': 'bg-success',
            'cancelled_user': 'bg-secondary',
            'cancelled_manager': 'bg-danger',
        }
        return classes.get(self.status, 'bg-secondary')


class OrderItem(models.Model):
    """Item in an order."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200, verbose_name='Product Name')
    weight = models.CharField(max_length=20, verbose_name='Weight')
    bean_type = models.CharField(max_length=50, verbose_name='Bean Type')
    quantity = models.PositiveIntegerField(verbose_name='Quantity')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Unit Price')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total')
    
    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class OrderStatusHistory(models.Model):
    """History of order status changes."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    comment = models.TextField(blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Order Status History'
        verbose_name_plural = 'Order Status History'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Order #{self.order.order_number} - {self.get_status_display()}"
