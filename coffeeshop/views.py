import re

from django.shortcuts import render, redirect, get_object_or_404
from decimal import Decimal
from django.db.models import Sum
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django import forms

from products.models import Product


PHONE_REGEX = re.compile(r'^\+?[0-9\s\-\(\)]{7,20}$')


class ContactForm(forms.Form):
    """Form for the contact page with validation."""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your name',
            'style': 'border-radius: 25px;',
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your email',
            'style': 'border-radius: 25px;',
        })
    )
    subject = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject',
            'style': 'border-radius: 25px;',
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Your message...',
            'style': 'border-radius: 15px;',
        })
    )

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError('Please enter your name (at least 2 characters)')
        return name

    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        if len(message) < 10:
            raise forms.ValidationError('Message must be at least 10 characters long')
        return message


def home(request):
    """Home page view."""
    # Top 20 best-selling products by quantity sold in completed orders
    from orders.models import OrderItem
    top_product_ids = (
        OrderItem.objects
        .filter(order__status='completed', product__isnull=False)
        .values('product_id')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:20]
    )
    top_ids = [item['product_id'] for item in top_product_ids]

    if top_ids:
        products_qs = Product.objects.filter(id__in=top_ids, is_active=True).prefetch_related(
            'countries', 'available_weights', 'reviews'
        )
        id_map = {p.id: p for p in products_qs}
        popular_products = [id_map[pid] for pid in top_ids if pid in id_map]
    else:
        popular_products = list(
            Product.objects.filter(is_active=True).prefetch_related(
                'countries', 'available_weights', 'reviews'
            ).order_by('-created_at')[:20]
        )

    user_favorites = []
    if request.user.is_authenticated:
        user_favorites = list(request.user.favorites.values_list('product_id', flat=True))

    discount_percent = Decimal('0.00')
    if request.user.is_authenticated:
        try:
            from discounts.services import DiscountCalculator
            calculator = DiscountCalculator(request.user)
            discount_info = calculator.calculate_discount(Decimal('100.00'))
            discount_percent = discount_info.get('total_discount_percent', Decimal('0.00'))
        except Exception:
            pass

    return render(request, 'home.html', {
        'popular_products': popular_products,
        'user_favorites': user_favorites,
        'discount_percent': discount_percent,
    })


def contacts(request):
    """Contacts page view — saves contact form submissions."""
    from .models import ContactMessage

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            ContactMessage.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                subject=form.cleaned_data.get('subject', ''),
                message=form.cleaned_data['message'],
            )
            messages.success(request, 'Your message has been sent! We will get back to you soon.')
            return redirect('contacts')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ContactForm()

    return render(request, 'contacts.html', {'form': form})


@login_required
def manager_contact_messages(request):
    """Manager view to see all contact form submissions."""
    if not request.user.is_manager:
        messages.error(request, 'Access denied.')
        return redirect('home')

    from .models import ContactMessage

    contact_messages = ContactMessage.objects.all()
    return render(request, 'manager_contact_messages.html', {
        'contact_messages': contact_messages,
    })


@login_required
def manager_contact_message_detail(request, pk):
    """Manager view — single contact message detail."""
    if not request.user.is_manager:
        messages.error(request, 'Access denied.')
        return redirect('home')

    from .models import ContactMessage

    msg = get_object_or_404(ContactMessage, pk=pk)
    if not msg.is_read:
        msg.is_read = True
        msg.save(update_fields=['is_read'])

    return render(request, 'manager_contact_message_detail.html', {
        'msg': msg,
    })


@login_required
def manager_contact_message_delete(request, pk):
    """Manager view — delete a contact message."""
    if not request.user.is_manager:
        messages.error(request, 'Access denied.')
        return redirect('home')

    from .models import ContactMessage

    msg = get_object_or_404(ContactMessage, pk=pk)
    msg.delete()
    messages.success(request, 'Message deleted.')
    return redirect('manager_contact_messages')
