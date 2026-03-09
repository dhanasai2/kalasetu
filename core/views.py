import json
import uuid
import logging
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncDate
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

from .models import Artisan, Buyer, Product, MarketingContent, ChatMessage, Wishlist, Order, ProductView
from .forms import ArtisanForm, BuyerRegisterForm, OrderForm, ProductUploadForm, ProductEditForm
from .gi_tags import get_gi_tag, GI_TAGS
from . import ai_service

logger = logging.getLogger(__name__)


# ─── HOME & LANDING ───────────────────────────────────────────

def home(request):
    featured_products = Product.objects.filter(is_published=True).order_by('-created_at')[:8]
    artisans = Artisan.objects.all().order_by('-created_at')[:6]
    state_data = (
        Artisan.objects.values('state')
        .annotate(count=Count('id'))
        .filter(state__gt='')
        .order_by('-count')
    )
    return render(request, 'core/home.html', {
        'featured_products': featured_products,
        'artisans': artisans,
        'state_data': list(state_data),
    })


# ─── ARTISAN AUTH ─────────────────────────────────────────────

def artisan_login(request):
    error = None
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')
        if not identifier or not password:
            error = "Please enter your email/phone and password."
        else:
            artisan = None
            if '@' in identifier:
                artisan = Artisan.objects.filter(email__iexact=identifier).first()
            else:
                artisan = Artisan.objects.filter(phone=identifier).first()
            if artisan and artisan.password and check_password(password, artisan.password):
                request.session['artisan_id'] = str(artisan.id)
                next_url = request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                return redirect('artisan_dashboard', artisan_id=artisan.id)
            else:
                error = "Invalid credentials. Please check your email/phone and password."
    return render(request, 'core/artisan_login.html', {'error': error})


def artisan_register(request):
    if request.method == 'POST':
        form = ArtisanForm(request.POST, request.FILES)
        if form.is_valid():
            artisan = form.save(commit=False)
            artisan.password = make_password(form.cleaned_data['password'])
            try:
                artisan.bio = ai_service.generate_artisan_bio(
                    name=artisan.name,
                    craft_type=artisan.craft_type,
                    location=f"{artisan.location}, {artisan.state}",
                    story=artisan.story,
                )
            except Exception:
                artisan.bio = artisan.story or ""
            artisan.save()
            request.session['artisan_id'] = str(artisan.id)
            return redirect('artisan_dashboard', artisan_id=artisan.id)
    else:
        form = ArtisanForm()
    return render(request, 'core/artisan_register.html', {'form': form})


def artisan_logout(request):
    if 'artisan_id' in request.session:
        del request.session['artisan_id']
    return redirect('home')


# ─── BUYER AUTH ───────────────────────────────────────────────

def buyer_register(request):
    if request.method == 'POST':
        form = BuyerRegisterForm(request.POST)
        if form.is_valid():
            buyer = form.save(commit=False)
            buyer.password = make_password(form.cleaned_data['password'])
            buyer.save()
            request.session['buyer_id'] = str(buyer.id)
            return redirect('storefront')
    else:
        form = BuyerRegisterForm()
    return render(request, 'core/buyer_register.html', {'form': form})


def buyer_login(request):
    error = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        if not email or not password:
            error = "Please enter your email and password."
        else:
            buyer = Buyer.objects.filter(email__iexact=email).first()
            if buyer and check_password(password, buyer.password):
                request.session['buyer_id'] = str(buyer.id)
                next_url = request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                return redirect('storefront')
            else:
                error = "Invalid credentials."
    return render(request, 'core/buyer_login.html', {'error': error})


def buyer_logout(request):
    if 'buyer_id' in request.session:
        del request.session['buyer_id']
    return redirect('home')


def buyer_dashboard(request):
    buyer_id = request.session.get('buyer_id')
    if not buyer_id:
        return redirect('buyer_login')
    buyer = get_object_or_404(Buyer, id=buyer_id)
    wishlisted = Wishlist.objects.filter(buyer=buyer).select_related('product', 'product__artisan').order_by('-created_at')
    orders = Order.objects.filter(buyer=buyer).select_related('product', 'product__artisan').order_by('-created_at')
    return render(request, 'core/buyer_dashboard.html', {
        'buyer': buyer,
        'wishlisted': wishlisted,
        'orders': orders,
    })


# ─── ARTISAN DASHBOARD ───────────────────────────────────────

