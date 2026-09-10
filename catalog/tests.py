import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from catalog.models import Category, Product, ProductImage, Review, Sale, Specification, Tag


class TagListViewTests(TestCase):
    def setUp(self):
        self.parent = Category.objects.create(title='Электроника')
        self.child = Category.objects.create(title='Наушники', parent=self.parent)
        self.other = Category.objects.create(title='Одежда')

        self.tag_parent = Tag.objects.create(name='Новинка')
        self.tag_child = Tag.objects.create(name='Хит продаж')
        self.tag_other = Tag.objects.create(name='Скидка')
        self.tag_unused = Tag.objects.create(name='Без товаров')

        product_parent = Product.objects.create(
            category=self.parent, title='Телевизор', price=Decimal('10000.00'),
        )
        product_parent.tags.add(self.tag_parent)

        product_child = Product.objects.create(
            category=self.child, title='Наушники Х', price=Decimal('2000.00'),
        )
        product_child.tags.add(self.tag_child)

        product_other = Product.objects.create(
            category=self.other, title='Куртка', price=Decimal('5000.00'),
        )
        product_other.tags.add(self.tag_other)

    def test_all_tags_without_category(self):
        response = self.client.get('/api/tags')
        self.assertEqual(response.status_code, 200)
        names = {tag['name'] for tag in response.json()}
        self.assertEqual(names, {'Новинка', 'Хит продаж', 'Скидка', 'Без товаров'})

    def test_tags_filtered_by_category_includes_subcategories(self):
        response = self.client.get(f'/api/tags?category={self.parent.id}')
        self.assertEqual(response.status_code, 200)
        names = {tag['name'] for tag in response.json()}
        # тег родительской категории и тег товара из подкатегории — оба должны быть
        self.assertEqual(names, {'Новинка', 'Хит продаж'})

    def test_tags_filtered_by_unrelated_category(self):
        response = self.client.get(f'/api/tags?category={self.other.id}')
        self.assertEqual(response.status_code, 200)
        names = {tag['name'] for tag in response.json()}
        self.assertEqual(names, {'Скидка'})


class CategoryListViewTests(TestCase):
    def setUp(self):
        self.parent = Category.objects.create(title='Компьютеры')
        Category.objects.create(title='Ноутбуки', parent=self.parent)
        Category.objects.create(title='Одежда')  # без подкатегорий

    def test_returns_only_top_level_with_nested_subcategories(self):
        response = self.client.get('/api/categories')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        titles = {cat['title'] for cat in data}
        self.assertEqual(titles, {'Компьютеры', 'Одежда'})  # подкатегория не должна попасть на верхний уровень

        computers = next(cat for cat in data if cat['title'] == 'Компьютеры')
        self.assertEqual([sub['title'] for sub in computers['subcategories']], ['Ноутбуки'])


