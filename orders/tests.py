from decimal import Decimal

from django.test import Client, TestCase

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
