import re

from django import forms
from .models import Order

PHONE_REGEX = re.compile(r'^\+?[0-9\s\-\(\)]{7,20}$')


class CheckoutForm(forms.Form):
    """Form for placing an order."""
    full_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First and Last Name'
        })
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Delivery address',
            'rows': 2
        })
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contact number',
            'pattern': r'\+?[0-9\s\-\(\)]{7,20}',
        })
    )
    payment_type = forms.ChoiceField(
        choices=Order.PAYMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean_full_name(self):
        name = self.cleaned_data.get('full_name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError('Please enter your full name')
        return name

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not PHONE_REGEX.match(phone):
            raise forms.ValidationError('Enter a valid phone number (digits, spaces, dashes, parentheses; 7-20 characters)')
        return phone

    def clean_address(self):
        address = self.cleaned_data.get('address', '').strip()
        if len(address) < 5:
            raise forms.ValidationError('Please enter a valid delivery address')
        return address


class UpdateOrderStatusForm(forms.ModelForm):
    """Form for managers to update order status."""

    class Meta:
        model = Order
        fields = ['status', 'manager_comment']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'manager_comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class UpdateOrderContactForm(forms.ModelForm):
    """Form for managers to update order contact info."""

    class Meta:
        model = Order
        fields = ['full_name', 'address', 'phone']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone and not PHONE_REGEX.match(phone):
            raise forms.ValidationError('Enter a valid phone number')
        return phone
