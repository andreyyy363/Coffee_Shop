"""
WSGI config for coffeeshop project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coffeeshop.settings')
application = get_wsgi_application()
