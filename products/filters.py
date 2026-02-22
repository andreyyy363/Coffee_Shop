import django_filters
from .models import Product, Country, RoastLevel, BeanType, Weight


class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name='base_price', lookup_expr='gte', label='Min Price')
    max_price = django_filters.NumberFilter(field_name='base_price', lookup_expr='lte', label='Max Price')

    country = django_filters.ModelMultipleChoiceFilter(
        field_name='countries',
        queryset=Country.objects.all(),
        label='Country'
    )

    roast_level = django_filters.ModelMultipleChoiceFilter(
        queryset=RoastLevel.objects.all(),
        label='Roast Level'
    )

    bean_type = django_filters.ModelMultipleChoiceFilter(
        field_name='available_bean_types',
        queryset=BeanType.objects.all(),
        label='Bean Type'
    )

    weight = django_filters.ModelMultipleChoiceFilter(
        field_name='available_weights',
        queryset=Weight.objects.all(),
        label='Weight'
    )

    ordering = django_filters.OrderingFilter(
        choices=[
            ('base_price', 'Price (Low to High)'),
            ('-base_price', 'Price (High to Low)'),
            ('-created_at', 'Newest'),
        ],
        label='Sort by'
    )

    class Meta:
        model = Product
        fields = ['country', 'roast_level', 'bean_type', 'weight']
