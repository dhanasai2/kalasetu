from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Artisan flows
    path('artisan/login/', views.artisan_login, name='artisan_login'),
    path('artisan/register/', views.artisan_register, name='artisan_register'),
    path('artisan/logout/', views.artisan_logout, name='artisan_logout'),
    path('artisan/<uuid:artisan_id>/dashboard/', views.artisan_dashboard, name='artisan_dashboard'),
    path('artisan/<uuid:artisan_id>/upload/', views.product_upload, name='product_upload'),
    path('artisan/<uuid:artisan_id>/profile/', views.artisan_profile, name='artisan_profile'),
    path('artisan/<uuid:artisan_id>/analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('artisan/<uuid:artisan_id>/orders/', views.artisan_orders, name='artisan_orders'),
    path('artisan/<uuid:artisan_id>/mentor/', views.craft_mentor, name='craft_mentor'),
    path('artisan/<uuid:artisan_id>/festivals/', views.festival_calendar, name='festival_calendar'),

    # Product flows
    path('product/<uuid:product_id>/edit/', views.product_edit, name='product_edit'),
    path('product/<uuid:product_id>/detail/', views.product_detail, name='product_detail'),
    path('product/<uuid:product_id>/publish/', views.product_publish, name='product_publish'),
    path('product/<uuid:product_id>/qr/', views.product_qr, name='product_qr'),
    path('product/<uuid:product_id>/translate/', views.translate_description, name='translate_description'),
    path('product/<uuid:product_id>/wishlist/', views.toggle_wishlist, name='toggle_wishlist'),
    path('product/<uuid:product_id>/heritage/', views.heritage_story, name='heritage_story'),
    path('product/<uuid:product_id>/order/', views.place_order, name='place_order'),

    # Certificate / Invoice PDF
    path('order/<uuid:order_id>/certificate/', views.order_certificate, name='order_certificate'),

    # Marketing AI
    path('product/<uuid:product_id>/marketing/', views.marketing_hub, name='marketing_hub'),
    path('product/<uuid:product_id>/marketing/generate/', views.generate_marketing, name='generate_marketing'),
    path('product/<uuid:product_id>/marketing/trends/', views.generate_trends, name='generate_trends'),

    # Buyer flows
    path('buyer/register/', views.buyer_register, name='buyer_register'),
    path('buyer/login/', views.buyer_login, name='buyer_login'),
    path('buyer/logout/', views.buyer_logout, name='buyer_logout'),
    path('buyer/dashboard/', views.buyer_dashboard, name='buyer_dashboard'),

    # Buyer storefront
    path('shop/', views.storefront, name='storefront'),

    # India Craft Map
    path('craft-map/', views.craft_map, name='craft_map'),

    # Chat
    path('chat/', views.chat_page, name='chat_page'),
    path('chat/send/', views.chat_send, name='chat_send'),
]
