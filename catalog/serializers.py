from rest_framework import serializers

from catalog.models import Category, Product, ProductImage, Sale, Tag


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
