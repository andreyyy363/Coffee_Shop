from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Avg, Count, F
from django.db import models
from django.core.paginator import Paginator
from decimal import Decimal
from django.utils.text import slugify

from .models import Product, Favorite, Country, RoastLevel, BeanType, Weight
from .filters import ProductFilter
from reviews.models import Review


def catalog_view(request):
    """Display product catalog with filters."""
    products = Product.objects.filter(is_active=True).prefetch_related(
        'countries', 'available_bean_types', 'available_weights', 'reviews'
    ).annotate(
        annotated_avg_rating=Avg('reviews__rating', filter=models.Q(reviews__is_approved=True)),
        annotated_reviews_count=Count('reviews', filter=models.Q(reviews__is_approved=True))
    )
    
    # Apply filters
    product_filter = ProductFilter(request.GET, queryset=products)
    products = product_filter.qs
    
    # Sorting
    sort = request.GET.get('sort', '-created_at')
    if sort == 'price_asc':
        products = products.order_by('base_price')
    elif sort == 'price_desc':
        products = products.order_by('-base_price')
    elif sort == 'rating':
        products = products.order_by(F('annotated_avg_rating').desc(nulls_last=True))
    else:
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)

    # Build querystring without page param (for pagination links)
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    querystring = query_params.urlencode()
    
    # Get filter options
    countries = Country.objects.all()
    roast_levels = RoastLevel.objects.all()
    bean_types = BeanType.objects.all()
    weights = Weight.objects.all()
    
    # Get user favorites for display
    user_favorites = []
    if request.user.is_authenticated:
        user_favorites = list(request.user.favorites.values_list('product_id', flat=True))
    
    # Get user's discount percent
    discount_percent = Decimal('0.00')
    if request.user.is_authenticated:
        try:
            from discounts.services import DiscountCalculator
            calculator = DiscountCalculator(request.user)
            # Get base discount (without promo codes)
            discount_info = calculator.calculate_discount(Decimal('100.00'))
            discount_percent = discount_info.get('total_discount_percent', Decimal('0.00'))
        except Exception:
            pass
    
    # Get personalized recommendations for authenticated users
    recommendations = []
    if request.user.is_authenticated:
        try:
            from recommendations.services import RecommendationEngine
            engine = RecommendationEngine(request.user)
            recommendations = engine.get_recommendations(limit=6)
        except Exception:
            pass
    
    context = {
        'products': products_page,
        'filter': product_filter,
        'countries': countries,
        'roast_levels': roast_levels,
        'bean_types': bean_types,
        'weights': weights,
        'user_favorites': user_favorites,
        'current_sort': sort,
        'discount_percent': discount_percent,
        'recommendations': recommendations,
        'querystring': querystring,
        'selected_countries': request.GET.getlist('country'),
        'selected_roast_levels': request.GET.getlist('roast_level'),
        'selected_bean_types': request.GET.getlist('bean_type'),
        'selected_weights': request.GET.getlist('weight'),
    }
    
    return render(request, 'products/catalog.html', context)


# Need to import models for the Q object
from django.db import models


def product_detail(request, slug):
    """Display product detail page."""
    product = get_object_or_404(
        Product.objects.prefetch_related(
            'countries', 'available_bean_types', 'available_weights',
            'reviews__user'
        ),
        slug=slug, is_active=True
    )
    
    # Track view interaction for recommendations
    if request.user.is_authenticated:
        try:
            from recommendations.services import record_interaction
            record_interaction(request.user, product, 'view')
        except Exception:
            pass
    
    # Get approved reviews
    reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
    
    # Check if user can review
    can_review = False
    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(user=request.user, product=product).first()
        can_review = user_review is None
    
    # Check if product is in favorites
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, product=product).exists()
    
    # Get user's discount info
    discount_percent = Decimal('0.00')
    if request.user.is_authenticated:
        try:
            from discounts.services import DiscountCalculator
            calculator = DiscountCalculator(request.user)
            # Get base discount (without promo codes)
            discount_info = calculator.calculate_discount(product.base_price)
            discount_percent = discount_info.get('total_discount_percent', Decimal('0.00'))
        except Exception:
            pass
    
    context = {
        'product': product,
        'reviews': reviews,
        'can_review': can_review,
        'user_review': user_review,
        'is_favorite': is_favorite,
        'discount_percent': discount_percent,
    }
    
    return render(request, 'products/product_detail.html', context)


@login_required
def toggle_favorite(request, product_id):
    """Add or remove product from favorites."""
    product = get_object_or_404(Product, pk=product_id)
    
    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if not created:
        favorite.delete()
        is_favorite = False
        message = 'Removed from favorites'
    else:
        is_favorite = True
        message = 'Added to favorites'
        
        # Track favorite interaction for recommendations
        try:
            from recommendations.services import record_interaction
            record_interaction(request.user, product, 'favorite')
        except Exception:
            pass
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'is_favorite': is_favorite, 'message': message})
    
    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'products:catalog'))


