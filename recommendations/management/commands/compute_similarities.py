"""
Management command to compute product similarities for the recommendation system.
Should be run periodically (e.g., daily via cron).
"""

from django.core.management.base import BaseCommand
from recommendations.services import compute_product_similarities


class Command(BaseCommand):
    help = 'Compute product similarities for the recommendation engine'
    
    def handle(self, *args, **options):
        self.stdout.write('Computing product similarities...')
        
        count = compute_product_similarities()
        
        self.stdout.write(self.style.SUCCESS(f'Created {count} similarity records'))
