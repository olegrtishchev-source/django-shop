from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings

from catalog.models import Category, Product


class BasketViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title='Ноутбуки')
        self.product = Product.objects.create(
            category=self.category, title='ProBook 15', price=Decimal('55000.00'), count=10,
        )
        self.other_product = Product.objects.create(
            category=self.category, title='Мышь', price=Decimal('990.00'), count=50,
        )

    def test_empty_basket_by_default(self):
        response = self.client.get('/api/basket')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_add_item_returns_full_product_shape_with_basket_count(self):
        response = self.client.post(
            '/api/basket', data={'id': self.product.id, 'count': 2}, content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        item = data[0]
        self.assertEqual(item['id'], self.product.id)
        self.assertEqual(item['title'], 'ProBook 15')
        self.assertEqual(item['price'], '55000.00')  # цена за единицу, не итог за количество
        self.assertEqual(item['count'], 2)  # count здесь — количество в корзине, не остаток на складе
        self.assertIn('images', item)
        self.assertIn('tags', item)

    def test_add_same_item_twice_accumulates_count(self):
        self.client.post('/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json')
        response = self.client.post(
            '/api/basket', data={'id': self.product.id, 'count': 2}, content_type='application/json',
        )
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['count'], 3)

    def test_add_without_count_defaults_to_one(self):
        response = self.client.post('/api/basket', data={'id': self.product.id}, content_type='application/json')
        self.assertEqual(response.json()[0]['count'], 1)

    def test_add_unknown_product_returns_404(self):
        response = self.client.post('/api/basket', data={'id': 999999, 'count': 1}, content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_add_soft_deleted_product_returns_404(self):
        self.product.is_deleted = True
        self.product.save(update_fields=['is_deleted'])
        response = self.client.post(
            '/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    def test_add_zero_or_negative_count_returns_400(self):
        response = self.client.post(
            '/api/basket', data={'id': self.product.id, 'count': 0}, content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_basket_holds_several_different_products(self):
        self.client.post('/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json')
        response = self.client.post(
            '/api/basket', data={'id': self.other_product.id, 'count': 3}, content_type='application/json',
        )
        data = response.json()
        self.assertEqual(len(data), 2)
        by_id = {item['id']: item['count'] for item in data}
        self.assertEqual(by_id, {self.product.id: 1, self.other_product.id: 3})

    def test_remove_decrements_count(self):
        self.client.post('/api/basket', data={'id': self.product.id, 'count': 3}, content_type='application/json')
        response = self.client.delete(
            '/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json',
        )
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['count'], 2)

    def test_remove_full_count_deletes_item_from_basket(self):
        self.client.post('/api/basket', data={'id': self.product.id, 'count': 2}, content_type='application/json')
        response = self.client.delete(
            '/api/basket', data={'id': self.product.id, 'count': 2}, content_type='application/json',
        )
        self.assertEqual(response.json(), [])

    def test_remove_more_than_present_does_not_go_negative(self):
        self.client.post('/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json')
        response = self.client.delete(
            '/api/basket', data={'id': self.product.id, 'count': 100}, content_type='application/json',
        )
        self.assertEqual(response.json(), [])

    def test_remove_item_not_in_basket_is_noop(self):
        response = self.client.delete(
            '/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_removed_product_disappears_from_get_after_deletion_from_catalog(self):
        self.client.post('/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json')
        self.product.is_deleted = True
        self.product.save(update_fields=['is_deleted'])
        response = self.client.get('/api/basket')
        self.assertEqual(response.json(), [])

    def test_basket_is_isolated_per_session(self):
        client_a = Client()
        client_b = Client()
        client_a.post('/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json')

        response_a = client_a.get('/api/basket')
        response_b = client_b.get('/api/basket')
        self.assertEqual(len(response_a.json()), 1)
        self.assertEqual(response_b.json(), [])


class OrderCreateAndDetailTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title='Ноутбуки')
        self.product = Product.objects.create(
            category=self.category, title='ProBook 15', price=Decimal('1500.00'), count=10,
        )
        self.other_product = Product.objects.create(
            category=self.category, title='Мышь', price=Decimal('300.00'), count=50,
        )

    def _add_to_basket(self, client, product, count=1):
        client.post('/api/basket', data={'id': product.id, 'count': count}, content_type='application/json')

    def test_create_order_with_empty_basket_returns_400(self):
        response = self.client.post('/api/orders', data={}, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_create_order_from_basket_anonymous(self):
        self._add_to_basket(self.client, self.product, 2)
        response = self.client.post('/api/orders', data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        order_id = response.json()['orderId']

        from orders.models import Order
        order = Order.objects.get(pk=order_id)
        self.assertIsNone(order.user)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.total_cost, Decimal('3000.00'))

        # корзина должна очиститься
        self.assertEqual(self.client.get('/api/basket').json(), [])

    def test_create_order_authenticated_prefills_from_profile(self):
        from accounts.models import Profile
        user = User.objects.create_user(username='buyer', password='pass12345', email='buyer@example.com')
        Profile.objects.create(user=user, full_name='Покупатель Тестовый', phone='+7 900 000-00-00')
        self.client.force_login(user)
        self._add_to_basket(self.client, self.product, 1)

        response = self.client.post('/api/orders', data={}, content_type='application/json')
        order_id = response.json()['orderId']

        from orders.models import Order
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.user, user)
        self.assertEqual(order.full_name, 'Покупатель Тестовый')
        self.assertEqual(order.email, 'buyer@example.com')
        self.assertEqual(order.phone, '+7 900 000-00-00')

    def test_anonymous_order_accessible_only_from_the_session_that_created_it(self):
        self._add_to_basket(self.client, self.product, 1)
        order_id = self.client.post('/api/orders', data={}, content_type='application/json').json()['orderId']

        response = self.client.get(f'/api/order/{order_id}')
        self.assertEqual(response.status_code, 200)

        other_client = Client()
        response = other_client.get(f'/api/order/{order_id}')
        self.assertEqual(response.status_code, 404)

    def test_order_belonging_to_another_user_returns_404(self):
        owner = User.objects.create_user(username='owner', password='pass12345')
        stranger = User.objects.create_user(username='stranger', password='pass12345')
        self.client.force_login(owner)
        self._add_to_basket(self.client, self.product, 1)
        order_id = self.client.post('/api/orders', data={}, content_type='application/json').json()['orderId']

        self.client.logout()
        self.client.force_login(stranger)
        response = self.client.get(f'/api/order/{order_id}')
        self.assertEqual(response.status_code, 404)

    def test_get_prefills_profile_data_for_anonymous_order_once_logged_in(self):
        from accounts.models import Profile
        # заказ создаётся анонимно (как при оформлении до входа)...
        self._add_to_basket(self.client, self.product, 1)
        order_id = self.client.post('/api/orders', data={}, content_type='application/json').json()['orderId']

        # ...а затем пользователь входит в том же браузере (например, через
        # попап логина на Шаге 1) — GET должен сразу вернуть подставленные
        # из профиля данные, не дожидаясь явного подтверждения заказа
        user = User.objects.create_user(username='buyer', password='pass12345', email='buyer@example.com')
        from accounts.models import Profile as ProfileModel
        ProfileModel.objects.create(user=user, full_name='Покупатель Тестовый', phone='+7 900 000-00-00')
        self.client.force_login(user)

        response = self.client.get(f'/api/order/{order_id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['fullName'], 'Покупатель Тестовый')
        self.assertEqual(data['email'], 'buyer@example.com')
        self.assertEqual(data['phone'], '+7 900 000-00-00')

        # но в БД заказ пока НЕ привязан к пользователю — привязка происходит
        # только при подтверждении (post), не при простом просмотре
        from orders.models import Order
        order = Order.objects.get(pk=order_id)
        self.assertIsNone(order.user)

    def test_confirm_attaches_anonymous_order_to_now_logged_in_user(self):
        # тот же сценарий "вошёл через попап логина", но теперь проверяем
        # само подтверждение заказа (POST) — заказ должен окончательно
        # привязаться к пользователю, а не остаться анонимным
        self._add_to_basket(self.client, self.product, 1)
        order_id = self.client.post('/api/orders', data={}, content_type='application/json').json()['orderId']

        user = User.objects.create_user(username='buyer', password='pass12345', email='buyer@example.com')
        self.client.force_login(user)

        response = self.client.post(
            f'/api/order/{order_id}',
            data={
                'fullName': 'Покупатель Тестовый', 'email': 'buyer@example.com', 'phone': '+79000000000',
                'deliveryType': 'ordinary', 'paymentType': 'online',
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        from orders.models import Order
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.user, user)

        # сессионная метка анонимного заказа должна очиститься — иначе после
        # выхода из аккаунта кто угодно в этой сессии снова получил бы к нему доступ
        self.assertNotIn('pending_order_id', self.client.session)

    def test_confirm_order_recomputes_total_with_standard_delivery_cost(self):
        from catalog.models import ShopSettings
        settings_obj = ShopSettings.load()
        settings_obj.standard_delivery_cost = Decimal('200')
        settings_obj.free_delivery_threshold = Decimal('2000')
        settings_obj.save()

        self._add_to_basket(self.client, self.product, 1)  # 1500 — меньше порога 2000
        order_id = self.client.post('/api/orders', data={}, content_type='application/json').json()['orderId']

        response = self.client.post(
            f'/api/order/{order_id}',
            data={
                'fullName': 'Иван Иванов', 'email': 'ivan@example.com', 'phone': '+79001112233',
                'deliveryType': 'ordinary', 'paymentType': 'online', 'city': 'Москва', 'address': 'Тверская 1',
                'comment': 'Позвонить заранее',
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        from orders.models import Order
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.delivery_type, Order.DeliveryType.STANDARD)  # "ordinary" -> "standard"
        self.assertEqual(order.total_cost, Decimal('1700.00'))  # 1500 + 200 доставка
        self.assertEqual(order.comment, 'Позвонить заранее')

    def test_confirm_order_free_delivery_above_threshold(self):
        from catalog.models import ShopSettings
        settings_obj = ShopSettings.load()
        settings_obj.standard_delivery_cost = Decimal('200')
        settings_obj.free_delivery_threshold = Decimal('2000')
        settings_obj.save()

        self._add_to_basket(self.client, self.product, 2)  # 3000 — больше порога
        order_id = self.client.post('/api/orders', data={}, content_type='application/json').json()['orderId']
        self.client.post(
            f'/api/order/{order_id}',
            data={
                'fullName': 'Иван Иванов', 'email': 'ivan@example.com', 'phone': '+79001112233',
                'deliveryType': 'ordinary', 'paymentType': 'online',
            },
            content_type='application/json',
        )

        from orders.models import Order
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.total_cost, Decimal('3000.00'))  # доставка бесплатна

    def test_confirm_order_express_delivery_cost(self):
        from catalog.models import ShopSettings
        settings_obj = ShopSettings.load()
        settings_obj.express_delivery_cost = Decimal('500')
        settings_obj.save()

        self._add_to_basket(self.client, self.product, 1)
        order_id = self.client.post('/api/orders', data={}, content_type='application/json').json()['orderId']
        self.client.post(
            f'/api/order/{order_id}',
            data={
                'fullName': 'Иван Иванов', 'email': 'ivan@example.com', 'phone': '+79001112233',
                'deliveryType': 'express', 'paymentType': 'online',
            },
            content_type='application/json',
        )

        from orders.models import Order
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.total_cost, Decimal('2000.00'))  # 1500 + 500 экспресс


class OrderCheckoutRegisterTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title='Ноутбуки')
        self.product = Product.objects.create(
            category=self.category, title='ProBook 15', price=Decimal('1500.00'), count=10,
        )
        self.client.post('/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json')
        self.order_id = self.client.post(
            '/api/orders', data={}, content_type='application/json',
        ).json()['orderId']

    def test_register_creates_user_and_attaches_order(self):
        response = self.client.post(
            f'/api/order/{self.order_id}/register',
            data={
                'fullName': 'Новый Покупатель', 'email': 'new@example.com', 'phone': '+79001112233',
                'password': 'pass12345', 'passwordConfirm': 'pass12345',
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        from orders.models import Order
        order = Order.objects.get(pk=self.order_id)
        self.assertIsNotNone(order.user)
        self.assertEqual(order.user.email, 'new@example.com')
        self.assertEqual(order.full_name, 'Новый Покупатель')

        # пользователь сразу залогинен
        self.assertEqual(self.client.get('/api/profile').status_code, 200)

    def test_register_with_existing_email_returns_400_with_specific_message(self):
        User.objects.create_user(username='existing', email='taken@example.com', password='whatever123')
        response = self.client.post(
            f'/api/order/{self.order_id}/register',
            data={
                'fullName': 'Кто-то', 'email': 'taken@example.com', 'phone': '',
                'password': 'pass12345', 'passwordConfirm': 'pass12345',
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('авторизоваться', str(response.json()))

    def test_register_password_mismatch_returns_400(self):
        response = self.client.post(
            f'/api/order/{self.order_id}/register',
            data={
                'fullName': 'Кто-то', 'email': 'a@example.com', 'phone': '',
                'password': 'pass12345', 'passwordConfirm': 'other12345',
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class PaymentTests(TestCase):
    # override_settings здесь обязателен: в реальном проекте (в отличие от
    # зеркала) settings.py НЕ включает ALWAYS_EAGER — очередь честная, через
    # Redis (решение от 07.09.2026). Без этой настройки process_payment.delay()
    # в тесте либо упадёт с ошибкой подключения (если Redis не запущен), либо
    # выполнится асинхронно, и order.status ниже ещё не успеет обновиться.
    def setUp(self):
        self.category = Category.objects.create(title='Ноутбуки')
        self.product = Product.objects.create(
            category=self.category, title='ProBook 15', price=Decimal('1500.00'), count=10,
        )
        self.user = User.objects.create_user(username='buyer', password='pass12345')
        self.client.force_login(self.user)
        self.client.post('/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json')
        self.order_id = self.client.post(
            '/api/orders', data={}, content_type='application/json',
        ).json()['orderId']

    def test_payment_rejects_odd_number(self):
        response = self.client.post(
            f'/api/payment/{self.order_id}', data={'number': '1234567'}, content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_payment_rejects_number_longer_than_8_digits(self):
        response = self.client.post(
            f'/api/payment/{self.order_id}', data={'number': '123456780'}, content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_payment_rejects_non_numeric(self):
        response = self.client.post(
            f'/api/payment/{self.order_id}', data={'number': '12ab5678'}, content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_payment_success_when_even_and_not_ending_in_zero(self):
        response = self.client.post(
            f'/api/payment/{self.order_id}', data={'number': '12345678'}, content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        from orders.models import Order, Payment
        order = Order.objects.get(pk=self.order_id)
        payment = Payment.objects.get(order=order)
        # CELERY_TASK_ALWAYS_EAGER=True в тестовых настройках — таск уже
        # выполнился синхронно к этому моменту
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(payment.number_last4, '5678')

    def test_payment_fails_when_ends_in_zero(self):
        self.client.post(
            f'/api/payment/{self.order_id}', data={'number': '12345670'}, content_type='application/json',
        )

        from orders.models import Order, Payment
        order = Order.objects.get(pk=self.order_id)
        payment = Payment.objects.get(order=order)
        self.assertEqual(order.status, Order.Status.NOT_PAID)
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertTrue(payment.error_message)

    def test_order_api_reports_human_readable_status(self):
        # На странице заказа должен отображаться понятный статус ("Оплачен"),
        # а не внутренний код ("paid") — ТЗ, стр. 6
        self.client.post(f'/api/payment/{self.order_id}', data={'number': '12345678'}, content_type='application/json')

        response = self.client.get(f'/api/order/{self.order_id}')
        data = response.json()
        self.assertEqual(data['status'], 'paid')
        self.assertEqual(data['statusDisplay'], 'Оплачен')


class OrderHistoryTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title='Ноутбуки')
        self.product = Product.objects.create(
            category=self.category, title='ProBook 15', price=Decimal('1500.00'), count=10,
        )

    def test_history_requires_authentication_returns_empty_list(self):
        response = self.client.get('/api/orders')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_history_returns_only_own_orders(self):
        owner = User.objects.create_user(username='owner', password='pass12345')
        stranger = User.objects.create_user(username='stranger', password='pass12345')

        self.client.force_login(owner)
        self.client.post('/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json')
        self.client.post('/api/orders', data={}, content_type='application/json')
        self.client.logout()

        self.client.force_login(stranger)
        response = self.client.get('/api/orders')
        self.assertEqual(response.json(), [])

    def test_history_sorted_by_date_descending(self):
        # ТЗ требует историю заказов по убыванию даты (самые новые — первыми)
        user = User.objects.create_user(username='buyer', password='pass12345')
        self.client.force_login(user)

        self.client.post('/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json')
        first_id = self.client.post('/api/orders', data={}, content_type='application/json').json()['orderId']

        self.client.post('/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json')
        second_id = self.client.post('/api/orders', data={}, content_type='application/json').json()['orderId']

        self.client.post('/api/basket', data={'id': self.product.id, 'count': 1}, content_type='application/json')
        third_id = self.client.post('/api/orders', data={}, content_type='application/json').json()['orderId']

        response = self.client.get('/api/orders')
        returned_ids = [order['id'] for order in response.json()]
        self.assertEqual(returned_ids, [third_id, second_id, first_id])
