import math
from collections import defaultdict
from decimal import Decimal
from typing import List, Dict, Optional, Set

from django.db.models import Avg, Count, Q
from django.utils import timezone
from django.core.cache import cache

from products.models import Product
from .models import UserProductInteraction, ProductSimilarity, RecommendationLog


class RecommendationEngine:
    """
    Hybrid recommendation engine for coffee products.

    This engine combines content-based filtering, collaborative filtering,
    and popularity-based scoring to generate personalized recommendations.

    :param user: The user object for whom recommendations are generated.
    """

    # Cache timeout (seconds)
    CACHE_TIMEOUT = 3600  # 1 hour

    def __init__(self, user):
        self.user = user
        self._user_profile = None
        self._all_products = None
        self._settings = None

    @property
    def settings(self):
        """Get recommendation settings from database."""
        if self._settings is None:
            from .models import RecommendationSettings
            self._settings = RecommendationSettings.get_settings()
        return self._settings

    @property
    def content_weight(self):
        return float(self.settings.weight_content_based)

    @property
    def collaborative_weight(self):
        return float(self.settings.weight_collaborative)

    @property
    def popularity_weight(self):
        return float(self.settings.weight_popularity)

    @property
    def country_weight(self):
        return float(self.settings.feature_country_weight)

    @property
    def roast_weight(self):
        return float(self.settings.feature_roast_weight)

    @property
    def bean_weight(self):
        return float(self.settings.feature_bean_weight)

    @property
    def price_weight(self):
        return float(self.settings.feature_price_weight)

    @property
    def time_decay_rate(self):
        return float(self.settings.time_decay_rate)

    @property
    def user_profile(self) -> Dict:
        """
        Build or retrieve the user preference profile from interactions.

        The profile is constructed by aggregating user interactions with products,
        applying a time-decay factor to weigh recent interactions more heavily.
        The result includes preferred countries, roast levels, bean types, and price sensitivity.

        :return: A dictionary containing the user's preference profile.
        :rtype: dict
        """
        if self._user_profile is not None:
            return self._user_profile

        cache_key = f'user_profile_{self.user.id}'
        cached = cache.get(cache_key)
        if cached:
            self._user_profile = cached
            return cached

        profile = {
            'preferred_countries': set(),
            'preferred_roast_levels': set(),
            'preferred_bean_types': set(),
            'price_sum': Decimal('0'),
            'price_count': 0,
            'interacted_products': set(),
            'interaction_scores': defaultdict(float),
        }

        # Get all user interactions with time decay
        interactions = UserProductInteraction.objects.filter(
            user=self.user
        ).select_related('product', 'product__roast_level').prefetch_related(
            'product__countries', 'product__available_bean_types'
        )

        now = timezone.now()

        for interaction in interactions:
            product = interaction.product

            # Calculate time-decayed weight
            days_ago = (now - interaction.last_interaction).days
            time_decay = math.exp(-self.time_decay_rate * days_ago)
            weight = interaction.weighted_score * time_decay

            # Add to interaction scores
            profile['interaction_scores'][product.id] += weight
            profile['interacted_products'].add(product.id)

            # Build preference vectors (weighted)
            for country in product.countries.all():
                profile['preferred_countries'].add(country.id)

            if product.roast_level:
                profile['preferred_roast_levels'].add(product.roast_level.id)

            for bean_type in product.available_bean_types.all():
                profile['preferred_bean_types'].add(bean_type.id)

            profile['price_sum'] += product.base_price * Decimal(str(weight))
            profile['price_count'] += weight

        # Calculate average preferred price
        if profile['price_count'] > 0:
            profile['avg_price'] = profile['price_sum'] / Decimal(str(profile['price_count']))
        else:
            profile['avg_price'] = Decimal('0')

        self._user_profile = profile
        cache.set(cache_key, profile, self.CACHE_TIMEOUT)

        return profile

    def _get_all_products(self) -> List[Product]:
        """Get all active products with prefetched relations."""
        if self._all_products is not None:
            return self._all_products

        self._all_products = list(
            Product.objects.filter(is_active=True)
            .select_related('roast_level')
            .prefetch_related('countries', 'available_bean_types')
            .annotate(
                avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
                review_count=Count('reviews', filter=Q(reviews__is_approved=True)),
                purchase_count=Count(
                    'user_interactions',
                    filter=Q(user_interactions__interaction_type='purchase')
                )
            )
        )
        return self._all_products

    def calculate_content_similarity(self, product: Product) -> float:
        """
        Calculate content-based similarity between user profile and product.

        This method computes a similarity score based on the match between the
        user's preferences (country, roast, bean type, price) and the product's attributes.
        It uses Jaccard similarity for sets and normalized distance for numerical values.

        :param product: The product to compare against the user profile.
        :type product: Product
        :return: A similarity score between 0.0 and 1.0.
        :rtype: float
        """
        profile = self.user_profile

        if not profile['interacted_products']:
            return 0.0

        # Country similarity (Jaccard)
        product_countries = set(product.countries.values_list('id', flat=True))
        if profile['preferred_countries'] and product_countries:
            country_intersection = len(profile['preferred_countries'] & product_countries)
            country_union = len(profile['preferred_countries'] | product_countries)
            country_sim = country_intersection / country_union if country_union > 0 else 0
        else:
            country_sim = 0.5  # Neutral if no data

        # Roast level similarity (exact match)
        if product.roast_level and profile['preferred_roast_levels']:
            roast_sim = 1.0 if product.roast_level.id in profile['preferred_roast_levels'] else 0.0
        else:
            roast_sim = 0.5

        # Bean type similarity (Jaccard)
        product_beans = set(product.available_bean_types.values_list('id', flat=True))
        if profile['preferred_bean_types'] and product_beans:
            bean_intersection = len(profile['preferred_bean_types'] & product_beans)
            bean_union = len(profile['preferred_bean_types'] | product_beans)
            bean_sim = bean_intersection / bean_union if bean_union > 0 else 0
        else:
            bean_sim = 0.5

        # Price similarity (normalized distance)
        if profile['avg_price'] > 0:
            max_price = max(p.base_price for p in self._get_all_products())
            price_diff = abs(float(product.base_price) - float(profile['avg_price']))
            max_diff = float(max_price)
            price_sim = 1 - (price_diff / max_diff) if max_diff > 0 else 1
        else:
            price_sim = 0.5

        # Weighted combination
        similarity = (
                self.country_weight * country_sim +
                self.roast_weight * roast_sim +
                self.bean_weight * bean_sim +
                self.price_weight * price_sim
        )

        return min(1.0, max(0.0, similarity))

    def calculate_collaborative_score(self, product: Product) -> float:
        """
        Calculate collaborative filtering score using an item-based approach.

        This method estimates the user's interest in a product by looking at
        products they have interacted with in the past and finding how similar
        those products are to the target product based on global user behavior.

        :param product: The product to score.
        :type product: Product
        :return: A score between 0.0 and 1.0.
        :rtype: float
        """
        profile = self.user_profile

        if not profile['interacted_products']:
            return 0.0

        if product.id in profile['interacted_products']:
            return 0.0  # Don't recommend already interacted products

        # Get pre-computed similarities
        similarities = ProductSimilarity.objects.filter(
            product_a_id__in=profile['interacted_products'],
            product_b=product
        ).values_list('product_a_id', 'similarity_score')

        sim_dict = {prod_id: score for prod_id, score in similarities}

        # Calculate weighted score
        weighted_sum = 0.0
        weight_sum = 0.0

        for interacted_id, interaction_score in profile['interaction_scores'].items():
            if interacted_id in sim_dict:
                weighted_sum += interaction_score * sim_dict[interacted_id]
                weight_sum += interaction_score

        if weight_sum > 0:
            return weighted_sum / weight_sum
        return 0.0

    def calculate_popularity_score(self, product: Product) -> float:
        """
        Calculate a popularity score based on purchases and ratings.

        This method normalizes the product's purchase count and review statistics
        against the maximum values in the catalog to produce a relative popularity score.

        :param product: The product to score.
        :type product: Product
        :return: A score between 0.0 and 1.0.
        :rtype: float
        """
        products = self._get_all_products()

        # Get max values for normalization
        max_purchases = max((p.purchase_count or 0) for p in products) or 1
        max_review_score = max(
            ((p.avg_rating or 0) * (p.review_count or 0)) for p in products
        ) or 1

        # Calculate score
        purchase_score = (product.purchase_count or 0) / max_purchases
        review_score = ((product.avg_rating or 0) * (product.review_count or 0)) / max_review_score

        # Weighted combination
        return 0.6 * purchase_score + 0.4 * review_score

    def get_recommendations(
            self, limit: int = 6, exclude_products: Optional[Set[int]] = None) -> List[Dict]:
        """
        Generate personalized recommendations for the user.

        This method combines scores from different algorithms (content-based,
        collaborative, popularity) to produce a final ranked list of products.

        :param limit: The maximum number of recommendations to return.
        :type limit: int
        :param exclude_products: A set of product IDs to exclude from results.
        :type exclude_products: set[int] or None
        :return: A list of dictionaries containing recommended products and their details.
        :rtype: list[dict]
        """
        profile = self.user_profile
        products = self._get_all_products()

        exclude = exclude_products or set()
        exclude.update(profile['interacted_products'])

        recommendations = []

        for product in products:
            if product.id in exclude:
                continue

            # Calculate component scores
            content_score = self.calculate_content_similarity(product)
            collab_score = self.calculate_collaborative_score(product)
            popularity_score = self.calculate_popularity_score(product)

            # Hybrid score
            if profile['interacted_products']:
                # For users with history, use full hybrid
                final_score = (
                        self.content_weight * content_score +
                        self.collaborative_weight * collab_score +
                        self.popularity_weight * popularity_score
                )
                algorithm = 'hybrid'
            else:
                # For new users, rely on popularity
                final_score = popularity_score
                algorithm = 'popular'

            recommendations.append({
                'product': product,
                'score': final_score,
                'algorithm': algorithm,
                'components': {
                    'content': content_score,
                    'collaborative': collab_score,
                    'popularity': popularity_score,
                }
            })

        # Sort by score (descending)
        recommendations.sort(key=lambda x: x['score'], reverse=True)

        # Take top N
        top_recommendations = recommendations[:limit]

        # Log recommendations (async in production)
        self._log_recommendations(top_recommendations)

        return top_recommendations

    def _log_recommendations(self, recommendations: List[Dict]) -> None:
        """Log recommendations for analytics."""
        logs = []
        for position, rec in enumerate(recommendations, 1):
            logs.append(RecommendationLog(
                user=self.user,
                product=rec['product'],
                algorithm=rec['algorithm'],
                score=rec['score'],
                position=position
            ))

        if logs:
            RecommendationLog.objects.bulk_create(logs, ignore_conflicts=True)

    def get_similar_products(self, product: Product, limit: int = 4) -> List[Product]:
        """
        Get products similar to a given product (for "You may also like" section).
        
        Uses pre-computed similarities from ProductSimilarity table.
        """
        similar_ids = ProductSimilarity.objects.filter(
            product_a=product
        ).order_by('-similarity_score').values_list('product_b_id', flat=True)[:limit]

        if similar_ids:
            products = Product.objects.filter(
                id__in=similar_ids, is_active=True
            ).prefetch_related('countries', 'available_bean_types')
            return list(products)

        return []


