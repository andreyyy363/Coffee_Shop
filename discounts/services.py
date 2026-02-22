"""
Discount Calculation Service.

Personal discount system based on RFM (Recency, Frequency, Monetary) analysis.
Scores each customer on three dimensions, combines them into a weighted score,
and maps that score to a discount percentage via a configurable curve.
Supports additional bonuses for first purchase and birthday,
as well as promo code validation.
"""
from datetime import datetime
from typing import Dict, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from django.db.models import Sum

from .models import DiscountSettings, CustomerDiscount, PromoCode, PromoCodeUsage, DiscountHistory


class DiscountCalculator:
    """
    Service class for calculating personal discounts.
    
    Usage:
        calculator = DiscountCalculator(user)
        discount_info = calculator.calculate_discount(order_total)
    """

    def __init__(self, user):
        self.user = user
        self.settings = DiscountSettings.get_settings()
        self._customer_profile = None

    @property
    def customer_profile(self) -> CustomerDiscount:
        """Get or create customer discount profile."""
        if self._customer_profile is None:
            self._customer_profile, _ = CustomerDiscount.objects.get_or_create(
                user=self.user
            )
        return self._customer_profile

    def recalculate_customer_metrics(self) -> CustomerDiscount:
        """
        Recalculate customer metrics from order history.
        Should be called after each completed order.
        """
        from orders.models import Order

        profile = self.customer_profile

        # Get completed orders
        completed_orders = Order.objects.filter(
            user=self.user,
            status='completed'
        )

        # Calculate raw metrics
        profile.total_orders = completed_orders.count()
        profile.total_spent = completed_orders.aggregate(
            total_sum=Sum('total')
        )['total_sum'] or Decimal('0.00')

        last_order = completed_orders.order_by('-created_at').first()
        profile.last_order_date = last_order.created_at if last_order else None

        # Calculate normalized scores
        profile.recency_score = self._calculate_recency_score(profile.last_order_date)
        profile.frequency_score = self._calculate_frequency_score(profile.total_orders)
        profile.monetary_score = self._calculate_monetary_score(profile.total_spent)

        # Calculate weighted RFM score
        profile.rfm_score = self._calculate_rfm_score(
            profile.recency_score,
            profile.frequency_score,
            profile.monetary_score
        )

        # Calculate base discount from RFM
        profile.base_discount_percent = self._calculate_discount_from_rfm(profile.rfm_score)

        profile.save()
        return profile

    def _calculate_recency_score(self, last_order_date: Optional[datetime]) -> Decimal:
        """
        Calculate recency score (R).

        Returns a value between 0 and 1 that decreases linearly as time
        passes since the last order.

        :param last_order_date: Datetime of the user's last order, or None.
        :type last_order_date: datetime or None
        :return: Recency score between 0 and 1.
        :rtype: Decimal
        """
        if last_order_date is None:
            return Decimal('0.000')

        now = timezone.now()
        days_since = (now - last_order_date).days
        max_days = self.settings.recency_max_days

        if days_since >= max_days:
            return Decimal('0.000')

        score = Decimal(str(1 - days_since / max_days))
        return score.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

    def _calculate_frequency_score(self, total_orders: int) -> Decimal:
        """
        Calculate frequency score (F).

        Returns a value between 0 and 1 that increases linearly
        up to the target, then stays at 1.

        :param total_orders: Total number of completed orders.
        :type total_orders: int
        :return: Frequency score between 0 and 1.
        :rtype: Decimal
        """
        target = self.settings.frequency_target
        score = min(1.0, total_orders / target)
        return Decimal(str(score)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

    def _calculate_monetary_score(self, total_spent: Decimal) -> Decimal:
        """
        Calculate monetary score (M).

        Returns a value between 0 and 1 that increases linearly
        up to the target, then stays at 1.

        :param total_spent: Total amount spent by the customer.
        :type total_spent: Decimal
        :return: Monetary score between 0 and 1.
        :rtype: Decimal
        """
        target = self.settings.monetary_target
        if target == 0:
            return Decimal('0.000')

        score = min(Decimal('1.000'), total_spent / target)
        return score.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

    def _calculate_rfm_score(
            self,
            recency: Decimal,
            frequency: Decimal,
            monetary: Decimal
    ) -> Decimal:
        """
        Calculate the weighted RFM score.

        Combines recency, frequency, and monetary scores using
        configurable weights that must sum to 1.

        :param recency: Recency score (0 to 1).
        :type recency: Decimal
        :param frequency: Frequency score (0 to 1).
        :type frequency: Decimal
        :param monetary: Monetary score (0 to 1).
        :type monetary: Decimal
        :return: Combined RFM score between 0 and 1.
        :rtype: Decimal
        """
        w1 = self.settings.weight_recency
        w2 = self.settings.weight_frequency
        w3 = self.settings.weight_monetary

        rfm = w1 * recency + w2 * frequency + w3 * monetary
        return rfm.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

    def _calculate_discount_from_rfm(self, rfm_score: Decimal) -> Decimal:
        """
        Calculate discount percentage from RFM score.

        Uses a configurable power curve to map RFM score to discount.
        The curve exponent controls how quickly discounts grow with engagement.

        :param rfm_score: Combined RFM score (0 to 1).
        :type rfm_score: Decimal
        :return: Discount percentage.
        :rtype: Decimal
        """
        base = float(self.settings.base_discount_rate)
        max_rate = float(self.settings.max_discount_rate)
        alpha = float(self.settings.curve_exponent)
        rfm = float(rfm_score)

        # Apply power function
        discount = base + (max_rate - base) * (rfm ** alpha)

        return Decimal(str(discount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def check_first_purchase_bonus(self) -> Decimal:
        """
        Check if user is eligible for the first purchase bonus.

        :return: Discount percentage if eligible, otherwise 0.
        :rtype: Decimal
        """
        from orders.models import Order

        has_orders = Order.objects.filter(
            user=self.user,
            status='completed'
        ).exists()

        if not has_orders:
            return self.settings.first_purchase_discount
        return Decimal('0.00')

    def check_birthday_bonus(self) -> Decimal:
        """
        Check if user is eligible for a birthday bonus.

        :return: Discount percentage if birthday is within the configured range, otherwise 0.
        :rtype: Decimal
        """
        if not hasattr(self.user, 'birth_date') or not self.user.birth_date:
            return Decimal('0.00')

        today = timezone.now().date()
        birth_date = self.user.birth_date

        # Create this year's birthday date
        try:
            this_year_birthday = birth_date.replace(year=today.year)
        except ValueError:
            # Handle Feb 29 for non-leap years
            this_year_birthday = birth_date.replace(year=today.year, day=28)

        days_until = abs((this_year_birthday - today).days)

        # Check if within range
        if days_until <= self.settings.birthday_discount_days:
            return self.settings.birthday_discount

        # Also check previous/next year boundaries
        try:
            last_year_birthday = birth_date.replace(year=today.year - 1)
            if abs((last_year_birthday - today).days) <= self.settings.birthday_discount_days:
                return self.settings.birthday_discount
        except ValueError:
            pass

        return Decimal('0.00')

    def validate_promo_code(self, code: str) -> Tuple[bool, str, Optional[PromoCode]]:
        """
        Validate a promo code for the current user.

        :param code: The promo code string to validate.
        :type code: str
        :return: A tuple of (is_valid, message, promo_code_object).
        :rtype: tuple[bool, str, PromoCode or None]
        """
        try:
            promo = PromoCode.objects.get(code__iexact=code)
        except PromoCode.DoesNotExist:
            return False, 'Invalid promo code', None

        if not promo.is_active:
            return False, 'This promo code is no longer active', None

        now = timezone.now()
        if now < promo.valid_from:
            return False, 'This promo code is not yet valid', None
        if now > promo.valid_until:
            return False, 'This promo code has expired', None

        if promo.max_uses and promo.times_used >= promo.max_uses:
            return False, 'This promo code has reached its usage limit', None

        # Check per-user limit
        user_uses = PromoCodeUsage.objects.filter(
            promo_code=promo,
            user=self.user
        ).count()

        if user_uses >= promo.max_uses_per_user:
            return False, 'You have already used this promo code', None

        return True, 'Promo code is valid', promo

    def calculate_discount(
            self,
            order_total: Decimal,
            promo_code: Optional[str] = None
    ) -> Dict:
        """
        Calculate the complete discount for an order.

        :param order_total: The order subtotal before discounts.
        :type order_total: Decimal
        :param promo_code: Optional promo code string to apply.
        :type promo_code: str or None
        :return: A dictionary with all discount information.
        :rtype: dict
        """
        if not self.settings.is_active:
            return {
                'is_active': False,
                'total_discount_percent': Decimal('0.00'),
                'total_discount_amount': Decimal('0.00'),
                'final_amount': order_total,
                'breakdown': [],
            }

        breakdown = []
        total_percent = Decimal('0.00')

        # Recalculate metrics first
        profile = self.recalculate_customer_metrics()

        # 1. RFM-based personal discount
        rfm_discount = profile.base_discount_percent
        if rfm_discount > 0:
            breakdown.append({
                'type': 'rfm',
                'name': 'Personal Discount',
                'percent': rfm_discount,
                'details': {
                    'rfm_score': float(profile.rfm_score),
                    'recency_score': float(profile.recency_score),
                    'frequency_score': float(profile.frequency_score),
                    'monetary_score': float(profile.monetary_score),
                    'total_orders': profile.total_orders,
                    'total_spent': float(profile.total_spent),
                }
            })
            total_percent += rfm_discount

        # 2. First purchase bonus (mutually exclusive with RFM)
        if rfm_discount == 0:
            first_purchase = self.check_first_purchase_bonus()
            if first_purchase > 0:
                breakdown.append({
                    'type': 'first_purchase',
                    'name': 'First Purchase Bonus',
                    'percent': first_purchase,
                    'details': {}
                })
                total_percent += first_purchase

        # 3. Birthday bonus (additive)
        birthday_bonus = self.check_birthday_bonus()
        if birthday_bonus > 0:
            breakdown.append({
                'type': 'birthday',
                'name': 'Birthday Bonus',
                'percent': birthday_bonus,
                'details': {'birth_date': str(self.user.birth_date) if hasattr(self.user, 'birth_date') else None}
            })
            total_percent += birthday_bonus

        # Apply max discount cap
        max_discount = self.settings.max_total_discount
        if total_percent > max_discount:
            total_percent = max_discount

        # Calculate amount
        total_discount_amount = (order_total * total_percent / 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        # 4. Promo code (applied after percentage discounts)
        promo_discount_amount = Decimal('0.00')
        promo_obj = None

        if promo_code:
            is_valid, message, promo_obj = self.validate_promo_code(promo_code)
            if is_valid and promo_obj:
                # Check min order amount (on original total)
                if order_total >= promo_obj.min_order_amount:
                    if promo_obj.discount_type == 'percent':
                        promo_discount_amount = (
                                order_total * promo_obj.discount_value / 100
                        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    else:
                        promo_discount_amount = promo_obj.discount_value

                    breakdown.append({
                        'type': 'promo',
                        'name': f'Promo Code: {promo_obj.code}',
                        'amount': promo_discount_amount,
                        'details': {
                            'code': promo_obj.code,
                            'discount_type': promo_obj.discount_type,
                            'discount_value': float(promo_obj.discount_value),
                        }
                    })

        # Final calculations
        total_discount_amount += promo_discount_amount
        final_amount = order_total - total_discount_amount

        # Ensure we don't go below zero
        if final_amount < 0:
            final_amount = Decimal('0.00')
            total_discount_amount = order_total

        # Build promo display info for templates
        promo_display = None
        if promo_obj and promo_discount_amount > 0:
            promo_display = {
                'code': promo_obj.code,
                'discount_type': promo_obj.discount_type,
                'discount_value': promo_obj.discount_value,
                'discount_amount': promo_discount_amount,
            }

        return {
            'is_active': True,
            'total_discount_percent': total_percent,
            'total_discount_amount': total_discount_amount,
            'promo_discount_amount': promo_discount_amount,
            'final_amount': final_amount,
            'original_amount': order_total,
            'breakdown': breakdown,
            'promo_display': promo_display,
            'rfm_score': float(profile.rfm_score),
            'promo_code_valid': promo_obj is not None,
        }

    def save_discount_history(self, order, discount_info: Dict) -> None:
        """
        Save discount application history for an order.

        :param order: The order to record discount history for.
        :type order: Order
        :param discount_info: Discount calculation result from calculate_discount.
        :type discount_info: dict
        """
        for item in discount_info['breakdown']:
            if item['type'] == 'promo':
                discount_amount = item.get('amount', Decimal('0.00'))
                discount_percent = Decimal('0.00')
            else:
                discount_percent = item.get('percent', Decimal('0.00'))
                # Calculate proportional amount
                if discount_info['total_discount_percent'] > 0:
                    ratio = discount_percent / discount_info['total_discount_percent']
                    discount_amount = (
                                              discount_info['total_discount_amount'] - discount_info.get(
                                          'promo_discount_amount', Decimal('0.00'))
                                      ) * ratio
                else:
                    discount_amount = Decimal('0.00')

            DiscountHistory.objects.create(
                order=order,
                user=self.user,
                discount_type=item['type'],
                discount_percent=discount_percent,
                discount_amount=discount_amount.quantize(Decimal('0.01')),
                rfm_score_snapshot=Decimal(str(discount_info.get('rfm_score', 0))),
                calculation_details=item.get('details', {})
            )


def get_discount_curve_data(settings: DiscountSettings = None) -> list:
    """
    Generate data points for visualizing the discount curve.

    :param settings: Discount settings instance; uses global settings if None.
    :type settings: DiscountSettings or None
    :return: A list of dicts with 'rfm_score' and 'discount_percent' keys.
    :rtype: list[dict]
    """
    if settings is None:
        settings = DiscountSettings.get_settings()

    base = float(settings.base_discount_rate)
    max_rate = float(settings.max_discount_rate)
    alpha = float(settings.curve_exponent)

    data = []
    for i in range(101):
        rfm = i / 100
        discount = base + (max_rate - base) * (rfm ** alpha)
        data.append({
            'rfm_score': rfm,
            'discount_percent': round(discount, 2)
        })

    return data
