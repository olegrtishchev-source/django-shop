from decimal import Decimal

from django.test import TestCase

from catalog.models import Category, Product, Tag


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
