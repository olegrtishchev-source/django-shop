from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile
from catalog.models import Product, ShopSettings
from catalog.serializers import ProductShortSerializer
from orders.models import Order, OrderItem, Payment
from orders.serializers import (
    BasketItemInputSerializer,
    CheckoutRegisterSerializer,
    OrderConfirmInputSerializer,
    OrderSerializer,
    PaymentInputSerializer,
)
from orders.tasks import process_payment


class BasketView(APIView):
    """/api/basket — корзина в сессии Django (архитектурное решение Этапа 0),
    без отдельной модели: `request.session['basket']` — словарь
    {id товара (строкой — ключи сессии сериализуются в JSON): количество}.

    Два нюанса контракта, подтверждённые чтением реального `app.js`
    (тот же принцип, что и на предыдущих подэтапах — при сомнении верим
    коду, а не тексту swagger.yaml):
    - поле `count` в позиции корзины (Basket/OrderProduct) — это количество
      товара В КОРЗИНЕ, а не остаток на складе, как в ProductShort каталога;
      то же имя поля, разный смысл по контексту;
    - `price` — цена ЗА ЕДИНИЦУ, а не общая цена за количество (вопреки
      текстовому примечанию в самом swagger.yaml): computed `basketCount` во
      фронтенде сам считает `count * price` для каждой позиции — если бы
      `price` уже была итоговой суммой, сумма получилась бы задвоенной.
    """

    def get(self, request):
        return Response(self._serialize_basket(request))

    def post(self, request):
        serializer = BasketItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data['id']
        count = serializer.validated_data['count']

        product = get_object_or_404(Product.objects, pk=product_id)

        basket = self._get_basket(request)
        key = str(product.pk)
        basket[key] = basket.get(key, 0) + count
        self._save_basket(request, basket)

        return Response(self._serialize_basket(request))

    def delete(self, request):
        serializer = BasketItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = str(serializer.validated_data['id'])
        count = serializer.validated_data['count']

        # Товара может уже не быть в корзине (двойной клик, устаревшая
        # страница) или он мог быть удалён из каталога — в обоих случаях
        # тихо ничего не делаем, а не 404: пользователь и так хочет, чтобы
        # позиции не было в корзине, конечный результат тот же
        basket = self._get_basket(request)
        if key in basket:
            basket[key] -= count
            if basket[key] <= 0:
                del basket[key]
            self._save_basket(request, basket)

        return Response(self._serialize_basket(request))

    @staticmethod
    def _get_basket(request):
        return dict(request.session.get('basket', {}))

    @staticmethod
    def _save_basket(request, basket):
        request.session['basket'] = basket
        request.session.modified = True

    def _serialize_basket(self, request):
        basket = self._get_basket(request)
        if not basket:
            return []

        products = {
            str(product.pk): product
            for product in Product.objects.filter(pk__in=basket.keys())
        }

        items = []
        for product_id, quantity in basket.items():
            product = products.get(product_id)
            if product is None:
                continue
            item = ProductShortSerializer(product, context={'request': request}).data
            item['count'] = quantity
            items.append(item)

        # Товар мог быть удалён/архивирован после добавления в корзину —
        # тихо чистим сессию от таких «осиротевших» позиций
        if len(products) != len(basket):
            self._save_basket(request, {pid: qty for pid, qty in basket.items() if pid in products})

        return items


def _order_queryset():
    return Order.objects.select_related('payment').prefetch_related('items__product__images')


def _get_order_for_request(request, order_id):
    """Доступ к заказу без пользователя (ТЗ позволяет собрать корзину и начать
    оформление анонимно) даётся только если id совпадает с тем, что мы сами
    положили в сессию при создании (pending_order_id) — так же, как сессия уже
    используется для корзины. Заказ с прикреплённым пользователем — только
    для него самого. В обоих случаях "не мой заказ" отдаём как 404, а не 403,
    чтобы не подтверждать чужому пользователю сам факт существования id."""

    order = get_object_or_404(_order_queryset(), pk=order_id)
    if order.user_id is not None:
        if not request.user.is_authenticated or order.user_id != request.user.id:
            raise Http404
    elif request.session.get('pending_order_id') != order.id:
        raise Http404
    return order


def _delivery_cost(delivery_type, items_total):
    settings_obj = ShopSettings.load()
    if delivery_type == Order.DeliveryType.EXPRESS:
        return settings_obj.express_delivery_cost
    if items_total < settings_obj.free_delivery_threshold:
        return settings_obj.standard_delivery_cost
    return 0


