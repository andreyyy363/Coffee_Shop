from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from products.models import Country, RoastLevel, BeanType, Weight, Product
import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates initial data for the coffee shop'

    def handle(self, *args, **options):
        self.stdout.write('Creating initial data...')
        
        # Create countries
        countries_data = ['Brazil', 'Rwanda', 'Uganda', 'Vietnam', 'Colombia', 'Ethiopia', 'Kenya']
        countries = {}
        for name in countries_data:
            country, created = Country.objects.get_or_create(name=name)
            countries[name] = country
            if created:
                self.stdout.write(f'  Created country: {name}')
        
        # Create roast levels
        roast_levels_data = ['Light', 'Medium', 'Dark']
        roast_levels = {}
        for name in roast_levels_data:
            level, created = RoastLevel.objects.get_or_create(name=name)
            roast_levels[name] = level
            if created:
                self.stdout.write(f'  Created roast level: {name}')
        
        # Create bean types
        bean_types_data = ['Ground coffee', 'Coffee beans']
        bean_types = {}
        for name in bean_types_data:
            bean_type, created = BeanType.objects.get_or_create(name=name)
            bean_types[name] = bean_type
            if created:
                self.stdout.write(f'  Created bean type: {name}')
        
        # Create weights
        weights_data = [
            (200, Decimal('1.00')),
            (500, Decimal('2.00')),
            (1000, Decimal('3.50')),
        ]
        weights = {}
        for grams, multiplier in weights_data:
            weight, created = Weight.objects.get_or_create(
                grams=grams,
                defaults={'price_multiplier': multiplier}
            )
            weights[grams] = weight
            if created:
                self.stdout.write(f'  Created weight: {grams}g')
        
        # Create sample products
        products_data = [
            {
                'name': 'Morning magic',
                'slug': 'morning-magic',
                'short_description': 'natural roasted, 1 kg',
                'description': 'A Premium Arabica Blend With A Smooth, Chocolate-Caramel Aroma And Light Fruity Notes. Ideal For Morning Brewing, This Coffee Creates A Balanced Cup With Gentle Acidity And A Long, Sweet Aftertaste. Perfect For Espresso Lovers As Well As Filter Coffee Fans.',
                'taste_profile': 'Caramel Sweetness, Light Citrus Tone, Smooth Chocolate Finish',
                'base_price': '10.00',
                'roast_level': roast_levels['Medium'],
                'countries': [countries['Brazil'], countries['Rwanda'], countries['Uganda']],
            },
            {
                'name': 'European blend',
                'slug': 'european-blend',
                'short_description': 'coffee bean blend',
                'description': 'A classic European-style blend with rich, full-bodied flavor. Perfect for those who enjoy traditional coffee taste.',
                'taste_profile': 'Deep chocolate, nutty undertones, full body',
                'base_price': '10.00',
                'roast_level': roast_levels['Dark'],
                'countries': [countries['Brazil'], countries['Vietnam']],
            },
            {
                'name': 'Ethiopian Sunrise',
                'slug': 'ethiopian-sunrise',
                'short_description': 'single origin, light roast',
                'description': 'A bright and fruity single-origin coffee from the birthplace of coffee. Notes of blueberry and citrus.',
                'taste_profile': 'Blueberry, citrus, floral notes',
                'base_price': '12.00',
                'roast_level': roast_levels['Light'],
                'countries': [countries['Ethiopia']],
            },
            {
                'name': 'Colombian Supreme',
                'slug': 'colombian-supreme',
                'short_description': 'premium quality, medium roast',
                'description': 'Premium Colombian coffee with perfect balance of sweetness and acidity. A crowd favorite.',
                'taste_profile': 'Brown sugar, red apple, smooth finish',
                'base_price': '11.00',
                'roast_level': roast_levels['Medium'],
                'countries': [countries['Colombia']],
            },
            {
                'name': 'Kenya AA',
                'slug': 'kenya-aa',
                'short_description': 'top grade, bright acidity',
                'description': 'Top-grade Kenyan coffee known for its wine-like acidity and complex flavor profile.',
                'taste_profile': 'Blackcurrant, tomato, wine-like acidity',
                'base_price': '14.00',
                'roast_level': roast_levels['Light'],
                'countries': [countries['Kenya']],
            },
        ]
        
        for product_data in products_data:
            product_countries = product_data.pop('countries')
            product, created = Product.objects.get_or_create(
                slug=product_data['slug'],
                defaults=product_data
            )
            if created:
                product.countries.set(product_countries)
                product.available_bean_types.set(bean_types.values())
                product.available_weights.set(weights.values())
                product.save()
                self.stdout.write(f'  Created product: {product.name}')
        
        # Create admin user if not exists
        admin_email = 'admin@kavasoul.com'
        if not User.objects.filter(email=admin_email).exists():
            User.objects.create_superuser(
                email=admin_email,
                password='admin123',
                username='admin'
            )
            self.stdout.write(f'  Created admin user: {admin_email} (password: admin123)')
        
        # Create manager user if not exists
        manager_email = 'manager@kavasoul.com'
        if not User.objects.filter(email=manager_email).exists():
            user = User.objects.create_user(
                email=manager_email,
                password='manager123',
                username='manager',
                role='manager',
                email_verified=True
            )
            self.stdout.write(f'  Created manager user: {manager_email} (password: manager123)')
        
        self.stdout.write(self.style.SUCCESS('Initial data created successfully!'))
