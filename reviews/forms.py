from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    """Form for creating/editing reviews."""
    
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, str(i)) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Your comment (optional)',
                'rows': 3
            })
        }