@login_required
def favorites_view(request):
    """Display user's favorite products."""
    favorites = Favorite.objects.filter(user=request.user).select_related(
        'product__roast_level'
    ).prefetch_related(
        'product__countries', 'product__available_weights'
    ).order_by('-created_at')

    discount_percent = Decimal('0.00')
    try:
        from discounts.services import DiscountCalculator
        calculator = DiscountCalculator(request.user)
        discount_info = calculator.calculate_discount(Decimal('100.00'))
        discount_percent = discount_info.get('total_discount_percent', Decimal('0.00'))
    except Exception:
        pass

    return render(request, 'products/favorites.html', {
        'favorites': favorites,
        'discount_percent': discount_percent,
    })


def search_products(request):
    """Search products by name."""
    query = request.GET.get('q', '')
    products = []
    
    if query:
        products = Product.objects.filter(
            is_active=True,
            name__icontains=query
        ).prefetch_related('countries', 'reviews').annotate(
            annotated_avg_rating=Avg('reviews__rating', filter=models.Q(reviews__is_approved=True))
        )[:20]
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        results = [{
            'id': p.id,
            'name': p.name,
            'slug': p.slug,
            'image': p.image.url if p.image else '',
            'price': str(p.base_price),
            'countries': p.countries_display,
        } for p in products]
        return JsonResponse({'results': results})

    discount_percent = Decimal('0.00')
    if request.user.is_authenticated:
        try:
            from discounts.services import DiscountCalculator
            calculator = DiscountCalculator(request.user)
            discount_info = calculator.calculate_discount(Decimal('100.00'))
            discount_percent = discount_info.get('total_discount_percent', Decimal('0.00'))
        except Exception:
            pass
    
    return render(request, 'products/search_results.html', {
        'products': products,
        'query': query,
        'discount_percent': discount_percent,
    })


# ============== Manager Views ==============

def manager_required(view_func):
    """Decorator to check if user is manager."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_manager:
            messages.error(request, 'Access denied')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


from .forms import ProductForm, CountryForm, RoastLevelForm, BeanTypeForm, WeightForm


@manager_required
def manager_products(request):
    """List all products for manager."""
    products = Product.objects.all().select_related('roast_level').prefetch_related(
        'countries'
    ).order_by('-created_at')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        products = products.filter(name__icontains=search)
    
    # Filter by active status
    active = request.GET.get('active')
    if active == '1':
        products = products.filter(is_active=True)
    elif active == '0':
        products = products.filter(is_active=False)
    
    paginator = Paginator(products, 20)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)
    
    return render(request, 'products/manager/product_list.html', {
        'products': products_page,
        'search': search,
        'current_active': active,
    })


@manager_required
def manager_product_create(request):
    """Create new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            if not product.slug:
                product.slug = generate_unique_slug(product.name)
            product.save()
            form.save_m2m()
            messages.success(request, f'Product "{product.name}" created successfully')
            return redirect('products:manager_products')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = ProductForm()
    
    return render(request, 'products/manager/product_form.html', {
        'form': form,
        'title': 'Create Product',
    })


@manager_required
def manager_product_edit(request, pk):
    """Edit existing product."""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save(commit=False)
            if not product.slug:
                product.slug = generate_unique_slug(product.name, exclude_pk=product.pk)
            product.save()
            form.save_m2m()
            messages.success(request, f'Product "{product.name}" updated successfully')
            return redirect('products:manager_products')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'products/manager/product_form.html', {
        'form': form,
        'product': product,
        'title': 'Edit Product',
    })


@manager_required
def manager_product_delete(request, pk):
    """Delete product."""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" deleted successfully')
        return redirect('products:manager_products')
    
    return render(request, 'products/manager/product_confirm_delete.html', {
        'product': product,
    })


def generate_unique_slug(name, exclude_pk=None):
    base_slug = slugify(name) or 'product'
    slug = base_slug
    counter = 1
    existing = Product.objects.all()
    if exclude_pk is not None:
        existing = existing.exclude(pk=exclude_pk)
    while existing.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


@manager_required
def manager_product_toggle(request, pk):
    """Toggle product active status."""
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save()
    
    status = 'activated' if product.is_active else 'deactivated'
    messages.success(request, f'Product "{product.name}" {status}')
    
    return redirect(request.META.get('HTTP_REFERER', 'products:manager_products'))


# ============== Reference Data Management ==============

@manager_required
def manager_countries(request):
    """Manage countries."""
    countries = Country.objects.all().order_by('name')
    form = CountryForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            form = CountryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Country added successfully')
                return redirect('products:manager_countries')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
                return redirect('products:manager_countries')

        elif action == 'edit':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(Country, pk=item_id)
            new_name = request.POST.get('new_name', '').strip()
            if not new_name:
                messages.error(request, 'Name cannot be empty')
            elif Country.objects.filter(name__iexact=new_name).exclude(pk=item.pk).exists():
                messages.error(request, f'Country "{new_name}" already exists')
            else:
                item.name = new_name
                item.save()
                messages.success(request, 'Country updated successfully')
            return redirect('products:manager_countries')

        elif action == 'delete':
            country_id = request.POST.get('country_id')
            country = get_object_or_404(Country, pk=country_id)
            country.delete()
            messages.success(request, 'Country deleted successfully')
            return redirect('products:manager_countries')

    return render(request, 'products/manager/reference_list.html', {
        'items': countries,
        'form': form,
        'title': 'Countries',
        'item_type': 'country',
    })


