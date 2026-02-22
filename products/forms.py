from django import forms
from .models import Product, Country, RoastLevel, BeanType, Weight


class ProductForm(forms.ModelForm):
    """Form for creating/editing products."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['slug'].required = False

        if not self.instance.pk:
            default_weight = Weight.objects.filter(grams=100).first()
            if default_weight:
                self.initial.setdefault('available_weights', [default_weight.pk])

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            default_weight = Weight.objects.filter(grams=100).first()
            if default_weight:
                instance.available_weights.add(default_weight)
        return instance

    def clean_available_weights(self):
        weights = self.cleaned_data.get('available_weights')
        default_weight = Weight.objects.filter(grams=100).first()
        if not default_weight:
            return weights

        if weights is None:
            return [default_weight]

        if default_weight not in weights:
            weights = list(weights) + [default_weight]

        return weights

    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'image', 'short_description', 'description',
            'taste_profile', 'base_price', 'countries', 'roast_level',
            'available_bean_types', 'available_weights', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'taste_profile': forms.TextInput(attrs={'class': 'form-control'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'countries': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'roast_level': forms.Select(attrs={'class': 'form-select'}),
            'available_bean_types': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'available_weights': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CountryForm(forms.ModelForm):
    class Meta:
        model = Country
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if Country.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(f'Country "{name}" already exists')
        return name


class RoastLevelForm(forms.ModelForm):
    """Form for creating/editing roast levels."""

    class Meta:
        model = RoastLevel
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if RoastLevel.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(f'Roast level "{name}" already exists')
        return name


class BeanTypeForm(forms.ModelForm):
    """Form for creating/editing bean types."""

    class Meta:
        model = BeanType
        fields = ['name', 'price_multiplier']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'price_multiplier': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if BeanType.objects.filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(f'Bean type "{name}" already exists')
        return name


class WeightForm(forms.ModelForm):
    """Form for creating/editing weights."""

    class Meta:
        model = Weight
        fields = ['grams', 'price_multiplier']
        widgets = {
            'grams': forms.NumberInput(attrs={'class': 'form-control'}),
            'price_multiplier': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def clean_grams(self):
        grams = self.cleaned_data['grams']
        if Weight.objects.filter(grams=grams).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(f'Weight {grams}g already exists')
        return grams
