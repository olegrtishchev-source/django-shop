from django.contrib.auth.models import User
from django.db import models

from catalog.models import Product


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

    user = models.ForeignKey(User, verbose_name='покупатель', related_name='orders', on_delete=models.CASCADE)
    created_at = models.DateTimeField('дата создания', auto_now_add=True)

    full_name = models.CharField('ФИО', max_length=255)
    email = models.EmailField('email')
    phone = models.CharField('телефон', max_length=20)

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

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'
        ordering = ['-created_at']

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
    """Результат обработки оплаты заказа. Полный номер карты не хранится —
    только последние 4 цифры, для истории."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'В обработке'
        SUCCESS = 'success', 'Успешно'
        FAILED = 'failed', 'Отклонено'

    order = models.OneToOneField(Order, related_name='payment', on_delete=models.CASCADE)
    card_last4 = models.CharField('последние 4 цифры карты', max_length=4, blank=True)
    status = models.CharField('статус', max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.CharField('сообщение об ошибке', max_length=255, blank=True)
    processed_at = models.DateTimeField('дата обработки', null=True, blank=True)

    class Meta:
        verbose_name = 'оплата'
        verbose_name_plural = 'оплаты'

    def __str__(self):
        return f'Оплата заказа №{self.order_id} — {self.get_status_display()}'
