from rest_framework import serializers

from catalog.models import Category, Product, ProductImage, Review, Sale, Specification, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class SubcategorySerializer(serializers.ModelSerializer):
    """Категория без вложенных подкатегорий — используется и как самостоятельная
    подкатегория внутри CategorySerializer, и как база для него (вложенность
    на курсе только на один уровень, второй уровень подкатегориям не нужен)."""

    image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'title', 'image']

    def get_image(self, obj):
        if not obj.image:
            return None
        return {'src': obj.image.url, 'alt': obj.image_alt}


class CategorySerializer(SubcategorySerializer):
    subcategories = SubcategorySerializer(many=True, read_only=True)

    class Meta(SubcategorySerializer.Meta):
        fields = SubcategorySerializer.Meta.fields + ['subcategories']


class ProductImageSerializer(serializers.ModelSerializer):
    src = serializers.ImageField(source='image', read_only=True)

    class Meta:
        model = ProductImage
        fields = ['src', 'alt']


class ProductShortSerializer(serializers.ModelSerializer):
    """Карточка товара для листингов (каталог, популярное, лимитка, баннеры) —
    контракт ProductShort из swagger."""

    freeDelivery = serializers.BooleanField(source='free_delivery')
    images = ProductImageSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'price', 'count', 'date', 'title', 'description',
            'freeDelivery', 'images', 'tags', 'reviews', 'rating',
        ]

    def get_reviews(self, obj):
        return obj.reviews.count()


class SaleItemSerializer(serializers.ModelSerializer):
    """Карточка скидки — контракт SaleItem из swagger. id ведёт на страницу
    товара (`/product/${card.id}/` в sale.html), поэтому это id самого товара,
    а не строки Sale."""

    id = serializers.IntegerField(source='product.id', read_only=True)
    title = serializers.CharField(source='product.title', read_only=True)
    price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    salePrice = serializers.DecimalField(source='sale_price', max_digits=10, decimal_places=2, read_only=True)
    dateFrom = serializers.SerializerMethodField()
    dateTo = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ['id', 'price', 'salePrice', 'dateFrom', 'dateTo', 'title', 'images']

    def get_dateFrom(self, obj):
        return obj.date_from.strftime('%m-%d')

    def get_dateTo(self, obj):
        return obj.date_to.strftime('%m-%d')

    def get_images(self, obj):
        return ProductImageSerializer(obj.product.images.all(), many=True, context=self.context).data


class SpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specification
        fields = ['name', 'value']


class ReviewSerializer(serializers.ModelSerializer):
    """Отзыв для отображения — контракт Review из swagger. Дата отдаётся уже
    отформатированной строкой (как и везде в проекте, где дата уходит на
    фронтенд), формат — как в примере swagger ('2023-05-05 12:12')."""

    date = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['author', 'email', 'text', 'rate', 'date']

    def get_date(self, obj):
        return obj.date.strftime('%Y-%m-%d %H:%M')


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Вход для POST /api/product/<id>/reviews — только то, что реально шлёт
    submitReview() в product-detail.js (author/email/text/rate); product и
    date выставляются во view, не берутся из тела запроса."""

    class Meta:
        model = Review
        fields = ['author', 'email', 'text', 'rate']


class ProductFullSerializer(serializers.ModelSerializer):
    """Детальная карточка товара — контракт ProductFull из swagger.

    Есть два расхождения со свагером, найденные чтением реального шаблона
    product.html/product-detail.js (тот же принцип, что и в 2.1-2.3 — при
    расхождении верим реальному коду, не тексту документации):
    - `tags`: swagger описывает элементы как голые строки (tagId), но
      шаблон делает `${ tag.name }$` — значит фронтенду нужны объекты тегов
      (id+name), как и в ProductShort. Отдаём через TagSerializer.
    - `reviews`: в ProductShort это число (счётчик), а в ProductFull —
      массив объектов Review целиком (шаблон явно перебирает
      `v-for="review in product.reviews"` и читает review.author/date/rate/text).
    """

    freeDelivery = serializers.BooleanField(source='free_delivery')
    fullDescription = serializers.CharField(source='full_description')
    images = ProductImageSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    specifications = SpecificationSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'price', 'count', 'date', 'title', 'description',
            'fullDescription', 'freeDelivery', 'images', 'tags', 'reviews',
            'specifications', 'rating',
        ]


class CompareItemSerializer(serializers.ModelSerializer):
    """Карточка товара для страницы сравнения (/api/compare, Этап 3).
    Готового контракта в swagger.yaml нет — эндпоинт и страница сделаны
    с нуля (см. ниже CompareView), набор полей подобран под таблицу
    сравнения: карточка товара + полный список характеристик."""

    images = ProductImageSerializer(many=True, read_only=True)
    specifications = SpecificationSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'category', 'title', 'price', 'rating', 'images', 'specifications']
