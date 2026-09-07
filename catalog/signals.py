from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from catalog.models import Review


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def recalculate_product_rating(sender, instance, **kwargs):
    """Пересчитывает рейтинг товара при добавлении/удалении отзыва."""
    instance.product.update_rating()
