import re

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.validators import validate_phone_format
from catalog.serializers import ProductImageSerializer


class BasketItemInputSerializer(serializers.Serializer):
    """Тело POST/DELETE /api/basket — `{id, count}`, ровно то, что шлют
    addToBasket()/removeFromBasket() в app.js. В реальном JS `count` всегда
    положительное число (кнопки +/- шлют 1, кнопка «Купить» на детальной
    странице — выбранное на степпере количество, но не меньше 1) — по умолчанию
    тоже 1, как и в addToBasket(item, count = 1)."""

    id = serializers.IntegerField()
    count = serializers.IntegerField(min_value=1, default=1)


class OrderItemSerializer(serializers.Serializer):
    """Одна позиция заказа для контракта Order.products — берём снимок
    (title/price/count) из самой OrderItem, а картинку и описание — с живого
    товара, если он ещё существует (мог быть удалён после покупки, тогда
    отдаём пустые значения, а не 500)."""

    id = serializers.IntegerField(source='product_id')
    title = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    count = serializers.IntegerField(source='quantity')
    description = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    def get_description(self, obj):
        return obj.product.description if obj.product else ''

    def get_images(self, obj):
        if not obj.product:
            return []
        return ProductImageSerializer(obj.product.images.all(), many=True, context=self.context).data


class OrderSerializer(serializers.Serializer):
    """Контракт Order из swagger — camelCase-поля строго под order-detail.js/
    historyOrder.js/oneorder.html (поле products, createdAt, totalCost и т.д.)."""

    id = serializers.IntegerField()
    createdAt = serializers.DateTimeField(source='created_at', format='%Y-%m-%d %H:%M')
    fullName = serializers.CharField(source='full_name')
    email = serializers.EmailField()
    phone = serializers.CharField()
    deliveryType = serializers.CharField(source='delivery_type')
    paymentType = serializers.CharField(source='payment_type')
    totalCost = serializers.DecimalField(source='total_cost', max_digits=10, decimal_places=2)
    # status — код статуса ('processing'/'paid'/...), для логики на фронте
    # (опрос страницы ожидания оплаты, условный показ кнопки «Оплатить ещё
    # раз»); statusDisplay — человекочитаемый текст ("Оплачен"/"Ошибка
    # оплаты" и т.д.) для показа на странице заказа (ТЗ, стр. 6)
    status = serializers.CharField()
    statusDisplay = serializers.CharField(source='get_status_display')
    city = serializers.CharField()
    address = serializers.CharField()
    comment = serializers.CharField()
    products = OrderItemSerializer(many=True, source='items')
    paymentError = serializers.SerializerMethodField()

    def get_paymentError(self, obj):
        # payment создаётся только когда пользователь дошёл до оплаты —
        # до этого момента ошибки просто нет (не пустая строка, а null,
        # как и ждёт paymentError !== null в oneorder.html)
        payment = getattr(obj, 'payment', None)
        if payment is not None and payment.status == 'failed' and payment.error_message:
            return payment.error_message
        return None


class OrderConfirmInputSerializer(serializers.Serializer):
    """Тело POST /api/order/{id} — confirmOrder() в order-detail.js шлёт
    `{...this}` (весь компонент целиком, включая orderId/status/products/
    totalCost и т.п.) — сериализатор явно берёт только то, что реально можно
    менять на этом шаге, остальное игнорируется."""

    fullName = serializers.CharField(source='full_name', max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, validators=[validate_phone_format])
    deliveryType = serializers.ChoiceField(source='delivery_type', choices=['standard', 'express', 'ordinary'])
    paymentType = serializers.ChoiceField(source='payment_type', choices=['online', 'someone'])
    city = serializers.CharField(max_length=255, allow_blank=True, required=False, default='')
    address = serializers.CharField(max_length=500, allow_blank=True, required=False, default='')
    comment = serializers.CharField(allow_blank=True, required=False, default='')

    def validate_deliveryType(self, value):
        # order.html шлёт радиокнопками значения "ordinary"/"express" —
        # приводим "ordinary" к модельному "standard"
        return 'standard' if value == 'ordinary' else value


class CheckoutRegisterSerializer(serializers.Serializer):
    """Тело регистрации прямо на Шаге 1 оформления заказа (ТЗ, стр. 5) —
    отдельно от обычной /api/sign-up: там логин по username, здесь — по
    email (уникальность проверяется по email, не по username, как того
    требует ТЗ)."""

    fullName = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True, validators=[validate_phone_format],
    )
    password = serializers.CharField(min_length=1)
    passwordConfirm = serializers.CharField(min_length=1)

    def validate(self, attrs):
        if attrs['password'] != attrs['passwordConfirm']:
            raise serializers.ValidationError({'passwordConfirm': 'Пароли не совпадают'})
        try:
            validate_password(attrs['password'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'Пользователь с указанным email существует, вы можете авторизоваться'
            )
        return value


class PaymentInputSerializer(serializers.Serializer):
    """Тело POST /api/payment/{id} — одно поле "number" что для карты, что
    для счёта (ТЗ, стр. 5-6): "для обоих способов оплаты используется
    одинаковая валидация: номер должен быть чётным и не длиннее восьми
    цифр". Эта валидация — синхронная, до постановки в очередь; отдельная,
    более узкая проверка (не заканчивается на 0) — уже внутри фиктивного
    сервиса оплаты (Celery-таск), не здесь."""

    number = serializers.CharField(max_length=8, min_length=1)

    def validate_number(self, value):
        if not re.fullmatch(r'\d+', value):
            raise serializers.ValidationError('Номер должен состоять только из цифр')
        if int(value) % 2 != 0:
            raise serializers.ValidationError('Номер должен быть чётным')
        return value