class OrderListCreateView(APIView):
    """GET /api/orders — история заказов пользователя (по убыванию даты —
    порядок уже задан в Order.Meta.ordering). POST /api/orders — создание
    заказа из корзины сессии (submitBasket() в cart.js), ровно как оно уже
    вызывается с Этапа 2.5 — тело запроса (сам массив корзины) не используем,
    источник истины — серверная сессия, а не то, что прислал клиент."""

    def get(self, request):
        if not request.user.is_authenticated:
            return Response([])
        orders = _order_queryset().filter(user=request.user)
        return Response(OrderSerializer(orders, many=True, context={'request': request}).data)

    def post(self, request):
        basket = dict(request.session.get('basket', {}))
        products = {
            str(product.pk): product
            for product in Product.objects.filter(pk__in=basket.keys())
        }
        if not products:
            return Response({'detail': 'Корзина пуста'}, status=status.HTTP_400_BAD_REQUEST)

        # Для авторизованного — сразу подставляем данные профиля (ТЗ, стр. 5:
        # "если пользователь авторизован, то данные выбираются из его профиля
        # автоматически и подставляются в форму"); getOrder() во фронтенде их
        # тут же и покажет, отдельно фронт под это не переписываем
        full_name, email, phone = '', '', ''
        if request.user.is_authenticated:
            profile = Profile.objects.filter(user=request.user).first()
            full_name = (profile.full_name if profile else '') or ''
            phone = (profile.phone if profile else '') or ''
            email = request.user.email or ''

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            full_name=full_name,
            email=email,
            phone=phone,
        )
        items_total = 0
        for product_id, quantity in basket.items():
            product = products.get(product_id)
            if product is None:
                continue
            OrderItem.objects.create(
                order=order, product=product, title=product.title, price=product.price, quantity=quantity,
            )
            items_total += product.price * quantity
        order.total_cost = items_total
        order.save(update_fields=['total_cost'])

        # Корзина превращается в заказ — сессионную корзину очищаем (то же
        # решение, что архитектурно было принято 07.09.2026)
        request.session['basket'] = {}
        request.session.modified = True

        if not request.user.is_authenticated:
            request.session['pending_order_id'] = order.id

        return Response({'orderId': order.id})


class OrderDetailView(APIView):
    """GET /api/order/{id} — данные заказа (getOrder() в order-detail.js).
    POST /api/order/{id} — подтверждение (confirmOrder()): сохраняет
    параметры пользователя/доставки/оплаты/комментарий и пересчитывает
    total_cost с учётом стоимости доставки по ShopSettings."""

    def get(self, request, order_id):
        order = _get_order_for_request(request, order_id)

        # Заказ ещё анонимный, но пользователь уже вошёл (например, через
        # попап логина на Шаге 1) — подставляем данные профиля прямо в
        # ответ, не сохраняя их в БД: ТЗ (стр. 4) требует, чтобы после
        # авторизации данные пользователя подставлялись в форму заказа, а
        # окончательная привязка заказа к пользователю происходит в post()
        # ниже (или через /register), не раньше.
        if order.user_id is None and request.user.is_authenticated and not order.full_name:
            profile = Profile.objects.filter(user=request.user).first()
            order.full_name = (profile.full_name if profile else '') or order.full_name
            order.phone = (profile.phone if profile else '') or order.phone
            order.email = request.user.email or order.email

        return Response(OrderSerializer(order, context={'request': request}).data)

    def post(self, request, order_id):
        order = _get_order_for_request(request, order_id)

        # Если пользователь вошёл через попап логина на Шаге 1 (а не
        # зарегистрировался через /register), заказ до этого момента
        # оставался анонимным — привязываем его к вошедшему пользователю
        # прямо здесь, при подтверждении.
        if order.user_id is None and request.user.is_authenticated:
            order.user = request.user
            request.session.pop('pending_order_id', None)

        serializer = OrderConfirmInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(order, field, value)

        items_total = sum(item.price * item.quantity for item in order.items.all())
        order.total_cost = items_total + _delivery_cost(order.delivery_type, items_total)
        order.save()

        return Response({'orderId': order.id})


class OrderCheckoutRegisterView(APIView):
    """POST /api/order/{id}/register — регистрация прямо на Шаге 1
    оформления заказа для неавторизованного пользователя (ТЗ, стр. 5).
    Отдельный от /api/sign-up эндпойнт: там логин строится по username,
    здесь — по email (и уникальность проверяется по email, как того требует
    ТЗ), плюс сразу привязывает ранее анонимный заказ к новому пользователю."""

    def post(self, request, order_id):
        order = _get_order_for_request(request, order_id)
        if order.user_id is not None:
            return Response({'detail': 'Заказ уже привязан к пользователю'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CheckoutRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.create_user(username=data['email'], email=data['email'], password=data['password'])
        Profile.objects.create(user=user, full_name=data['fullName'], phone=data.get('phone', ''))
        login(request, user)

        order.user = user
        order.full_name = data['fullName']
        order.email = data['email']
        order.phone = data.get('phone', '')
        order.save()

        request.session.pop('pending_order_id', None)

        return Response(OrderSerializer(order, context={'request': request}).data)


class PaymentView(APIView):
    """POST /api/payment/{id} — единая точка для обеих страниц оплаты
    (payment.html и paymentsomeone.html шлют один и тот же {number}).
    Синхронная валидация (чётность, ≤8 цифр) — здесь; сама имитация "похода
    в платёжную систему" — в Celery-таске (orders/tasks.py), честно через
    очередь, а не имитацией через поток/задержку (решение от 07.09.2026)."""

    def post(self, request, order_id):
        order = _get_order_for_request(request, order_id)

        serializer = PaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        number = serializer.validated_data['number']

        payment, _ = Payment.objects.update_or_create(
            order=order,
            defaults={'number_last4': number[-4:], 'status': Payment.Status.PENDING, 'error_message': ''},
        )
        order.status = Order.Status.PROCESSING
        order.save(update_fields=['status'])

        process_payment.delay(order.id, number)

        return Response({'orderId': order.id})
