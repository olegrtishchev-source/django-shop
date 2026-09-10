from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Category, Product, Sale, Tag
from catalog.serializers import (
    CategorySerializer,
    ProductFullSerializer,
    ProductShortSerializer,
    ReviewCreateSerializer,
    ReviewSerializer,
    SaleItemSerializer,
    TagSerializer,
)


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


class CategoryListView(ListAPIView):
    """/api/categories — меню каталога: только верхнеуровневые категории,
    подкатегории вложены внутрь (сериализатор), без пагинации — swagger отдаёт
    просто массив."""

    serializer_class = CategorySerializer
    pagination_class = None
    queryset = Category.objects.filter(parent__isnull=True).order_by('title')


class CatalogPagination(PageNumberPagination):
    """Формат ответа /api/catalog и /api/sales — {items, currentPage, lastPage},
    а не стандартный DRF-формат {count, next, previous, results}. Имена
    query-параметров — под контракт фронтенда (currentPage/limit, не page/page_size)."""

    page_size = 20
    page_query_param = 'currentPage'
    page_size_query_param = 'limit'

    def get_paginated_response(self, data):
        return Response({
            'items': data,
            'currentPage': self.page.number,
            'lastPage': self.page.paginator.num_pages,
        })


class CatalogView(ListAPIView):
    """/api/catalog — список товаров с фильтром, сортировкой, тегами и
    пагинацией. Axios (реальный код catalog.js) сериализует вложенный объект
    filter bracket-нотацией (filter[name]=..., проверено вживую через
    axios.getUri), а массив тегов — как tags[]=1&tags[]=2, поэтому читаем
    именно эти ключи, а не плоские filter/tags."""

    serializer_class = ProductShortSerializer
    pagination_class = CatalogPagination

    SORT_FIELDS = {
        'rating': 'rating',
        'price': 'price',
        'reviews': 'reviews_count',
        'date': 'date',
    }

    def get_queryset(self):
        params = self.request.query_params
        qs = Product.objects.all()

        name = params.get('filter[name]')
        if name:
            qs = qs.filter(title__icontains=name)

        min_price = params.get('filter[minPrice]')
        if min_price not in (None, ''):
            qs = qs.filter(price__gte=min_price)

        max_price = params.get('filter[maxPrice]')
        if max_price not in (None, ''):
            qs = qs.filter(price__lte=max_price)

        if params.get('filter[freeDelivery]') == 'true':
            qs = qs.filter(free_delivery=True)

        # available по умолчанию true и в swagger, и в data() catalog.js
        if params.get('filter[available]', 'true') == 'true':
            qs = qs.filter(count__gt=0)

        category_id = params.get('category')
        if category_id:
            category_ids = [category_id] + list(
                Category.objects.filter(parent_id=category_id).values_list('id', flat=True)
            )
            qs = qs.filter(category_id__in=category_ids)

        tag_ids = params.getlist('tags[]')
        if tag_ids:
            qs = qs.filter(tags__id__in=tag_ids).distinct()

        qs = qs.annotate(reviews_count=Count('reviews'))

        sort = params.get('sort', 'date')
        sort_type = params.get('sortType', 'dec')
        sort_field = self.SORT_FIELDS.get(sort, 'date')
        return qs.order_by(sort_field if sort_type == 'inc' else f'-{sort_field}')


class PopularProductsView(ListAPIView):
    """/api/products/popular — вычисляемая выборка: топ-8 товаров по рейтингу
    (решение согласовано на Этапе 1, ручного флага под это нет)."""

    serializer_class = ProductShortSerializer
    pagination_class = None
    queryset = Product.objects.order_by('-rating', '-id')[:8]


class LimitedProductsView(ListAPIView):
    """/api/products/limited — товары с флагом is_limited (курируется вручную
    в админке)."""

    serializer_class = ProductShortSerializer
    pagination_class = None
    queryset = Product.objects.filter(is_limited=True)


class BannersView(ListAPIView):
    """/api/banners — товары с флагом is_banner (курируется вручную в админке)."""

    serializer_class = ProductShortSerializer
    pagination_class = None
    queryset = Product.objects.filter(is_banner=True)


class SalesView(ListAPIView):
    """/api/sales — товары со скидкой, с пагинацией (currentPage), лимит
    страницы — 20, как и в каталоге (в sales.js параметр limit не передаётся)."""

    serializer_class = SaleItemSerializer
    pagination_class = CatalogPagination
    queryset = Sale.objects.select_related('product').order_by('date_from')


class ProductDetailView(RetrieveAPIView):
    """/api/product/<id> — детальная карточка товара, контракт ProductFull.
    Мягко удалённые товары не отдаются (Product.objects — активный менеджер),
    прямая ссылка на них — обычный 404, как и на несуществующий id."""

    serializer_class = ProductFullSerializer
    queryset = Product.objects.select_related('category').prefetch_related(
        'images', 'tags', 'reviews', 'specifications',
    )


class ProductReviewsView(APIView):
    """/api/product/<id>/reviews — путь взят из реального product-detail.js
    (submitReview), а не из swagger: там эндпоинт ошибочно в единственном
    числе — /product/{id}/review. Тот же класс расхождений, что уже
    разбирался в 2.1-2.2, каждый эндпоинт сверяется с реальным JS отдельно.
    Отдаёт весь актуальный список отзывов товара после создания — ровно то,
    что фронтенд ждёт в `data` и кладёт в `this.product.reviews`."""

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(product=product)
        if request.user.is_authenticated:
            review.user = request.user
            review.save(update_fields=['user'])
        reviews = product.reviews.all()
        return Response(ReviewSerializer(reviews, many=True).data)
