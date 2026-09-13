from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ActiveCategoryManager(models.Manager):
    """Отдаёт только не удалённые категории -- тот же принцип мягкого
    удаления, что и у Product (ТЗ требует его и для категорий тоже)."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Category(models.Model):
    """Категория товара. Поддерживает одну вложенность (подкатегории).
    Удаление -- мягкое (is_deleted), как и у Product."""

    title = models.CharField('название', max_length=255)
    parent = models.ForeignKey(
        'self',
        verbose_name='родительская категория',
        null=True,
        blank=True,
        related_name='subcategories',
        on_delete=models.CASCADE,
    )
    image = models.ImageField('изображение', upload_to='categories/', blank=True, null=True)
    image_alt = models.CharField('alt-текст изображения', max_length=255, blank=True)
    is_deleted = models.BooleanField('удалена', default=False)

    objects = ActiveCategoryManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.title


class Tag(models.Model):
    """Тег товара. Не привязан к категории напрямую — фильтр /tags?category=
    вычисляется по тегам товаров этой категории."""

    name = models.CharField('название', max_length=100, unique=True)

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'теги'

    def __str__(self):
        return self.name


class ActiveProductManager(models.Manager):
    """Отдаёт только не удалённые товары — используется на витрине/в API."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Product(models.Model):
    """Товар. Удаление — мягкое (is_deleted), реальная запись из БД не убирается."""

    category = models.ForeignKey(
        Category, verbose_name='категория', related_name='products', on_delete=models.PROTECT
    )
    title = models.CharField('название', max_length=255)
    price = models.DecimalField('цена', max_digits=10, decimal_places=2)
    count = models.PositiveIntegerField('количество на складе', default=0)
    date = models.DateTimeField('дата добавления', auto_now_add=True)
    description = models.TextField('краткое описание', blank=True)
    full_description = models.TextField('полное описание', blank=True)
    free_delivery = models.BooleanField('бесплатная доставка', default=False)
    tags = models.ManyToManyField(Tag, verbose_name='теги', related_name='products', blank=True)
    rating = models.DecimalField('рейтинг', max_digits=3, decimal_places=2, default=0)
    sort_index = models.PositiveIntegerField(
        'индекс сортировки', default=0,
        help_text=(
            'Чем меньше значение, тем выше товар в топе на главной странице; '
            'при равном индексе -- сортировка по количеству покупок'
        ),
    )

    is_limited = models.BooleanField(
        'товар лимитированной серии', default=False,
        help_text='Показывается в разделе "Limited edition" на главной'
    )
    is_banner = models.BooleanField(
        'товар для баннера', default=False,
        help_text='Показывается в баннерах на главной странице'
    )
    is_deleted = models.BooleanField('удалён', default=False)

    objects = ActiveProductManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.title

    def update_rating(self):
        """Пересчитывает средний рейтинг по отзывам. Вызывается сигналом при
        сохранении/удалении Review, чтобы не считать AVG() на каждый запрос каталога."""
        aggregate = self.reviews.aggregate(models.Avg('rate'))
        self.rating = aggregate['rate__avg'] or 0
        self.save(update_fields=['rating'])


class ProductImage(models.Model):
    """Изображение товара. У товара их может быть несколько, порядок задаётся вручную."""

    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField('изображение', upload_to='products/')
    alt = models.CharField('alt-текст', max_length=255, blank=True)
    sort_order = models.PositiveSmallIntegerField('порядок', default=0)

    class Meta:
        verbose_name = 'изображение товара'
        verbose_name_plural = 'изображения товара'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.product.title} — изображение {self.pk}'


class Specification(models.Model):
    """Характеристика товара (пара «название — значение»)."""

    product = models.ForeignKey(Product, related_name='specifications', on_delete=models.CASCADE)
    name = models.CharField('название', max_length=255)
    value = models.CharField('значение', max_length=255)

    class Meta:
        verbose_name = 'характеристика'
        verbose_name_plural = 'характеристики'

    def __str__(self):
        return f'{self.name}: {self.value}'


class Review(models.Model):
    """Отзыв на товар."""

    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, verbose_name='пользователь', related_name='reviews',
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    author = models.CharField('имя автора', max_length=150)
    email = models.EmailField('email автора')
    text = models.TextField('текст отзыва')
    rate = models.PositiveSmallIntegerField(
        'оценка', validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    date = models.DateTimeField('дата', auto_now_add=True)

    class Meta:
        verbose_name = 'отзыв'
        verbose_name_plural = 'отзывы'
        ordering = ['-date']

    def __str__(self):
        return f'{self.author} — {self.product.title} ({self.rate})'


class Sale(models.Model):
    """Скидка на товар на определённый период."""

    product = models.OneToOneField(Product, related_name='sale', on_delete=models.CASCADE)
    sale_price = models.DecimalField('цена по скидке', max_digits=10, decimal_places=2)
    date_from = models.DateField('дата начала')
    date_to = models.DateField('дата окончания')

    class Meta:
        verbose_name = 'скидка'
        verbose_name_plural = 'скидки'

    def __str__(self):
        return f'{self.product.title}: {self.sale_price}'


class ShopSettings(models.Model):
    """Настройки магазина. Синглтон — всегда одна запись с pk=1."""

    standard_delivery_cost = models.DecimalField(
        'стоимость обычной доставки', max_digits=10, decimal_places=2, default=200
    )
    free_delivery_threshold = models.DecimalField(
        'сумма заказа для бесплатной доставки', max_digits=10, decimal_places=2, default=2000
    )
    express_delivery_cost = models.DecimalField(
        'стоимость экспресс-доставки', max_digits=10, decimal_places=2, default=500
    )

    class Meta:
        verbose_name = 'настройки магазина'
        verbose_name_plural = 'настройки магазина'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Настройки магазина'
