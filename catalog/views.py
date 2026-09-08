from rest_framework.generics import ListAPIView

from catalog.models import Category, Tag
from catalog.serializers import TagSerializer


class TagListView(ListAPIView):
    """/api/tags?category=<id> — теги товаров конкретной категории (включая
    подкатегории, у нас вложенность на один уровень); без category — все теги."""

    serializer_class = TagSerializer

    def get_queryset(self):
        category_id = self.request.query_params.get('category')
        if not category_id:
            return Tag.objects.order_by('name')
        category_ids = [category_id] + list(
            Category.objects.filter(parent_id=category_id).values_list('id', flat=True)
        )
        return Tag.objects.filter(products__category_id__in=category_ids).distinct().order_by('name')
