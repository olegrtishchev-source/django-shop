from django.db.models import Count, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Category, Product, Sale, Tag
from catalog.serializers import (
    CategorySerializer,
    CompareItemSerializer,
    ProductFullSerializer,
    ProductShortSerializer,
    ReviewCreateSerializer,
    ReviewSerializer,
    SaleItemSerializer,
    SubcategorySerializer,
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
    """/api/products/popular — топ-8 по «индексу сортировки» (ТЗ, стр. 2):
    чем меньше sort_index, тем выше товар; при совпадении индекса -
    по количеству покупок (сумма quantity по всем OrderItem на этот товар).
    Раньше сортировали по рейтингу - это было временной заменой на Этапе 1,
    пока не завели отдельное поле sort_index."""

    serializer_class = ProductShortSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Product.objects
            .annotate(purchases=Coalesce(Sum('order_items__quantity'), Value(0)))
            .order_by('sort_index', '-purchases', '-id')[:8]
        )


class LimitedProductsView(ListAPIView):
    """/api/products/limited — товары с флагом is_limited (курируется вручную
    в админке). ТЗ ограничивает блок «Ограниченный тираж» 16 товарами."""

    serializer_class = ProductShortSerializer
    pagination_class = None
    queryset = Product.objects.filter(is_limited=True)[:16]


class BannersView(ListAPIView):
    """/api/banners — товары с флагом is_banner (курируется вручную в
    админке). ТЗ говорит о «трёх избранных категориях товаров» на главной,
    но реальная вёрстка/swagger описывают этот блок как три товара-баннера,
    каждый со ссылкой на свою категорию (banner.category) - трогать
    вёрстку нельзя, поэтому ограничиваем количество тремя, сохраняя
    контракт как есть."""

    serializer_class = ProductShortSerializer
    pagination_class = None
    queryset = Product.objects.filter(is_banner=True)[:3]


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


class CompareView(APIView):
    """/api/compare — страница сравнения товаров (Этап 3). ТЗ упоминает
    иконку перехода на неё в шапке сайта, но готовой вёрстки и JS под нею
    в пакете `diploma-frontend` нет вообще (проверено чтением всех
    шаблонов и `.js`-файлов — ни одной ссылки на неё, только мёртвый
    jQuery-код `.Compare` в `scripts.js`, не подключённый ни к одной
    странице). Сделано с нуля по решению Олега.

    Хранение — в сессии, без модели в БД, по тому же принципу, что и
    корзина (Этап 2.5): `request.session['compare']` — список id товаров
    (не словарь, как в корзине — количество тут не нужно, товар либо
    в сравнении, либо нет). Список хранит порядок добавления.

    Ограничение — до 4 товаров одновременно и только одной категории
    (решение Олега 11.09.2026, ТЗ так делать не требует, но так поступает
    большинство реальных магазинов — сравнивать холодильник с ноутбуком
    бессмысленно). При попытке добавить товар другой категории список
    не подменяется молча: ответ — 409 с `code: "different_category"`,
    страница сравнения показывает пользователю подтверждение и, если он
    согласен, шлёт тот же запрос повторно с `replace: true`."""

    MAX_ITEMS = 4

    def get(self, request):
        return Response(self._serialize(request))

    def post(self, request):
        product_id = request.data.get('id')
        if product_id is None:
            return Response({'detail': 'Не указан id товара'}, status=status.HTTP_400_BAD_REQUEST)
        replace = bool(request.data.get('replace'))

        product = get_object_or_404(Product.objects, pk=product_id)
        ids = self._get_ids(request)

        if product.id in ids:
            return Response(self._serialize(request))

        if ids:
            current_category_id = (
                Product.objects.filter(pk=ids[0]).values_list('category_id', flat=True).first()
            )
            if current_category_id is not None and product.category_id != current_category_id:
                if not replace:
                    return Response(
                        {
                            'detail': 'Список сравнения содержит товары другой категории.',
                            'code': 'different_category',
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
                ids = []

        if len(ids) >= self.MAX_ITEMS:
            return Response(
                {
                    'detail': f'Можно сравнивать не более {self.MAX_ITEMS} товаров одновременно.',
                    'code': 'limit_reached',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ids.append(product.id)
        self._save_ids(request, ids)
        return Response(self._serialize(request))

    def delete(self, request):
        product_id = request.data.get('id')
        ids = self._get_ids(request)
        if product_id is None:
            # без id — очистка всего списка (кнопка "очистить сравнение")
            ids = []
        else:
            ids = [pid for pid in ids if pid != int(product_id)]
        self._save_ids(request, ids)
        return Response(self._serialize(request))

    @staticmethod
    def _get_ids(request):
        return list(request.session.get('compare', []))

    @staticmethod
    def _save_ids(request, ids):
        request.session['compare'] = ids
        request.session.modified = True

    def _serialize(self, request):
        ids = self._get_ids(request)
        products = Product.objects.filter(pk__in=ids).prefetch_related('images', 'specifications')
        by_id = {product.id: product for product in products}
        # .filter(pk__in=...) не сохраняет порядок — восстанавливаем порядок
        # добавления из самого списка id в сессии
        ordered = [by_id[pid] for pid in ids if pid in by_id]

        # товар мог быть удалён/архивирован после добавления в сравнение —
        # тихо чистим сессию от таких позиций (тот же приём, что и в корзине)
        if len(ordered) != len(ids):
            self._save_ids(request, [product.id for product in ordered])

        category = None
        if ordered:
            category = SubcategorySerializer(ordered[0].category, context={'request': request}).data

        return {
            'items': CompareItemSerializer(ordered, many=True, context={'request': request}).data,
            'category': category,
            'maxItems': self.MAX_ITEMS,
        }
