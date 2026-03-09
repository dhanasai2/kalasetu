from django.db import models
from django.utils import timezone
import uuid


class Artisan(models.Model):
    """Profile of a local artisan/craftsperson."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=254, blank=True, unique=True, null=True)
    password = models.CharField(max_length=128, blank=True)
    location = models.CharField(max_length=300, blank=True)
    state = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=50, default='Hindi')
    craft_type = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True, help_text="AI-generated or manual artisan biography")
    story = models.TextField(blank=True, help_text="The artisan's personal craft story")
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='artisans/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} — {self.craft_type}"

    @property
    def product_count(self):
        return self.products.count()


class Buyer(models.Model):
    """Buyer account for shopping, wishlist, and orders."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=254, unique=True)
    password = models.CharField(max_length=128)
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    """A craft product listed by an artisan."""

    CATEGORY_CHOICES = [
        ('painting', 'Painting'),
        ('textile', 'Textile & Weaving'),
        ('pottery', 'Pottery & Ceramics'),
        ('jewelry', 'Jewelry'),
        ('woodwork', 'Woodwork & Carving'),
        ('metalwork', 'Metalwork'),
        ('embroidery', 'Embroidery'),
        ('sculpture', 'Sculpture'),
        ('basketry', 'Basketry'),
        ('leatherwork', 'Leatherwork'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artisan = models.ForeignKey(Artisan, on_delete=models.CASCADE, related_name='products')
    title = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    cultural_story = models.TextField(blank=True, help_text="AI-generated heritage/cultural context")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    art_form = models.CharField(max_length=200, blank=True, help_text="e.g. Madhubani, Bidri, Phulkari")
    materials = models.CharField(max_length=500, blank=True)
    techniques = models.CharField(max_length=500, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    suggested_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to='products/')
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated SEO tags")
    is_published = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or f"Product by {self.artisan.name}"

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]


class Wishlist(models.Model):
    """Buyer's saved/favorited products."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('buyer', 'product')

    def __str__(self):
        return f"{self.buyer.name} ♡ {self.product.title}"


class Order(models.Model):
    """Order / inquiry from buyer to artisan."""
    STATUS_CHOICES = [
        ('inquiry', 'Inquiry'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, related_name='orders')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inquiry')
    message = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} — {self.product.title}"


class ProductView(models.Model):
    """Track product page views for analytics."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='views')
    date = models.DateField(default=timezone.now)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('product', 'date')


class MarketingContent(models.Model):
    """AI-generated marketing content for a product."""

    CONTENT_TYPES = [
        ('instagram', 'Instagram Post'),
        ('facebook', 'Facebook Post'),
        ('product_desc', 'Product Description'),
        ('campaign', 'Campaign Idea'),
        ('hashtags', 'Hashtags'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='marketing_contents')
    content_type = models.CharField(max_length=50, choices=CONTENT_TYPES)
    content = models.TextField()
    language = models.CharField(max_length=50, default='English')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.content_type} for {self.product.title}"


class ChatMessage(models.Model):
    """Buyer-side chat messages for conversational shopping."""
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=100, db_index=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"