@manager_required
def manager_roast_levels(request):
    """Manage roast levels."""
    roast_levels = RoastLevel.objects.all().order_by('name')
    form = RoastLevelForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            form = RoastLevelForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Roast level added successfully')
                return redirect('products:manager_roast_levels')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
                return redirect('products:manager_roast_levels')

        elif action == 'edit':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(RoastLevel, pk=item_id)
            new_name = request.POST.get('new_name', '').strip()
            if not new_name:
                messages.error(request, 'Name cannot be empty')
            elif RoastLevel.objects.filter(name__iexact=new_name).exclude(pk=item.pk).exists():
                messages.error(request, f'Roast level "{new_name}" already exists')
            else:
                item.name = new_name
                item.save()
                messages.success(request, 'Roast level updated successfully')
            return redirect('products:manager_roast_levels')

        elif action == 'delete':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(RoastLevel, pk=item_id)
            item.delete()
            messages.success(request, 'Roast level deleted successfully')
            return redirect('products:manager_roast_levels')

    return render(request, 'products/manager/reference_list.html', {
        'items': roast_levels,
        'form': form,
        'title': 'Roast Levels',
        'item_type': 'roast_level',
    })


@manager_required
def manager_bean_types(request):
    """Manage bean types."""
    bean_types = BeanType.objects.all().order_by('name')
    form = BeanTypeForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            form = BeanTypeForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Bean type added successfully')
                return redirect('products:manager_bean_types')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
                return redirect('products:manager_bean_types')

        elif action == 'edit':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(BeanType, pk=item_id)
            new_name = request.POST.get('new_name', '').strip()
            new_multiplier = request.POST.get('new_multiplier', '').strip()
            if not new_name:
                messages.error(request, 'Name cannot be empty')
            elif BeanType.objects.filter(name__iexact=new_name).exclude(pk=item.pk).exists():
                messages.error(request, f'Bean type "{new_name}" already exists')
            else:
                item.name = new_name
                if new_multiplier:
                    try:
                        item.price_multiplier = Decimal(new_multiplier)
                    except Exception:
                        messages.error(request, 'Invalid multiplier value')
                        return redirect('products:manager_bean_types')
                item.save()
                messages.success(request, 'Bean type updated successfully')
            return redirect('products:manager_bean_types')

        elif action == 'delete':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(BeanType, pk=item_id)
            item.delete()
            messages.success(request, 'Bean type deleted successfully')
            return redirect('products:manager_bean_types')

    return render(request, 'products/manager/bean_types_list.html', {
        'items': bean_types,
        'form': form,
        'title': 'Bean Types',
        'item_type': 'bean_type',
    })


@manager_required
def manager_weights(request):
    """Manage weights."""
    weights = Weight.objects.all().order_by('grams')
    form = WeightForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            form = WeightForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Weight option added successfully')
                return redirect('products:manager_weights')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
                return redirect('products:manager_weights')

        elif action == 'edit':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(Weight, pk=item_id)
            if item.grams == 100:
                messages.error(request, '100g is the base weight and cannot be edited')
                return redirect('products:manager_weights')
            new_grams = request.POST.get('new_grams', '').strip()
            new_multiplier = request.POST.get('new_multiplier', '').strip()
            if not new_grams:
                messages.error(request, 'Grams cannot be empty')
            else:
                try:
                    grams_val = int(new_grams)
                except ValueError:
                    messages.error(request, 'Invalid grams value')
                    return redirect('products:manager_weights')
                if Weight.objects.filter(grams=grams_val).exclude(pk=item.pk).exists():
                    messages.error(request, f'Weight {grams_val}g already exists')
                else:
                    item.grams = grams_val
                    if new_multiplier:
                        try:
                            item.price_multiplier = Decimal(new_multiplier)
                        except Exception:
                            messages.error(request, 'Invalid multiplier value')
                            return redirect('products:manager_weights')
                    item.save()
                    messages.success(request, 'Weight option updated successfully')
            return redirect('products:manager_weights')

        elif action == 'delete':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(Weight, pk=item_id)
            if item.grams == 100:
                messages.error(request, '100g is the base weight and cannot be deleted')
                return redirect('products:manager_weights')
            item.delete()
            messages.success(request, 'Weight option deleted successfully')
            return redirect('products:manager_weights')

    return render(request, 'products/manager/weights_list.html', {
        'items': weights,
        'form': form,
        'title': 'Weight Options',
    })
