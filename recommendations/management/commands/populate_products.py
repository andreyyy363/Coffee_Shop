"""
Management command to populate the database with sample coffee products.
Generates diverse products for testing the recommendation system.
"""

import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from products.models import Product, Country, RoastLevel, BeanType, Weight


class Command(BaseCommand):
    help = 'Populate database with sample coffee products for recommendation testing'
    
    COFFEE_PRODUCTS = [
        # Ethiopian coffees
        {'name': 'Yirgacheffe Supreme', 'country': 'Ethiopia', 'roast': 'Light', 'desc': 'Floral notes with bright citrus acidity', 'price': '18.50'},
        {'name': 'Sidamo Natural', 'country': 'Ethiopia', 'roast': 'Medium', 'desc': 'Berry-forward with wine-like complexity', 'price': '19.00'},
        {'name': 'Harrar Wild', 'country': 'Ethiopia', 'roast': 'Medium', 'desc': 'Blueberry and dark chocolate notes', 'price': '21.00'},
        {'name': 'Guji Highland', 'country': 'Ethiopia', 'roast': 'Light', 'desc': 'Stone fruit and jasmine aromatics', 'price': '22.50'},
        
        # Colombian coffees
        {'name': 'Huila Reserva', 'country': 'Colombia', 'roast': 'Medium', 'desc': 'Caramel sweetness with nutty finish', 'price': '16.50'},
        {'name': 'Nariño Especial', 'country': 'Colombia', 'roast': 'Medium', 'desc': 'Balanced with red apple notes', 'price': '17.00'},
        {'name': 'Supremo Classic', 'country': 'Colombia', 'roast': 'Dark', 'desc': 'Bold body with chocolate undertones', 'price': '15.00'},
        {'name': 'Sierra Nevada', 'country': 'Colombia', 'roast': 'Light', 'desc': 'Citrus brightness with honey sweetness', 'price': '18.00'},
        
        # Brazilian coffees
        {'name': 'Santos Premium', 'country': 'Brazil', 'roast': 'Medium', 'desc': 'Smooth nutty flavor with low acidity', 'price': '14.00'},
        {'name': 'Cerrado Gold', 'country': 'Brazil', 'roast': 'Dark', 'desc': 'Rich chocolate and roasted nuts', 'price': '15.50'},
        {'name': 'Mogiana Estate', 'country': 'Brazil', 'roast': 'Medium', 'desc': 'Sweet caramel with toasted almond', 'price': '16.00'},
        {'name': 'Sul de Minas', 'country': 'Brazil', 'roast': 'Light', 'desc': 'Delicate citrus with brown sugar', 'price': '17.50'},
        
        # Kenyan coffees
        {'name': 'Kenya AA Plus', 'country': 'Kenya', 'roast': 'Light', 'desc': 'Blackcurrant and grapefruit explosion', 'price': '24.00'},
        {'name': 'Nyeri Peaberry', 'country': 'Kenya', 'roast': 'Medium', 'desc': 'Concentrated flavor with tomato acidity', 'price': '26.00'},
        {'name': 'Kiambu Estate', 'country': 'Kenya', 'roast': 'Light', 'desc': 'Wine-like body with berry finish', 'price': '23.50'},
        
        # Costa Rican coffees
        {'name': 'Tarrazú Reserve', 'country': 'Costa Rica', 'roast': 'Medium', 'desc': 'Bright acidity with honey notes', 'price': '19.50'},
        {'name': 'West Valley', 'country': 'Costa Rica', 'roast': 'Light', 'desc': 'Tropical fruit with floral hints', 'price': '20.00'},
        {'name': 'Dota Estate', 'country': 'Costa Rica', 'roast': 'Medium', 'desc': 'Brown sugar with citrus zest', 'price': '18.50'},
        
        # Indonesian coffees  
        {'name': 'Sumatra Mandheling', 'country': 'Indonesia', 'roast': 'Dark', 'desc': 'Earthy and full-bodied with herbal notes', 'price': '17.00'},
        {'name': 'Java Estate', 'country': 'Indonesia', 'roast': 'Medium', 'desc': 'Spicy with rustic sweetness', 'price': '18.00'},
        {'name': 'Sulawesi Toraja', 'country': 'Indonesia', 'roast': 'Dark', 'desc': 'Complex spice and dark chocolate', 'price': '20.00'},
        
        # Guatemala coffees
        {'name': 'Antigua Valley', 'country': 'Guatemala', 'roast': 'Medium', 'desc': 'Smoky with cocoa and spice', 'price': '17.50'},
        {'name': 'Huehuetenango', 'country': 'Guatemala', 'roast': 'Light', 'desc': 'Fruity complexity with wine notes', 'price': '19.00'},
        {'name': 'Cobán Highland', 'country': 'Guatemala', 'roast': 'Medium', 'desc': 'Balanced with mild fruit tones', 'price': '16.50'},
        
        # Blends
        {'name': 'House Blend Classic', 'country': 'Brazil', 'roast': 'Medium', 'desc': 'Everyday excellence, smooth and balanced', 'price': '12.50', 'blend': ['Brazil', 'Colombia']},
        {'name': 'Espresso Perfetto', 'country': 'Brazil', 'roast': 'Dark', 'desc': 'Rich crema, intense flavor', 'price': '14.00', 'blend': ['Brazil', 'Indonesia']},
        {'name': 'Morning Sunrise', 'country': 'Ethiopia', 'roast': 'Light', 'desc': 'Bright and energizing blend', 'price': '15.00', 'blend': ['Ethiopia', 'Kenya']},
        {'name': 'African Safari', 'country': 'Kenya', 'roast': 'Medium', 'desc': 'Bold African flavors combined', 'price': '21.00', 'blend': ['Kenya', 'Ethiopia']},
        {'name': 'Latin Lover', 'country': 'Colombia', 'roast': 'Medium', 'desc': 'Best of Central and South America', 'price': '16.00', 'blend': ['Colombia', 'Guatemala', 'Costa Rica']},
        
        # Specialty/Limited
        {'name': 'Geisha Panama', 'country': 'Costa Rica', 'roast': 'Light', 'desc': 'Legendary variety, jasmine and bergamot', 'price': '45.00'},
        {'name': 'Kona Hawaiian', 'country': 'Brazil', 'roast': 'Medium', 'desc': 'Rare Hawaiian beans, nutty and smooth', 'price': '38.00'},
        {'name': 'Jamaica Blue Mountain', 'country': 'Colombia', 'roast': 'Medium', 'desc': 'Legendary smoothness, mild and sweet', 'price': '42.00'},
    ]
    
    def handle(self, *args, **options):
        self.stdout.write('Starting database population...')
        
        # Create countries if they don't exist
        countries = {}
        country_names = ['Ethiopia', 'Colombia', 'Brazil', 'Kenya', 'Costa Rica', 'Indonesia', 'Guatemala']
        for name in country_names:
            country, created = Country.objects.get_or_create(name=name)
            countries[name] = country
            if created:
                self.stdout.write(f'  Created country: {name}')
        
        # Create roast levels if they don't exist
        roast_levels = {}
        for name in ['Light', 'Medium', 'Dark']:
            roast, created = RoastLevel.objects.get_or_create(name=name)
            roast_levels[name] = roast
            if created:
                self.stdout.write(f'  Created roast level: {name}')
        
        # Create bean types if they don't exist
        bean_types = []
        bean_names = ['Whole Beans', 'Ground', 'Espresso Ground', 'French Press Ground']
        for name in bean_names:
            bean, created = BeanType.objects.get_or_create(
                name=name,
                defaults={'price_multiplier': Decimal('1.00') if 'Whole' in name else Decimal('1.05')}
            )
            bean_types.append(bean)
            if created:
                self.stdout.write(f'  Created bean type: {name}')
        
        # Create weights if they don't exist
        weights = []
        weight_configs = [
            (250, Decimal('1.00')),
            (500, Decimal('1.90')),
            (1000, Decimal('3.60')),
        ]
        for grams, multiplier in weight_configs:
            weight, created = Weight.objects.get_or_create(
                grams=grams,
                defaults={'price_multiplier': multiplier}
            )
            weights.append(weight)
            if created:
                self.stdout.write(f'  Created weight: {grams}g')
        
        # Create products
        created_count = 0
        for product_data in self.COFFEE_PRODUCTS:
            # Check if product already exists
            if Product.objects.filter(name=product_data['name']).exists():
                self.stdout.write(f'  Product already exists: {product_data["name"]}')
                continue
            
            product = Product.objects.create(
                name=product_data['name'],
                slug=slugify(product_data['name']),
                description=f"{product_data['desc']}. Premium quality coffee beans sourced directly from {product_data['country']}. Perfect for coffee enthusiasts who appreciate exceptional flavor profiles.",
                short_description=product_data['desc'],
                base_price=Decimal(product_data['price']),
                roast_level=roast_levels[product_data['roast']],
                is_active=True,
            )
            
            # Add countries
            if 'blend' in product_data:
                for country_name in product_data['blend']:
                    product.countries.add(countries[country_name])
            else:
                product.countries.add(countries[product_data['country']])
            
            # Add all bean types and weights
            product.available_bean_types.set(bean_types)
            product.available_weights.set(weights)
            
            created_count += 1
            self.stdout.write(f'  Created product: {product.name}')
        
        self.stdout.write(self.style.SUCCESS(f'\nCreated {created_count} new products'))
        self.stdout.write(self.style.SUCCESS(f'Total products in database: {Product.objects.count()}'))
