"""
Recommendation System Models

This module contains models for storing user interactions and product similarities
used by the recommendation engine.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from products.models import Product


class RecommendationSettings(models.Model):
    """
    Global settings for the recommendation system (singleton model).

    Stores hybrid algorithm weights, feature weights, and other
    configuration for the recommendation engine.
    """

    # Hybrid algorithm weights
    weight_content_based = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.35'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Content-Based Weight (α)',
        help_text='Weight for content-based filtering (product similarity)'
    )
    weight_collaborative = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.40'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Collaborative Weight (β)',
        help_text='Weight for collaborative filtering (user behavior)'
    )
    weight_popularity = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.25'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Popularity Weight (γ)',
        help_text='Weight for popularity-based recommendations'
    )

    # Content-based feature weights
    feature_country_weight = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.25'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Country Feature Weight'
    )
    feature_roast_weight = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.30'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Roast Level Feature Weight'
    )
    feature_bean_weight = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.25'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Bean Type Feature Weight'
    )
    feature_price_weight = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.20'),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Price Feature Weight'
    )

    # Time decay parameter
    time_decay_rate = models.DecimalField(
        max_digits=4, decimal_places=3, default=Decimal('0.050'),
        validators=[MinValueValidator(Decimal('0.001')), MaxValueValidator(1)],
        verbose_name='Time Decay Rate (λ)',
        help_text='Higher = interactions lose weight faster. Formula: weight × e^(-λt)'
    )

    # System settings
    is_active = models.BooleanField(default=True, verbose_name='System Active')
    min_interactions_for_cf = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1)],
        verbose_name='Min Interactions for CF',
        help_text='Minimum user interactions to use collaborative filtering'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Recommendation Settings'
        verbose_name_plural = 'Recommendation Settings'

    def __str__(self):
        return f"Recommendation Settings (α={self.weight_content_based}, β={self.weight_collaborative}, γ={self.weight_popularity})"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and RecommendationSettings.objects.exists():
            existing = RecommendationSettings.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create singleton settings instance."""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class UserProductInteraction(models.Model):
    """
    Tracks user interactions with products.
    Used for collaborative filtering and building user preference profiles.

    Interaction types and their weights:
    - view: User viewed product detail page
    - cart: User added product to cart
    - purchase: User completed purchase
    - favorite: User added to favorites
    - review: User left a review
    """

    INTERACTION_TYPES = [
        ('view', 'View'),
        ('cart', 'Add to Cart'),
        ('purchase', 'Purchase'),
        ('favorite', 'Favorite'),
        ('review', 'Review'),
    ]

    # Weights for different interactions (used in scoring)
    INTERACTION_WEIGHTS = {
        'view': 1.0,
        'cart': 3.0,
        'purchase': 5.0,
        'favorite': 4.0,
        'review': 4.5,
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='product_interactions'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='user_interactions'
    )
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    interaction_count = models.PositiveIntegerField(default=1)
    last_interaction = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Product Interaction'
        verbose_name_plural = 'User Product Interactions'
        unique_together = ['user', 'product', 'interaction_type']
        indexes = [
            models.Index(fields=['user', 'interaction_type']),
            models.Index(fields=['product', 'interaction_type']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.product.name} ({self.interaction_type})"

    @property
    def weighted_score(self):
        """Calculate weighted score for this interaction."""
        weight = self.INTERACTION_WEIGHTS.get(self.interaction_type, 1.0)
        return weight * self.interaction_count


class ProductSimilarity(models.Model):
    """
    Pre-computed product similarities using content-based filtering.

    Similarity is calculated based on country origin, roast level,
    bean types, and price range as a weighted combination.
    """

    product_a = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='similarities_as_a'
    )
    product_b = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='similarities_as_b'
    )
    similarity_score = models.FloatField()  # 0.0 to 1.0
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product Similarity'
        verbose_name_plural = 'Product Similarities'
        unique_together = ['product_a', 'product_b']
        indexes = [
            models.Index(fields=['product_a', 'similarity_score']),
        ]

    def __str__(self):
        return f"{self.product_a.name} ~ {self.product_b.name} ({self.similarity_score:.2f})"


class RecommendationLog(models.Model):
    """
    Log of recommendations shown to users.
    Used for A/B testing and measuring recommendation effectiveness.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommendation_logs'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='recommendation_logs'
    )
    algorithm = models.CharField(max_length=50)  # 'content', 'collaborative', 'hybrid', 'popular'
    score = models.FloatField()
    position = models.PositiveIntegerField()  # Position in recommendation list
    was_clicked = models.BooleanField(default=False)
    was_purchased = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Recommendation Log'
        verbose_name_plural = 'Recommendation Logs'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['algorithm', 'was_clicked']),
        ]

    def __str__(self):
        return f"Rec: {self.product.name} for {self.user.email} ({self.algorithm})"
