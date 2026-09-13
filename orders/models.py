from django.contrib.auth.models import User
from django.db import models

from catalog.models import Product


class ActiveOrderManager(models.Manager):
    """Отдаёт только не удалённые заказы - мягкое удаление, как и у
    Product/Category (ТЗ требует его и для заказов тоже)."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Order(models.Model):
    """Заказ. Контактные данные хранятся снимком на момент оформления —
    чтобы последующее изменение профиля не искажало историю заказов."""

    class DeliveryType(models.TextChoices):
        STANDARD = 'standard', 'Обычная'
        EXPRESS = 'express', 'Экспресс'

    class PaymentType(models.TextChoices):
        ONLINE = 'online', 'Онлайн-картой'
        SOMEONE = 'someone', 'Онлайн со случайного чужого счёта'

    class Status(models.TextChoices):
        CREATED = 'created', 'Оформлен'
        PROCESSING = 'processing', 'Оплата обрабатывается'
        PAID = 'paid', 'Оплачен'
        NOT_PAID = 'not_paid', 'Ошибка оплаты'

    # null=True — по ТЗ (стр. 4-5) незарегистрированный пользователь может
    # собрать корзину и нажать «Оформить заказ» ДО регистрации/входа: заказ
    # создаётся анонимным (user=None), id кладём в сессию (см.
    # OrderView._get_or_check_pending в views.py), а как только на Шаге 1
    # происходит регистрация или вход — заказ прикрепляется к пользователю.
    # on_delete=SET_NULL - реальное удаление пользователя теперь и так не
    # должно происходить (админка мягко удаляет через is_active, см.
    # accounts/admin.py), но даже в этом крайнем случае заказ не должен
    # пропадать вместе с пользователем.
    user = models.ForeignKey(
        User, verbose_name='покупатель', related_name='orders', null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField('дата создания', auto_now_add=True)

    full_name = models.CharField('ФИО', max_length=255, blank=True)
    email = models.EmailField('email', blank=True)
    phone = models.CharField('телефон', max_length=20, blank=True)
    comment = models.TextField('комментарий к заказу', blank=True)

    delivery_type = models.CharField(
        'тип доставки', max_length=20, choices=DeliveryType.choices, default=DeliveryType.STANDARD
    )
    payment_type = models.CharField(
        'тип оплаты', max_length=20, choices=PaymentType.choices, default=PaymentType.ONLINE
    )
    total_cost = models.DecimalField('итоговая стоимость', max_digits=10, decimal_places=2, default=0)
    status = models.CharField('статус', max_length=20, choices=Status.choices, default=Status.CREATED)

    city = models.CharField('город', max_length=255, blank=True)
    address = models.CharField('адрес', max_length=500, blank=True)
    is_deleted = models.BooleanField('удалён', default=False)

    objects = ActiveOrderManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'
        # -id вторым ключом — без него у двух заказов, созданных в один и тот
        # же момент (created_at совпадает с точностью БД), порядок в истории
        # не гарантирован; ТЗ требует именно убывание даты оформления
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'Заказ №{self.pk} от {self.full_name}'


class OrderItem(models.Model):
    """Позиция заказа. Название и цена — снимок на момент покупки."""

    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, verbose_name='товар', related_name='order_items', null=True, on_delete=models.SET_NULL
    )
    title = models.CharField('название на момент покупки', max_length=255)
    price = models.DecimalField('цена за единицу на момент покупки', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('количество')

    class Meta:
        verbose_name = 'позиция заказа'
        verbose_name_plural = 'позиции заказа'

    def __str__(self):
        return f'{self.title} × {self.quantity}'


class Payment(models.Model):
    """Результат обработки оплаты заказа. Полный номер (карты или «чужого
    счёта» — по ТЗ для обоих способов используется одно и то же поле ввода
    и одна и та же валидация) не хранится — только последние 4 цифры, для
    истории."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'В обработке'
        SUCCESS = 'success', 'Успешно'
        FAILED = 'failed', 'Отклонено'

    order = models.OneToOneField(Order, related_name='payment', on_delete=models.CASCADE)
    number_last4 = models.CharField('последние цифры номера', max_length=4, blank=True)
    status = models.CharField('статус', max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.CharField('сообщение об ошибке', max_length=255, blank=True)
    processed_at = models.DateTimeField('дата обработки', null=True, blank=True)

    class Meta:
        verbose_name = 'оплата'
        verbose_name_plural = 'оплаты'

    def __str__(self):
        return f'Оплата заказа №{self.order_id} — {self.get_status_display()}'