def artisan_dashboard(request, artisan_id):
    artisan = get_object_or_404(Artisan, id=artisan_id)
    request.session['artisan_id'] = str(artisan.id)
    products = artisan.products.all().order_by('-created_at')
    published = products.filter(is_published=True)

    total_views = published.aggregate(s=Sum('view_count'))['s'] or 0
    total_orders = Order.objects.filter(product__artisan=artisan).count()
    total_wishlist = Wishlist.objects.filter(product__artisan=artisan).count()
    recent_orders = (
        Order.objects.filter(product__artisan=artisan)
        .select_related('buyer', 'product')
        .order_by('-created_at')[:5]
    )

    return render(request, 'core/artisan_dashboard.html', {
        'artisan': artisan,
        'products': products,
        'total_views': total_views,
        'total_orders': total_orders,
        'total_wishlist': total_wishlist,
        'recent_orders': recent_orders,
    })


# ─── ANALYTICS DASHBOARD ─────────────────────────────────────

def analytics_dashboard(request, artisan_id):
    artisan = get_object_or_404(Artisan, id=artisan_id)
    products = artisan.products.all()
    published = products.filter(is_published=True)

    total_views = published.aggregate(s=Sum('view_count'))['s'] or 0
    total_wishlist = Wishlist.objects.filter(product__artisan=artisan).count()
    total_orders = Order.objects.filter(product__artisan=artisan).count()
    total_marketing = MarketingContent.objects.filter(product__artisan=artisan).count()

    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    daily_views = (
        ProductView.objects.filter(product__artisan=artisan, date__gte=thirty_days_ago)
        .values('date').annotate(total=Sum('count')).order_by('date')
    )
    top_products = published.order_by('-view_count')[:5]
    daily_orders = (
        Order.objects.filter(product__artisan=artisan, created_at__date__gte=thirty_days_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date').annotate(total=Count('id')).order_by('date')
    )

    # Category breakdown for bar chart
    category_data = (
        products.values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    category_labels = [dict(Product.CATEGORY_CHOICES).get(c['category'], c['category']) for c in category_data]
    category_counts = [c['count'] for c in category_data]

    # Order status breakdown for pie chart
    order_status_data = (
        Order.objects.filter(product__artisan=artisan)
        .values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )
    status_labels = [dict(Order.STATUS_CHOICES).get(s['status'], s['status']) for s in order_status_data]
    status_counts = [s['count'] for s in order_status_data]

    # Estimated revenue
    from django.db.models import F
    total_revenue = (
        Order.objects.filter(product__artisan=artisan)
        .aggregate(revenue=Sum(F('product__price') * F('quantity')))
    )['revenue'] or 0

    # Top wishlisted products
    top_wishlisted = (
        Wishlist.objects.filter(product__artisan=artisan)
        .values('product__id', 'product__title')
        .annotate(saves=Count('id'))
        .order_by('-saves')[:5]
    )

    # Recent orders with buyer details
    recent_orders = (
        Order.objects.filter(product__artisan=artisan)
        .select_related('buyer', 'product')
        .order_by('-created_at')[:10]
    )

    # Monthly wishlists for sparkline
    daily_wishlists = (
        Wishlist.objects.filter(product__artisan=artisan, created_at__date__gte=thirty_days_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date').annotate(total=Count('id')).order_by('date')
    )

    return render(request, 'core/analytics.html', {
        'artisan': artisan,
        'total_views': total_views,
        'total_wishlist': total_wishlist,
        'total_orders': total_orders,
        'total_marketing': total_marketing,
        'total_products': products.count(),
        'published_count': published.count(),
        'daily_views': list(daily_views),
        'top_products': top_products,
        'daily_orders': list(daily_orders),
        'category_labels': json.dumps(category_labels),
        'category_counts': json.dumps(category_counts),
        'status_labels': json.dumps(status_labels),
        'status_counts': json.dumps(status_counts),
        'total_revenue': total_revenue,
        'top_wishlisted': top_wishlisted,
        'recent_orders': recent_orders,
        'daily_wishlists': list(daily_wishlists),
    })


# ─── PRODUCT MANAGEMENT ──────────────────────────────────────

def product_upload(request, artisan_id):
    artisan = get_object_or_404(Artisan, id=artisan_id)
    if request.method == 'POST':
        form = ProductUploadForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.artisan = artisan
            product.save()
            try:
                voice_note = form.cleaned_data.get('voice_note', '')
                ai_data = ai_service.analyze_product_image(product.image.path, artisan_voice_note=voice_note)
                product.title = ai_data.get('title', '') or 'Handcrafted Product'
                product.description = ai_data.get('description', '') or f'A beautiful handcrafted product by {artisan.name}'
                product.cultural_story = ai_data.get('cultural_story', '')
                product.category = ai_data.get('category', 'other')
                product.art_form = ai_data.get('art_form', '')
                product.materials = ai_data.get('materials', '')
                product.techniques = ai_data.get('techniques', '')
                product.tags = ai_data.get('tags', '')
                try:
                    price = ai_data.get('suggested_price_inr', 0)
                    product.suggested_price = float(price) if price else None
                except (ValueError, TypeError):
                    product.suggested_price = None
                if not product.price or product.price <= 0:
                    product.price = product.suggested_price or 100
                product.save()
            except Exception as e:
                logger.error(f"Product AI analysis error: {e}")
                product.title = product.title or "Handcrafted Product"
                product.description = product.description or f"A beautiful handcrafted product by {artisan.name}"
                product.save()
            return redirect('product_edit', product_id=product.id)
    else:
        form = ProductUploadForm()
    return render(request, 'core/product_upload.html', {'form': form, 'artisan': artisan})


def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductEditForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            if product.is_published:
                return redirect('product_detail', product_id=product.id)
            return redirect('artisan_dashboard', artisan_id=product.artisan.id)
    else:
        form = ProductEditForm(instance=product)
    return render(request, 'core/product_edit.html', {'form': form, 'product': product})


@require_POST
def product_publish(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_published = not product.is_published
    product.save(update_fields=['is_published'])
    return JsonResponse({
        'success': True,
        'is_published': product.is_published,
        'detail_url': f'/product/{product.id}/detail/' if product.is_published else '',
    })


# ─── MARKETING AI ────────────────────────────────────────────

def marketing_hub(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    existing_content = product.marketing_contents.all().order_by('-created_at')
    return render(request, 'core/marketing_hub.html', {
        'product': product,
        'existing_content': existing_content,
    })


@require_POST
def generate_marketing(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    content_type = request.POST.get('content_type', 'instagram')
    language = request.POST.get('language', 'English')
    try:
        content = ai_service.generate_marketing_content(
            product_title=product.title,
            product_description=product.description,
            art_form=product.art_form,
            cultural_story=product.cultural_story,
            content_type=content_type,
            language=language,
        )
        mc = MarketingContent.objects.create(
            product=product, content_type=content_type,
            content=content, language=language,
        )
        return JsonResponse({'success': True, 'content': content, 'id': str(mc.id)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
def generate_trends(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        trends = ai_service.generate_trend_suggestions(craft_type=product.category, art_form=product.art_form)
        return JsonResponse({'success': True, 'content': trends})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─── MULTI-LANGUAGE DESCRIPTION ──────────────────────────────

@require_POST
def translate_description(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    language = request.POST.get('language', 'Hindi')
    try:
        translated = ai_service.translate_content(content=product.description, target_language=language)
        return JsonResponse({'success': True, 'content': translated, 'language': language})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─── BUYER STOREFRONT ────────────────────────────────────────

def storefront(request):
    products = Product.objects.filter(is_published=True).select_related('artisan')
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    art_form = request.GET.get('art_form', '')
    state = request.GET.get('state', '')

    if query:
        products = products.filter(
            Q(title__icontains=query) | Q(description__icontains=query) |
            Q(art_form__icontains=query) | Q(tags__icontains=query) |
            Q(artisan__name__icontains=query)
        )
    if category:
        products = products.filter(category=category)
    if art_form:
        products = products.filter(art_form__icontains=art_form)
    if state:
        products = products.filter(artisan__state__icontains=state)
    products = products.order_by('-created_at')

    buyer_id = request.session.get('buyer_id')
    wishlist_ids = set()
    if buyer_id:
        wishlist_ids = set(Wishlist.objects.filter(buyer_id=buyer_id).values_list('product_id', flat=True))

    categories = Product.CATEGORY_CHOICES
    art_forms = Product.objects.filter(is_published=True).values_list('art_form', flat=True).distinct()

    return render(request, 'core/storefront.html', {
        'products': products,
        'query': query,
        'selected_category': category,
        'selected_art_form': art_form,
        'categories': categories,
        'art_forms': art_forms,
        'wishlist_ids': wishlist_ids,
    })


def product_detail(request, product_id):
    product = Product.objects.filter(id=product_id).select_related('artisan').first()
    if not product:
        raise Http404
    # Allow the owning artisan to view even if unpublished; everyone else needs published
    artisan_id = request.session.get('artisan_id')
    if not product.is_published and str(product.artisan_id) != str(artisan_id):
        raise Http404

    product.view_count += 1
    product.save(update_fields=['view_count'])
    today = timezone.now().date()
    pv, _ = ProductView.objects.get_or_create(product=product, date=today)
    pv.count += 1
    pv.save(update_fields=['count'])

    related = _get_recommendations(product, limit=4)
    gi_tag = get_gi_tag(product.art_form)

    buyer_id = request.session.get('buyer_id')
    is_wishlisted = False
    if buyer_id:
        is_wishlisted = Wishlist.objects.filter(buyer_id=buyer_id, product=product).exists()

    order_form = OrderForm()

    return render(request, 'core/product_detail.html', {
        'product': product,
        'related_products': related,
        'gi_tag': gi_tag,
        'is_wishlisted': is_wishlisted,
        'order_form': order_form,
    })


def _get_recommendations(product, limit=4):
    candidates = Product.objects.filter(is_published=True).exclude(id=product.id).select_related('artisan')
    if not product.tags:
        return candidates.filter(category=product.category)[:limit]
    product_tags = set(t.lower().strip() for t in product.tags.split(',') if t.strip())
    scored = []
    for p in candidates[:50]:
        p_tags = set(t.lower().strip() for t in p.tags.split(',') if t.strip())
        overlap = len(product_tags & p_tags)
        if p.category == product.category:
            overlap += 2
        if p.art_form and product.art_form and p.art_form.lower() == product.art_form.lower():
            overlap += 3
        scored.append((overlap, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:limit]]


def artisan_profile(request, artisan_id):
    artisan = get_object_or_404(Artisan, id=artisan_id)
    products = artisan.products.filter(is_published=True).order_by('-created_at')
    gi_tags = set()
    for p in products:
        gi = get_gi_tag(p.art_form)
        if gi:
            gi_tags.add(gi['name'])
    return render(request, 'core/artisan_profile.html', {
        'artisan': artisan,
        'products': products,
        'gi_tags': gi_tags,
    })


# ─── WISHLIST ─────────────────────────────────────────────────

@require_POST
def toggle_wishlist(request, product_id):
    buyer_id = request.session.get('buyer_id')
    if not buyer_id:
        return JsonResponse({'error': 'Login required', 'login_url': '/buyer/login/'}, status=401)
    product = get_object_or_404(Product, id=product_id)
    existing = Wishlist.objects.filter(buyer_id=buyer_id, product=product).first()
    if existing:
        existing.delete()
        return JsonResponse({'success': True, 'wishlisted': False})
    else:
        Wishlist.objects.create(buyer_id=buyer_id, product=product)
        return JsonResponse({'success': True, 'wishlisted': True})


# ─── ORDERS / CONTACT ARTISAN ────────────────────────────────

@require_POST
def place_order(request, product_id):
    buyer_id = request.session.get('buyer_id')
    if not buyer_id:
        return JsonResponse({'error': 'Login required', 'login_url': '/buyer/login/'}, status=401)
    product = get_object_or_404(Product, id=product_id, is_published=True)
    form = OrderForm(request.POST)
    if form.is_valid():
        order = form.save(commit=False)
        order.buyer_id = buyer_id
        order.product = product
        order.save()
        return JsonResponse({'success': True, 'order_id': str(order.id)})
    return JsonResponse({'success': False, 'error': 'Invalid form data'}, status=400)


def artisan_orders(request, artisan_id):
    artisan = get_object_or_404(Artisan, id=artisan_id)
    orders = Order.objects.filter(product__artisan=artisan).select_related('buyer', 'product').order_by('-created_at')
    return render(request, 'core/artisan_orders.html', {
        'artisan': artisan,
        'orders': orders,
    })


# ─── AI CRAFT MENTOR ─────────────────────────────────────────

def craft_mentor(request, artisan_id):
    """AI Craft Mentor — personalized business coaching for artisans."""
    artisan = get_object_or_404(Artisan, id=artisan_id)
    if str(artisan.id) != request.session.get('artisan_id'):
        return redirect('home')

    products = artisan.products.all()
    published = products.filter(is_published=True)
    total_views = published.aggregate(s=Sum('view_count'))['s'] or 0
    total_orders = Order.objects.filter(product__artisan=artisan).count()
    total_wishlist = Wishlist.objects.filter(product__artisan=artisan).count()
    total_marketing = MarketingContent.objects.filter(product__artisan=artisan).count()

    top_products = published.order_by('-view_count')[:5]
    top_products_info = "\n".join(
        [f"- {p.title} ({p.get_category_display()}) — {p.view_count} views, ₹{p.price or 0}" for p in top_products]
    ) or "No published products yet."

    recent_orders = Order.objects.filter(product__artisan=artisan).select_related('buyer', 'product').order_by('-created_at')[:10]
    recent_orders_info = "\n".join(
        [f"- {o.product.title} — ordered by {o.buyer.name} ({o.buyer.location or 'Unknown location'}), qty: {o.quantity}, status: {o.get_status_display()}" for o in recent_orders]
    ) or "No orders yet."

    advice = None
    if request.method == 'POST':
        advice = ai_service.generate_craft_mentor_advice(
            artisan_name=artisan.name,
            craft_type=artisan.craft_type,
            location=f"{artisan.location}, {artisan.state}" if artisan.state else artisan.location,
            total_views=total_views,
            total_orders=total_orders,
            total_wishlist=total_wishlist,
            total_products=products.count(),
            published_count=published.count(),
            top_products_info=top_products_info,
            recent_orders_info=recent_orders_info,
            marketing_count=total_marketing,
        )

    return render(request, 'core/craft_mentor.html', {
        'artisan': artisan,
        'advice': advice,
        'total_views': total_views,
        'total_orders': total_orders,
        'total_wishlist': total_wishlist,
        'total_products': products.count(),
        'published_count': published.count(),
    })


# ─── FESTIVAL CAMPAIGN CALENDAR ──────────────────────────────

INDIAN_FESTIVALS = [
    {"name": "Makar Sankranti / Pongal", "date": "2026-01-14", "month": "January", "icon": "sun", "color": "#f9a825"},
    {"name": "Republic Day", "date": "2026-01-26", "month": "January", "icon": "flag", "color": "#1565c0"},
    {"name": "Vasant Panchami", "date": "2026-02-01", "month": "February", "icon": "flower1", "color": "#ffeb3b"},
    {"name": "Maha Shivaratri", "date": "2026-02-11", "month": "February", "icon": "moon-stars", "color": "#5c6bc0"},
    {"name": "Holi", "date": "2026-03-03", "month": "March", "icon": "palette", "color": "#e91e63"},
    {"name": "Ugadi / Gudi Padwa", "date": "2026-03-19", "month": "March", "icon": "calendar-event", "color": "#ff9800"},
    {"name": "Ram Navami", "date": "2026-03-27", "month": "March", "icon": "stars", "color": "#ff7043"},
    {"name": "Baisakhi", "date": "2026-04-13", "month": "April", "icon": "grain", "color": "#8bc34a"},
    {"name": "Eid ul-Fitr", "date": "2026-03-30", "month": "March", "icon": "moon", "color": "#26a69a"},
    {"name": "Akshaya Tritiya", "date": "2026-04-18", "month": "April", "icon": "gem", "color": "#ffd54f"},
    {"name": "Raksha Bandhan", "date": "2026-08-08", "month": "August", "icon": "heart", "color": "#e91e63"},
    {"name": "Independence Day", "date": "2026-08-15", "month": "August", "icon": "flag", "color": "#f57c00"},
    {"name": "Janmashtami", "date": "2026-08-14", "month": "August", "icon": "stars", "color": "#1a237e"},
    {"name": "Ganesh Chaturthi", "date": "2026-08-27", "month": "August", "icon": "emoji-smile", "color": "#e65100"},
    {"name": "Onam", "date": "2026-08-25", "month": "August", "icon": "flower2", "color": "#ff9800"},
    {"name": "Navratri / Durga Puja", "date": "2026-09-27", "month": "September", "icon": "fire", "color": "#c62828"},
    {"name": "Dussehra", "date": "2026-10-06", "month": "October", "icon": "arrow-up-circle", "color": "#ff5722"},
    {"name": "Karwa Chauth", "date": "2026-10-09", "month": "October", "icon": "moon", "color": "#ad1457"},
    {"name": "Dhanteras", "date": "2026-10-22", "month": "October", "icon": "coin", "color": "#ffc107"},
    {"name": "Diwali", "date": "2026-10-24", "month": "October", "icon": "lightbulb", "color": "#ff6f00"},
    {"name": "Bhai Dooj", "date": "2026-10-26", "month": "October", "icon": "people", "color": "#7b1fa2"},
    {"name": "Christmas", "date": "2026-12-25", "month": "December", "icon": "tree", "color": "#2e7d32"},
    {"name": "New Year", "date": "2027-01-01", "month": "January", "icon": "calendar-check", "color": "#1565c0"},
]

def festival_calendar(request, artisan_id):
    """Festival Campaign Calendar with AI auto-campaign generation."""
    artisan = get_object_or_404(Artisan, id=artisan_id)
    if str(artisan.id) != request.session.get('artisan_id'):
        return redirect('home')

    products = artisan.products.filter(is_published=True)
    product_titles = list(products.values_list('title', flat=True)[:8])

    from datetime import datetime
    today = datetime.today().date()
    upcoming = []
    for f in INDIAN_FESTIVALS:
        fdate = datetime.strptime(f['date'], '%Y-%m-%d').date()
        days_away = (fdate - today).days
        if days_away >= -2:  # include festivals up to 2 days past
            upcoming.append({**f, 'days_away': max(days_away, 0), 'past': days_away < 0})

    upcoming.sort(key=lambda x: x['days_away'])

    campaign = None
    selected_festival = None
    if request.method == 'POST':
        selected_festival = request.POST.get('festival', '')
        campaign = ai_service.generate_festival_campaign(
            craft_type=artisan.craft_type,
            art_form=products.first().art_form if products.exists() else artisan.craft_type,
            product_titles=product_titles,
            artisan_name=artisan.name,
            festival_name=selected_festival if selected_festival else None,
        )

    return render(request, 'core/festival_calendar.html', {
        'artisan': artisan,
        'upcoming_festivals': upcoming[:15],
        'campaign': campaign,
        'selected_festival': selected_festival,
        'product_count': products.count(),
    })


# ─── AI HERITAGE STORY ───────────────────────────────────────

def heritage_story(request, product_id):
    """Generate a rich cultural heritage story for a product."""
    product = get_object_or_404(Product.objects.select_related('artisan'), id=product_id)
    artisan = product.artisan

    story = None
    if request.method == 'POST':
        story = ai_service.generate_heritage_story(
            product_title=product.title,
            art_form=product.art_form,
            category=product.get_category_display(),
            materials=product.materials,
            techniques=product.techniques,
            cultural_story=product.cultural_story,
            artisan_name=artisan.name,
            artisan_location=artisan.location,
            artisan_state=artisan.state,
        )

    return render(request, 'core/heritage_story.html', {
        'product': product,
        'artisan': artisan,
        'story': story,
    })


# ─── PDF CERTIFICATE / INVOICE ───────────────────────────────

def order_certificate(request, order_id):
    """Generate a branded PDF authenticity certificate + invoice for an order."""
    order = get_object_or_404(Order.objects.select_related('buyer', 'product', 'product__artisan'), id=order_id)
    artisan = order.product.artisan
    product = order.product
    buyer = order.buyer

    # Security: only the artisan or buyer can download
    session_artisan = request.session.get('artisan_id')
    session_buyer = request.session.get('buyer_id')
    if str(artisan.id) != session_artisan and str(buyer.id) != session_buyer:
        return redirect('home')

    import io
    import qrcode
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.utils import ImageReader

    buf = io.BytesIO()
    w, h = A4
    c = pdf_canvas.Canvas(buf, pagesize=A4)

    # Colors
    primary = HexColor('#C45B28')
    dark = HexColor('#1B1B1B')
    muted = HexColor('#666666')
    gold = HexColor('#B8860B')
    bg_cream = HexColor('#FFF8F0')

    # ── Background ──
    c.setFillColor(bg_cream)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # ── Decorative border ──
    c.setStrokeColor(primary)
    c.setLineWidth(3)
    c.rect(15*mm, 15*mm, w - 30*mm, h - 30*mm, fill=0, stroke=1)
    c.setStrokeColor(gold)
    c.setLineWidth(1)
    c.rect(17*mm, 17*mm, w - 34*mm, h - 34*mm, fill=0, stroke=1)

    # ── Header ──
    y = h - 40*mm
    c.setFillColor(primary)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(w/2, y, "KalaSetu")
    y -= 8*mm
    c.setFont("Helvetica", 10)
    c.setFillColor(muted)
    c.drawCentredString(w/2, y, "Bridging Artisans to the World — AI-Powered Indian Craft Marketplace")

    # ── Title ──
    y -= 16*mm
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w/2, y, "Certificate of Authenticity")
    y -= 6*mm
    c.setStrokeColor(gold)
    c.setLineWidth(1.5)
    c.line(w/2 - 60*mm, y, w/2 + 60*mm, y)

    # ── Certificate ID ──
    y -= 10*mm
    c.setFont("Helvetica", 9)
    c.setFillColor(muted)
    cert_id = str(order.id).replace('-', '').upper()[:16]
    c.drawCentredString(w/2, y, f"Certificate No: KS-{cert_id}")

    # ── Product Info ──
    y -= 14*mm
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(dark)
    c.drawString(25*mm, y, "Product Details")
    y -= 2*mm
    c.setStrokeColor(primary)
    c.setLineWidth(1)
    c.line(25*mm, y, 100*mm, y)

    y -= 8*mm
    c.setFont("Helvetica", 10)
    fields = [
        ("Product", product.title or "Handcrafted Item"),
        ("Art Form", product.art_form or product.get_category_display()),
        ("Materials", product.materials or "Traditional materials"),
        ("Techniques", product.techniques or "Handcrafted"),
    ]
    if product.price:
        fields.append(("Price", f"₹{product.price:,.0f}"))
    for label, value in fields:
        c.setFillColor(muted)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25*mm, y, f"{label}:")
        c.setFillColor(dark)
        c.setFont("Helvetica", 9)
        c.drawString(55*mm, y, str(value)[:70])
        y -= 5.5*mm

    # ── GI Tag Info ──
    gi_tag = get_gi_tag(product.art_form) or get_gi_tag(product.title)
    if gi_tag:
        y -= 6*mm
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(dark)
        c.drawString(25*mm, y, "GI Tag Certification")
        y -= 2*mm
        c.setStrokeColor(HexColor('#2e7d32'))
        c.line(25*mm, y, 105*mm, y)

        y -= 8*mm
        gi_fields = [
            ("GI Tag", gi_tag['name']),
            ("GI Number", gi_tag['gi_number']),
            ("State / Region", f"{gi_tag['state']} — {gi_tag['region']}"),
            ("Year Registered", str(gi_tag['year'])),
        ]
        for label, value in gi_fields:
            c.setFillColor(muted)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(25*mm, y, f"{label}:")
            c.setFillColor(HexColor('#2e7d32'))
            c.setFont("Helvetica", 9)
            c.drawString(55*mm, y, str(value)[:70])
            y -= 5.5*mm

        # GI description (wrapped)
        y -= 2*mm
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(muted)
        desc = gi_tag.get('description', '')
        from reportlab.lib.utils import simpleSplit
        lines = simpleSplit(desc, "Helvetica-Oblique", 8, w - 55*mm)
        for line in lines[:3]:
            c.drawString(25*mm, y, line)
            y -= 4*mm

    # ── Artisan Info ──
    y -= 8*mm
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(dark)
    c.drawString(25*mm, y, "Artisan")
    y -= 2*mm
    c.setStrokeColor(primary)
    c.line(25*mm, y, 75*mm, y)
    y -= 8*mm

    artisan_fields = [
        ("Name", artisan.name),
        ("Craft", artisan.craft_type),
        ("Location", f"{artisan.location}, {artisan.state}" if artisan.state else artisan.location),
    ]
    for label, value in artisan_fields:
        c.setFillColor(muted)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25*mm, y, f"{label}:")
        c.setFillColor(dark)
        c.setFont("Helvetica", 9)
        c.drawString(55*mm, y, str(value)[:70])
        y -= 5.5*mm

    # Artisan story snippet
    if artisan.bio:
        y -= 2*mm
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(muted)
        from reportlab.lib.utils import simpleSplit
        bio_lines = simpleSplit(artisan.bio, "Helvetica-Oblique", 8, w - 55*mm)
        for line in bio_lines[:3]:
            c.drawString(25*mm, y, line)
            y -= 4*mm

    # ── Order / Invoice Info ──
    y -= 8*mm
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(dark)
    c.drawString(25*mm, y, "Invoice")
    y -= 2*mm
    c.setStrokeColor(primary)
    c.line(25*mm, y, 70*mm, y)
    y -= 8*mm

    order_fields = [
        ("Buyer", buyer.name),
        ("Email", buyer.email),
        ("Quantity", str(order.quantity)),
        ("Status", order.get_status_display()),
        ("Order Date", order.created_at.strftime("%d %B %Y")),
    ]
    if product.price:
        total = product.price * order.quantity
        order_fields.append(("Total Amount", f"₹{total:,.0f}"))
    if order.message:
        order_fields.append(("Note", order.message[:60]))
    for label, value in order_fields:
        c.setFillColor(muted)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25*mm, y, f"{label}:")
        c.setFillColor(dark)
        c.setFont("Helvetica", 9)
        c.drawString(55*mm, y, str(value))
        y -= 5.5*mm

    # ── QR Code (bottom right) ──
    product_url = request.build_absolute_uri(f'/product/{product.id}/detail/')
    qr = qrcode.make(product_url, box_size=4, border=2)
    qr_buf = io.BytesIO()
    qr.save(qr_buf, format='PNG')
    qr_buf.seek(0)
    qr_img = ImageReader(qr_buf)
    qr_size = 28*mm
    c.drawImage(qr_img, w - 25*mm - qr_size, 22*mm, width=qr_size, height=qr_size)
    c.setFont("Helvetica", 7)
    c.setFillColor(muted)
    c.drawCentredString(w - 25*mm - qr_size/2, 19*mm, "Scan to verify product")

    # ── Footer ──
    c.setFont("Helvetica", 8)
    c.setFillColor(muted)
    c.drawCentredString(w/2, 22*mm, f"Generated on {timezone.now().strftime('%d %B %Y')} · KalaSetu — Empowering Indian Artisans with AI")
    c.drawCentredString(w/2, 18*mm, "This certificate attests to the handcrafted authenticity and artisan origin of the above product.")

    c.showPage()
    c.save()

    buf.seek(0)
    from django.http import FileResponse
    safe_title = (product.title or 'product').replace(' ', '_')[:30]
    response = FileResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="KalaSetu_Certificate_{safe_title}.pdf"'
    return response


# ─── INDIA CRAFT MAP ─────────────────────────────────────────

def craft_map(request):
    state_crafts = {}
    artisans_by_state = (
        Artisan.objects.filter(state__gt='')
        .values('state', 'craft_type')
        .annotate(count=Count('id'))
        .order_by('state', '-count')
    )
    for row in artisans_by_state:
        st = row['state']
        if st not in state_crafts:
            state_crafts[st] = []
        state_crafts[st].append({'craft': row['craft_type'], 'count': row['count']})

    product_counts = (
        Product.objects.filter(is_published=True)
        .values('artisan__state')
        .annotate(count=Count('id'))
    )
    state_products = {r['artisan__state']: r['count'] for r in product_counts if r['artisan__state']}

    gi_by_state = {}
    for key, data in GI_TAGS.items():
        st = data['state']
        if '/' in st:
            for s in st.split('/'):
                gi_by_state.setdefault(s.strip(), []).append(data['name'])
        else:
            gi_by_state.setdefault(st, []).append(data['name'])

    return render(request, 'core/craft_map.html', {
        'state_crafts': json.dumps(state_crafts),
        'state_products': json.dumps(state_products),
        'gi_by_state': json.dumps(gi_by_state),
    })


# ─── QR CODE ─────────────────────────────────────────────────

def product_qr(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product_url = request.build_absolute_uri(f'/product/{product.id}/detail/')
    return render(request, 'core/product_qr.html', {
        'product': product,
        'product_url': product_url,
    })


# ─── CHAT ─────────────────────────────────────────────────────

def chat_page(request):
    if not request.session.get('artisan_id') and not request.session.get('buyer_id'):
        return redirect('/buyer/login/?next=/chat/')
    session_id = str(uuid.uuid4())
    request.session['chat_session_id'] = session_id
    return render(request, 'core/chat.html', {'session_id': session_id})


@csrf_exempt
@require_POST
def chat_send(request):
    data = json.loads(request.body)
    message = data.get('message', '').strip()
    session_id = data.get('session_id', '')
    if not message or not session_id:
        return JsonResponse({'error': 'Missing message or session'}, status=400)
    ChatMessage.objects.create(session_id=session_id, role='user', content=message)
    history = list(
        ChatMessage.objects.filter(session_id=session_id)
        .order_by('created_at').values('role', 'content')
    )
    products = Product.objects.filter(is_published=True).select_related('artisan')[:20]
    products_context = "\n".join([
        f"- {p.title} | {p.art_form} | ₹{p.price or p.suggested_price or 'N/A'} | by {p.artisan.name} from {p.artisan.location} | {p.description[:100]}"
        for p in products
    ])
    try:
        reply = ai_service.chat_with_buyer(message, history[:-1], products_context)
    except Exception:
        reply = "I'm having trouble connecting right now. Please try again in a moment!"
    ChatMessage.objects.create(session_id=session_id, role='assistant', content=reply)
    return JsonResponse({'reply': reply})


# ─── ERROR PAGES ──────────────────────────────────────────────

def custom_404(request, exception):
    return render(request, 'errors/404.html', status=404)


def custom_500(request):
    return render(request, 'errors/500.html', status=500)
