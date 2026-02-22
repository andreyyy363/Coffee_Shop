from decimal import Decimal
from django.db import models
from django.conf import settings


class Country(models.Model):
    """Coffee origin country."""
    name = models.CharField(max_length=100, verbose_name='Name')

    class Meta:
        verbose_name = 'Country'
        verbose_name_plural = 'Countries'
        ordering = ['name']

    def __str__(self):
        return self.name


class RoastLevel(models.Model):
    """Coffee roast level."""
    name = models.CharField(max_length=50, verbose_name='Name')

    class Meta:
        verbose_name = 'Roast Level'
        verbose_name_plural = 'Roast Levels'

    def __str__(self):
        return self.name


class BeanType(models.Model):
    """Coffee bean type."""
    name = models.CharField(max_length=50, verbose_name='Name')
    price_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('1.00'),
                                           verbose_name='Price Multiplier')

    class Meta:
        verbose_name = 'Bean Type'
        verbose_name_plural = 'Bean Types'

    def __str__(self):
        return self.name


class Weight(models.Model):
    """Product weight options."""
    grams = models.IntegerField(verbose_name='Weight (g)')
    price_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('1.00'),
                                           verbose_name='Price Multiplier')

    class Meta:
        verbose_name = 'Weight'
        verbose_name_plural = 'Weight Options'
        ordering = ['grams']

    def __str__(self):
        return f"{self.grams}g"


class Product(models.Model):
    """Coffee product."""
    name = models.CharField(max_length=200, verbose_name='Name')
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(verbose_name='Description')
    short_description = models.CharField(max_length=200, verbose_name='Short Description', blank=True)

    image = models.ImageField(upload_to='products/', verbose_name='Image', blank=True)

    # Base price (for smallest weight)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Base Price (USD)')

    # Characteristics
    countries = models.ManyToManyField(Country, verbose_name='Origin Countries', related_name='products')
    roast_level = models.ForeignKey(RoastLevel, on_delete=models.SET_NULL, null=True, verbose_name='Roast Level')
    available_bean_types = models.ManyToManyField(BeanType, verbose_name='Available Bean Types',
                                                  related_name='products')
    available_weights = models.ManyToManyField(Weight, verbose_name='Available Weights', related_name='products')

    # Taste profile
    taste_profile = models.TextField(verbose_name='Taste Profile', blank=True)

    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_price_for_weight(self, weight, bean_type=None):
        """Calculate price based on weight and bean type multipliers."""
        price = self.base_price * weight.price_multiplier
        if bean_type:
            price = price * bean_type.price_multiplier
        return price.quantize(Decimal('0.01'))

    @property
    def min_price(self):
        """Get minimum price (smallest weight)."""
        smallest_weight = self.available_weights.order_by('grams').first()
        if smallest_weight:
            return self.get_price_for_weight(smallest_weight)
        return self.base_price

    @property
    def average_rating(self):
        """Calculate average rating from reviews."""
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            return round(reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)
        return 0

    @property
    def reviews_count(self):
        """Count approved reviews."""
        return self.reviews.filter(is_approved=True).count()

    @property
    def countries_display(self):
        """Get comma-separated list of countries."""
        return ', '.join([c.name for c in self.countries.all()])


class Favorite(models.Model):
    """User's favorite products."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Favorite'
        verbose_name_plural = 'Favorites'
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"
