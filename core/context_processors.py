from .models import Artisan, Buyer


def artisan_context(request):
    """Make current artisan and buyer available in all templates."""
    artisan_id = request.session.get('artisan_id')
    buyer_id = request.session.get('buyer_id')
    current_artisan = None
    current_buyer = None
    if artisan_id:
        try:
            current_artisan = Artisan.objects.get(id=artisan_id)
        except (Artisan.DoesNotExist, Exception):
            pass
    if buyer_id:
        try:
            current_buyer = Buyer.objects.get(id=buyer_id)
        except (Buyer.DoesNotExist, Exception):
            pass
    return {
        'current_artisan': current_artisan,
        'current_buyer': current_buyer,
    }
