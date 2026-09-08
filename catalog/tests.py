import datetime
from decimal import Decimal

from django.test import TestCase

from catalog.models import Category, Product, Sale, Tag


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