class CatalogViewTests(TestCase):
    def setUp(self):
        self.parent = Category.objects.create(title='Электроника')
        self.child = Category.objects.create(title='Наушники', parent=self.parent)
        self.other = Category.objects.create(title='Одежда')

        self.tag = Tag.objects.create(name='Новинка')

        self.cheap = Product.objects.create(
            category=self.parent, title='Дешёвый товар', price=Decimal('100.00'), count=5,
        )
        self.cheap.tags.add(self.tag)

        self.expensive = Product.objects.create(
            category=self.child, title='Дорогой товар', price=Decimal('9000.00'), count=3, free_delivery=True,
        )

        self.out_of_stock = Product.objects.create(
            category=self.other, title='Нет в наличии', price=Decimal('500.00'), count=0,
        )

    def test_default_available_only(self):
        response = self.client.get('/api/catalog')
        self.assertEqual(response.status_code, 200)
        titles = {item['title'] for item in response.json()['items']}
        self.assertNotIn('Нет в наличии', titles)

    def test_filter_by_name(self):
        response = self.client.get('/api/catalog', {'filter[name]': 'Дорогой'})
        titles = {item['title'] for item in response.json()['items']}
        self.assertEqual(titles, {'Дорогой товар'})

    def test_filter_by_price_range(self):
        response = self.client.get('/api/catalog', {'filter[minPrice]': '50', 'filter[maxPrice]': '200'})
        titles = {item['title'] for item in response.json()['items']}
        self.assertEqual(titles, {'Дешёвый товар'})

    def test_filter_free_delivery(self):
        response = self.client.get('/api/catalog', {'filter[freeDelivery]': 'true'})
        titles = {item['title'] for item in response.json()['items']}
        self.assertEqual(titles, {'Дорогой товар'})

    def test_filter_available_false_includes_out_of_stock(self):
        response = self.client.get('/api/catalog', {'filter[available]': 'false'})
        titles = {item['title'] for item in response.json()['items']}
        self.assertIn('Нет в наличии', titles)

    def test_category_includes_subcategory_products(self):
        response = self.client.get('/api/catalog', {'category': self.parent.id})
        titles = {item['title'] for item in response.json()['items']}
        self.assertEqual(titles, {'Дешёвый товар', 'Дорогой товар'})

    def test_sort_by_price_ascending(self):
        response = self.client.get('/api/catalog', {'sort': 'price', 'sortType': 'inc', 'filter[available]': 'false'})
        prices = [float(item['price']) for item in response.json()['items']]
        self.assertEqual(prices, sorted(prices))

    def test_tags_filter(self):
        response = self.client.get('/api/catalog?tags[]=' + str(self.tag.id))
        titles = {item['title'] for item in response.json()['items']}
        self.assertEqual(titles, {'Дешёвый товар'})

    def test_pagination_shape(self):
        response = self.client.get('/api/catalog', {'limit': 1, 'currentPage': 1, 'filter[available]': 'false'})
        data = response.json()
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['currentPage'], 1)
        self.assertEqual(data['lastPage'], 3)


class ProductsPopularLimitedBannersTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title='Категория')
        Product.objects.create(category=self.category, title='Обычный', price=Decimal('100.00'), rating=Decimal('3.00'))
        Product.objects.create(
            category=self.category, title='Топовый', price=Decimal('100.00'), rating=Decimal('5.00'),
        )
        Product.objects.create(
            category=self.category, title='Лимитка', price=Decimal('100.00'), is_limited=True,
        )
        Product.objects.create(
            category=self.category, title='Баннер', price=Decimal('100.00'), is_banner=True,
        )

    def test_popular_is_plain_array_sorted_by_rating(self):
        response = self.client.get('/api/products/popular')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(data[0]['title'], 'Топовый')

    def test_limited_returns_only_flagged(self):
        response = self.client.get('/api/products/limited')
        titles = {item['title'] for item in response.json()}
        self.assertEqual(titles, {'Лимитка'})

    def test_banners_returns_only_flagged(self):
        response = self.client.get('/api/banners')
        titles = {item['title'] for item in response.json()}
        self.assertEqual(titles, {'Баннер'})


class SalesViewTests(TestCase):
    def setUp(self):
        category = Category.objects.create(title='Категория')
        product = Product.objects.create(category=category, title='Товар со скидкой', price=Decimal('1000.00'))
        Sale.objects.create(
            product=product,
            sale_price=Decimal('800.00'),
            date_from=datetime.date(2026, 9, 5),
            date_to=datetime.date(2026, 9, 18),
        )

    def test_sales_response_shape(self):
        response = self.client.get('/api/sales')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['currentPage'], 1)
        self.assertEqual(len(data['items']), 1)
        item = data['items'][0]
        self.assertEqual(item['title'], 'Товар со скидкой')
        self.assertEqual(item['price'], '1000.00')
        self.assertEqual(item['salePrice'], '800.00')
        self.assertEqual(item['dateFrom'], '09-05')
        self.assertEqual(item['dateTo'], '09-18')


class StaticFilesServingTests(TestCase):
    """Регрессия на замечание куратора по MR: раздача /static/ и /media/ не
    должна зависеть от DJANGO_DEBUG — тот, кто проверяет проект, запускает
    его только через `manage.py runserver`, без collectstatic и отдельного
    веб-сервера под статику. Используется статика самой django.contrib.admin
    (всегда есть в INSTALLED_APPS), чтобы тест не зависел от установки
    внешнего пакета frontend."""

    @override_settings(DEBUG=False)
    def test_static_served_even_with_debug_false(self):
        response = self.client.get('/static/admin/css/base.css')
        self.assertEqual(response.status_code, 200)

    def test_static_served_with_debug_true(self):
        response = self.client.get('/static/admin/css/base.css')
        self.assertEqual(response.status_code, 200)


class ProductDetailViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(title='Ноутбуки')
        self.product = Product.objects.create(
            category=self.category, title='ProBook 15', price=Decimal('55000.00'),
            count=3, description='Краткое описание', full_description='<p>Полное описание</p>',
            free_delivery=True,
        )
        self.tag = Tag.objects.create(name='Новинка')
        self.product.tags.add(self.tag)
        ProductImage.objects.create(product=self.product, alt='Фото 1', sort_order=1)
        ProductImage.objects.create(product=self.product, alt='Фото 0', sort_order=0)
        Specification.objects.create(product=self.product, name='Экран', value='15.6"')
        Review.objects.create(
            product=self.product, author='Иван', email='ivan@example.com',
            text='Отличный ноутбук', rate=5,
        )

    def test_returns_full_product_shape(self):
        response = self.client.get(f'/api/product/{self.product.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['title'], 'ProBook 15')
        self.assertEqual(data['fullDescription'], '<p>Полное описание</p>')
        self.assertIs(data['freeDelivery'], True)
        self.assertEqual([img['alt'] for img in data['images']], ['Фото 0', 'Фото 1'])  # порядок по sort_order
        self.assertEqual(data['tags'], [{'id': self.tag.id, 'name': 'Новинка'}])
        self.assertEqual(len(data['reviews']), 1)
        self.assertEqual(data['reviews'][0]['author'], 'Иван')
        self.assertEqual(data['specifications'], [{'name': 'Экран', 'value': '15.6"'}])
        self.assertEqual(Decimal(data['rating']), Decimal('5.00'))  # пересчитан сигналом при создании отзыва

    def test_unknown_product_returns_404(self):
        response = self.client.get('/api/product/999999')
        self.assertEqual(response.status_code, 404)

    def test_soft_deleted_product_returns_404(self):
        self.product.is_deleted = True
        self.product.save(update_fields=['is_deleted'])
        response = self.client.get(f'/api/product/{self.product.id}')
        self.assertEqual(response.status_code, 404)


class ProductReviewsViewTests(TestCase):
    def setUp(self):
        category = Category.objects.create(title='Категория')
        self.product = Product.objects.create(category=category, title='Товар', price=Decimal('1000.00'))

    def test_create_review_returns_full_list_and_updates_rating(self):
        Review.objects.create(product=self.product, author='Пётр', email='petr@example.com', text='Норм', rate=3)

        response = self.client.post(
            f'/api/product/{self.product.id}/reviews',
            data={'author': 'Анна', 'email': 'anna@example.com', 'text': 'Хороший товар', 'rate': 5},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        authors = {review['author'] for review in data}
        self.assertEqual(authors, {'Пётр', 'Анна'})

        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('4.00'))  # (3 + 5) / 2

    def test_review_linked_to_logged_in_user(self):
        user = User.objects.create_user(username='ivanov', password='123456')
        self.client.force_login(user)

        self.client.post(
            f'/api/product/{self.product.id}/reviews',
            data={'author': 'Ивaнов', 'email': 'ivanov@example.com', 'text': 'Хорошо', 'rate': 4},
            content_type='application/json',
        )
        review = Review.objects.get(product=self.product)
        self.assertEqual(review.user, user)

    def test_missing_required_field_returns_400(self):
        response = self.client.post(
            f'/api/product/{self.product.id}/reviews',
            data={'email': 'a@example.com', 'text': 'Текст', 'rate': 3},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('author', response.json())

    def test_rate_out_of_range_returns_400(self):
        response = self.client.post(
            f'/api/product/{self.product.id}/reviews',
            data={'author': 'Аноним', 'email': 'a@example.com', 'text': 'Текст', 'rate': 6},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('rate', response.json())

    def test_unknown_product_returns_404(self):
        response = self.client.post(
            '/api/product/999999/reviews',
            data={'author': 'Анна', 'email': 'a@example.com', 'text': 'Текст', 'rate': 3},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)
