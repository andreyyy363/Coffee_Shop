from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class DiscountSettings(models.Model):
    """
    Global discount system settings (singleton model).

    Stores RFM weights, discount curve parameters, bonus settings,
    and other configuration for the personal discount system.
    """
    # RFM Weights (must sum to 1.0)
    weight_recency = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.25'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Recency Weight (w₁)',
        help_text='Weight for recency score in RFM calculation'
    )
    weight_frequency = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.35'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Frequency Weight (w₂)',
        help_text='Weight for frequency score in RFM calculation'
    )
    weight_monetary = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.40'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Monetary Weight (w₃)',
        help_text='Weight for monetary score in RFM calculation'
    )

    # Discount bounds
    base_discount_rate = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        verbose_name='Base Discount Rate (%)',
        help_text='Minimum discount for any registered customer'
    )
    max_discount_rate = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('15.00'),
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        verbose_name='Max Discount Rate (%)',
        help_text='Maximum discount achievable through RFM score'
    )

    # Curve parameters
    curve_exponent = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.70'),
        validators=[MinValueValidator(Decimal('0.1')), MaxValueValidator(3)],
        verbose_name='Curve Exponent (α)',
        help_text='Controls discount growth curve. <1 = fast initial growth, >1 = slow initial growth'
    )

    # Normalization parameters (for calculating scores)
    recency_max_days = models.IntegerField(
        default=90,
        validators=[MinValueValidator(7)],
        verbose_name='Recency Max Days',
        help_text='Days after which recency score becomes 0'
    )
    frequency_target = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        verbose_name='Frequency Target',
        help_text='Number of orders for maximum frequency score'
    )
    monetary_target = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('500.00'),
        validators=[MinValueValidator(1)],
        verbose_name='Monetary Target ($)',
        help_text='Total spending for maximum monetary score'
    )

    # Special bonuses
    first_purchase_discount = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('5.00'),
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        verbose_name='First Purchase Discount (%)'
    )
    birthday_discount = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('10.00'),
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        verbose_name='Birthday Discount (%)'
    )
    birthday_discount_days = models.IntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        verbose_name='Birthday Discount Valid Days',
        help_text='Days before/after birthday when discount is active'
    )

    # System settings
    is_active = models.BooleanField(default=True, verbose_name='System Active')
    max_total_discount = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('25.00'),
        validators=[MinValueValidator(0), MaxValueValidator(75)],
        verbose_name='Max Total Discount (%)',
        help_text='Maximum combined discount (RFM + bonuses)'
    )

    class Meta:
        verbose_name = 'Discount Settings'
        verbose_name_plural = 'Discount Settings'

    def __str__(self):
        return 'Discount System Settings'

    def clean(self):
        """Validate that weights sum to 1.0"""
        from django.core.exceptions import ValidationError
        total = self.weight_recency + self.weight_frequency + self.weight_monetary
        if abs(total - Decimal('1.00')) > Decimal('0.01'):
            raise ValidationError(
                f'RFM weights must sum to 1.0 (currently: {total})'
            )

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create settings instance"""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class CustomerDiscount(models.Model):
    """
    Cached discount data for each customer.
    Recalculated periodically or on significant events.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='discount_profile'
    )

    # Raw metrics
    total_orders = models.IntegerField(default=0, verbose_name='Total Orders')
    total_spent = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Total Spent ($)'
    )
    last_order_date = models.DateTimeField(null=True, blank=True, verbose_name='Last Order Date')

    # Calculated RFM scores (0.0 to 1.0)
    recency_score = models.DecimalField(
        max_digits=4, decimal_places=3, default=Decimal('0.000'),
        verbose_name='Recency Score (R)'
    )
    frequency_score = models.DecimalField(
        max_digits=4, decimal_places=3, default=Decimal('0.000'),
        verbose_name='Frequency Score (F)'
    )
    monetary_score = models.DecimalField(
        max_digits=4, decimal_places=3, default=Decimal('0.000'),
        verbose_name='Monetary Score (M)'
    )

    # Final RFM score and discount
    rfm_score = models.DecimalField(
        max_digits=4, decimal_places=3, default=Decimal('0.000'),
        verbose_name='RFM Score'
    )
    base_discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Base Discount (%)'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer Discount Profile'
        verbose_name_plural = 'Customer Discount Profiles'

    def __str__(self):
        return f"{self.user.email} - {self.base_discount_percent}%"


class PromoCode(models.Model):
    """Promotional codes for additional discounts."""

    TYPE_CHOICES = [
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name='Promo Code')
    description = models.TextField(blank=True, verbose_name='Description')

    discount_type = models.CharField(
        max_length=10, choices=TYPE_CHOICES, default='percent',
        verbose_name='Discount Type'
    )
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Discount Value',
        help_text='Percentage or fixed amount depending on type'
    )

    # Restrictions
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Minimum Order Amount'
    )
    max_uses = models.IntegerField(
        null=True, blank=True,
        verbose_name='Max Total Uses',
        help_text='Leave empty for unlimited'
    )
    max_uses_per_user = models.IntegerField(
        default=1,
        verbose_name='Max Uses Per User'
    )

    # Validity
    is_active = models.BooleanField(default=True, verbose_name='Active')
    valid_from = models.DateTimeField(verbose_name='Valid From')
    valid_until = models.DateTimeField(verbose_name='Valid Until')

    # Stats
    times_used = models.IntegerField(default=0, verbose_name='Times Used')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Promo Code'
        verbose_name_plural = 'Promo Codes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.discount_value}{'%' if self.discount_type == 'percent' else '$'})"

    def is_valid(self):
        """Check if promo code is currently valid."""
        from django.utils import timezone
        now = timezone.now()

        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.max_uses and self.times_used >= self.max_uses:
            return False
        return True


class PromoCodeUsage(models.Model):
    """Track promo code usage by users."""

    promo_code = models.ForeignKey(
        PromoCode, on_delete=models.CASCADE, related_name='usages'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='promo_usages'
    )
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL, null=True, related_name='promo_usage'
    )

    discount_applied = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Discount Applied ($)'
    )
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Promo Code Usage'
        verbose_name_plural = 'Promo Code Usages'


class DiscountHistory(models.Model):
    """
    History of all discounts applied to orders.
    Useful for analytics and audit.
    """

    DISCOUNT_TYPE_CHOICES = [
        ('rfm', 'RFM Personal Discount'),
        ('first_purchase', 'First Purchase Bonus'),
        ('birthday', 'Birthday Bonus'),
        ('promo', 'Promo Code'),
    ]

    order = models.ForeignKey(
        'orders.Order', on_delete=models.CASCADE, related_name='discount_history'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='discount_history'
    )

    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES)
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Discount Percent'
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Discount Amount ($)'
    )

    # Snapshot of calculation data at time of order
    rfm_score_snapshot = models.DecimalField(
        max_digits=4, decimal_places=3, null=True, blank=True,
        verbose_name='RFM Score (at time of order)'
    )
    calculation_details = models.JSONField(
        null=True, blank=True,
        verbose_name='Calculation Details',
        help_text='JSON with detailed calculation breakdown'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Discount History'
        verbose_name_plural = 'Discount Histories'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.discount_type} - ${self.discount_amount}"
