from django.contrib import admin
from .models import Artisan, Product, MarketingContent, ChatMessage


@admin.register(Artisan)
class ArtisanAdmin(admin.ModelAdmin):
    list_display = ['name', 'craft_type', 'location', 'state', 'product_count', 'created_at']
    search_fields = ['name', 'craft_type', 'location']
    list_filter = ['state', 'craft_type']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'artisan', 'category', 'art_form', 'price', 'is_published', 'created_at']
    search_fields = ['title', 'art_form', 'description']
    list_filter = ['category', 'is_published', 'art_form']


@admin.register(MarketingContent)
class MarketingContentAdmin(admin.ModelAdmin):
    list_display = ['product', 'content_type', 'language', 'created_at']
    list_filter = ['content_type', 'language']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'role', 'content', 'created_at']
    list_filter = ['role']
