from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Review
from .forms import ReviewForm
from products.models import Product


@login_required
@require_POST
def add_review(request, product_id):
    """Add review for a product."""
    product = get_object_or_404(Product, pk=product_id)
    
    # Check if user already reviewed
    if Review.objects.filter(user=request.user, product=product).exists():
        messages.error(request, 'You have already reviewed this product')
        return redirect('products:detail', slug=product.slug)
    
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.product = product
        review.save()
        messages.success(request, 'Your review has been added!')
    else:
        messages.error(request, 'Please select a rating')
    
    return redirect('products:detail', slug=product.slug)


@login_required
@require_POST
def update_review(request, review_id):
    """Update existing review."""
    review = get_object_or_404(Review, pk=review_id, user=request.user)
    
    form = ReviewForm(request.POST, instance=review)
    if form.is_valid():
        form.save()
        messages.success(request, 'Review updated')
    else:
        messages.error(request, 'Please correct the errors in your review')
    
    return redirect('products:detail', slug=review.product.slug)


@login_required
@require_POST
def delete_review(request, review_id):
    """Delete review."""
    review = get_object_or_404(Review, pk=review_id)
    
    # Allow owner or manager to delete
    if review.user != request.user and not request.user.is_manager:
        messages.error(request, 'Access denied')
        return redirect('products:detail', slug=review.product.slug)
    
    product_slug = review.product.slug
    review.delete()
    messages.success(request, 'Review deleted')
    
    return redirect('products:detail', slug=product_slug)


# Manager views
def manager_required(view_func):
    """Decorator to check if user is manager."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_manager:
            messages.error(request, 'Access denied')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


@manager_required
def manager_reviews(request):
    """Display all reviews for managers."""
    reviews = Review.objects.all().select_related('user', 'product').order_by('-created_at')
    
    # Filter by approval status
    approved = request.GET.get('approved')
    if approved == '1':
        reviews = reviews.filter(is_approved=True)
    elif approved == '0':
        reviews = reviews.filter(is_approved=False)
    
    return render(request, 'reviews/manager_reviews.html', {
        'reviews': reviews,
        'current_filter': approved,
    })


@manager_required
@require_POST
def toggle_review_approval(request, review_id):
    """Toggle review approval status."""
    review = get_object_or_404(Review, pk=review_id)
    review.is_approved = not review.is_approved
    review.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'is_approved': review.is_approved})
    
    messages.success(request, 'Review status changed')
    return redirect('reviews:manager_reviews')