def record_interaction(user, product, interaction_type: str) -> None:
    """
    Record a user-product interaction.
    
    Call this when:
    - User views a product
    - User adds to cart
    - User completes purchase
    - User favorites a product
    - User reviews a product
    """
    interaction, created = UserProductInteraction.objects.get_or_create(
        user=user,
        product=product,
        interaction_type=interaction_type,
        defaults={'interaction_count': 1}
    )

    if not created:
        interaction.interaction_count += 1
        interaction.save(update_fields=['interaction_count', 'last_interaction'])

    # Invalidate user profile cache
    cache.delete(f'user_profile_{user.id}')


def compute_product_similarities() -> int:
    """
    Compute and store product similarities for all products.
    
    Should be run periodically (e.g., daily) via management command.
    
    Returns: Number of similarity records created/updated
    """
    products = list(
        Product.objects.filter(is_active=True)
        .select_related('roast_level')
        .prefetch_related('countries', 'available_bean_types')
    )

    # Get price range for normalization
    prices = [float(p.base_price) for p in products]
    max_price_diff = max(prices) - min(prices) if prices else 1

    count = 0
    similarities_to_create = []

    for i, product_a in enumerate(products):
        countries_a = set(product_a.countries.values_list('id', flat=True))
        beans_a = set(product_a.available_bean_types.values_list('id', flat=True))
        roast_a = product_a.roast_level_id
        price_a = float(product_a.base_price)

        for product_b in products[i + 1:]:
            countries_b = set(product_b.countries.values_list('id', flat=True))
            beans_b = set(product_b.available_bean_types.values_list('id', flat=True))
            roast_b = product_b.roast_level_id
            price_b = float(product_b.base_price)

            # Calculate similarities
            # Country (Jaccard)
            if countries_a and countries_b:
                country_sim = len(countries_a & countries_b) / len(countries_a | countries_b)
            else:
                country_sim = 0.0

            # Roast (exact match)
            roast_sim = 1.0 if roast_a == roast_b else 0.0

            # Beans (Jaccard)
            if beans_a and beans_b:
                bean_sim = len(beans_a & beans_b) / len(beans_a | beans_b)
            else:
                bean_sim = 0.0

            # Price (normalized distance)
            price_sim = 1 - abs(price_a - price_b) / max_price_diff if max_price_diff > 0 else 1

            # Weighted combination
            similarity = (
                    0.25 * country_sim +
                    0.30 * roast_sim +
                    0.25 * bean_sim +
                    0.20 * price_sim
            )

            # Store both directions
            similarities_to_create.append(ProductSimilarity(
                product_a=product_a,
                product_b=product_b,
                similarity_score=similarity
            ))
            similarities_to_create.append(ProductSimilarity(
                product_a=product_b,
                product_b=product_a,
                similarity_score=similarity
            ))
            count += 2

    # Bulk create/update
    ProductSimilarity.objects.all().delete()
    ProductSimilarity.objects.bulk_create(similarities_to_create)

    return count
