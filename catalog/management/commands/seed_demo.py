"""
Наполняет базу демоданными для дипломного проекта Megano: покупатели с
простым паролем (123456), администратор, категории, теги, товары, отзывы,
скидки, демо-заказ. Идемпотентна — повторный запуск не создаёт дублей.

Запуск: python manage.py seed_demo
Фикстура для сдачи собирается отдельно:
python manage.py dumpdata auth.user auth.group accounts catalog orders \
    --indent 2 --output fixtures/demo_data.json
"""
import datetime
import decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Profile
from catalog.management.commands._demo_images import generate_product_image
from catalog.models import Category, Product, ProductImage, Review, Sale, ShopSettings, Specification, Tag
from orders.models import Order, OrderItem, Payment


class Command(BaseCommand):
    help = 'Наполняет базу демоданными (покупатели, товары, заказы и т.д.)'

    def handle(self, *args, **options):
        today = datetime.date.today()

        def make_user(username, password, first_name, last_name, email, group_name,
                      is_staff=False, is_superuser=False):
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'first_name': first_name, 'last_name': last_name, 'email': email},
            )
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.set_password(password)
            user.save()
            group = Group.objects.get(name=group_name)
            user.groups.add(group)
            Profile.objects.get_or_create(
                user=user, defaults={'full_name': f'{first_name} {last_name}', 'phone': '+7 900 000-00-00'}
            )
            return user

        admin = make_user('admin', 'admin12345', 'Админ', 'Админов', 'admin@megano.local',
                           'Администратор', is_staff=True, is_superuser=True)
        buyer1 = make_user('ivanov', '123456', 'Иван', 'Иванов', 'ivanov@example.com', 'Покупатель')
        buyer2 = make_user('petrova', '123456', 'Мария', 'Петрова', 'petrova@example.com', 'Покупатель')

        def make_category(title, parent=None, icon=None):
            category, _ = Category.objects.get_or_create(title=title, parent=parent)
            # меню каталога на фронтенде безусловно обращается к
            # category.image.src — без картинки страница падает точно так же,
            # как раньше падала из-за images[0] у товаров
            if icon and not category.image:
                category.image.save(f'{icon}.png', generate_product_image(icon), save=False)
                category.image_alt = title
                category.save()
            return category

        computers = make_category('Компьютеры и ноутбуки', icon='laptop')
        laptops = make_category('Ноутбуки', parent=computers, icon='laptop')
        components = make_category('Комплектующие', parent=computers, icon='motherboard')

        gadgets = make_category('Смартфоны и гаджеты', icon='smartphone')
        smartphones = make_category('Смартфоны', parent=gadgets, icon='smartphone')
        headphones = make_category('Наушники', parent=gadgets, icon='headphones')

        home_appliances = make_category('Бытовая техника', icon='multicooker')

        tag_names = ['Игровой', 'Новинка', 'Хит продаж', 'Для дома', 'Премиум']
        tags = {name: Tag.objects.get_or_create(name=name)[0] for name in tag_names}

        products_data = [
            dict(category=laptops, title='Ноутбук ProBook 15', price='54990.00', count=8,
                 description='Ноутбук для работы и учёбы.', free_delivery=True,
                 tag_list=['Новинка'], is_banner=True, icon='laptop'),
            dict(category=laptops, title='Игровой ноутбук StrikeForce 17', price='112990.00', count=3,
                 description='Мощный игровой ноутбук с дискретной видеокартой.', free_delivery=True,
                 tag_list=['Игровой', 'Премиум'], is_limited=True, icon='laptop'),
            dict(category=components, title='Видеокарта GeForce RTX 4070', price='68990.00', count=5,
                 description='Видеокарта для игр и работы с графикой.', tag_list=['Игровой'],
                 icon='graphics_card'),
            dict(category=components, title='SSD-накопитель 1TB NVMe', price='7990.00', count=25,
                 description='Быстрый твердотельный накопитель.', tag_list=['Хит продаж'], icon='ssd_stick'),
            dict(category=smartphones, title='Смартфон Vega X12', price='39990.00', count=15,
                 description='Смартфон с тройной камерой и быстрой зарядкой.', free_delivery=True,
                 tag_list=['Новинка'], is_banner=True, icon='smartphone'),
            dict(category=smartphones, title='Смартфон Vega Lite', price='19990.00', count=20,
                 description='Бюджетный смартфон с хорошей автономностью.', tag_list=['Хит продаж'],
                 icon='smartphone'),
            dict(category=headphones, title='Беспроводные наушники SoundPods', price='6990.00', count=40,
                 description='Полностью беспроводные наушники с шумоподавлением.', free_delivery=True,
                 tag_list=['Хит продаж'], is_banner=True, icon='earbuds'),
            dict(category=headphones, title='Наушники StudioMax (лимитированная серия)', price='24990.00', count=4,
                 description='Полноразмерные наушники, лимитированная серия.',
                 tag_list=['Премиум'], is_limited=True, icon='headphones'),
            dict(category=home_appliances, title='Робот-пылесос CleanBot 5', price='23990.00', count=6,
                 description='Робот-пылесос с влажной уборкой.', free_delivery=True,
                 tag_list=['Для дома'], icon='robot_vacuum'),
            dict(category=home_appliances, title='Мультиварка ChefHome 6L', price='8990.00', count=12,
                 description='Мультиварка на 6 литров, 15 программ.', tag_list=['Для дома'], icon='multicooker'),
            dict(category=home_appliances, title='Кофемашина EspressoPro', price='34990.00', count=3,
                 description='Автоматическая кофемашина для дома и офиса.',
                 tag_list=['Премиум'], is_limited=True, icon='coffee_machine'),
            dict(category=components, title='Материнская плата TechBoard Z790', price='24990.00', count=7,
                 description='Материнская плата для современных процессоров.', tag_list=['Игровой'],
                 icon='motherboard'),
        ]

        products = []
        for data in products_data:
            tag_list = data.pop('tag_list')
            is_limited = data.pop('is_limited', False)
            is_banner = data.pop('is_banner', False)
            icon = data.pop('icon')
            product, _ = Product.objects.get_or_create(
                title=data['title'],
                defaults=dict(
                    category=data['category'],
                    price=decimal.Decimal(data['price']),
                    count=data['count'],
                    description=data['description'],
                    full_description=data['description'] + ' Подробное описание уточняется у продавца.',
                    free_delivery=data.get('free_delivery', False),
                    is_limited=is_limited,
                    is_banner=is_banner,
                ),
            )
            product.tags.set([tags[name] for name in tag_list])
            Specification.objects.get_or_create(product=product, name='Гарантия', defaults={'value': '12 месяцев'})
            Specification.objects.get_or_create(
                product=product, name='Страна производства', defaults={'value': 'Китай'}
            )
            # своих фотографий товаров нет — карточки на фронтенде безусловно
            # обращаются к images[0].src, без картинки страница просто падает
            if not product.images.exists():
                product_image = ProductImage(product=product, alt=product.title)
                product_image.image.save(f'{icon}.png', generate_product_image(icon), save=True)
            products.append(product)

        for product in (products[1], products[6], products[10]):
            Sale.objects.get_or_create(
                product=product,
                defaults=dict(
                    sale_price=(decimal.Decimal(product.price) * decimal.Decimal('0.85'))
                    .quantize(decimal.Decimal('0.01')),
                    date_from=today - datetime.timedelta(days=3),
                    date_to=today + datetime.timedelta(days=10),
                ),
            )

        Review.objects.get_or_create(
            product=products[0], user=buyer1,
            defaults=dict(author='Иван Иванов', email='ivanov@example.com',
                          text='Отличный ноутбук, всё устраивает.', rate=5),
        )
        Review.objects.get_or_create(
            product=products[0], user=buyer2,
            defaults=dict(author='Мария Петрова', email='petrova@example.com',
                          text='Хорошее соотношение цены и качества.', rate=4),
        )
        Review.objects.get_or_create(
            product=products[4], user=buyer1,
            defaults=dict(author='Иван Иванов', email='ivanov@example.com',
                          text='Камера снимает хорошо, батарея держит день.', rate=5),
        )

        ShopSettings.load()

        order, created = Order.objects.get_or_create(
            user=buyer1,
            full_name='Иван Иванов',
            defaults=dict(
                email='ivanov@example.com',
                phone='+7 900 111-22-33',
                delivery_type=Order.DeliveryType.STANDARD,
                payment_type=Order.PaymentType.ONLINE,
                total_cost=decimal.Decimal(products[0].price) + decimal.Decimal(products[3].price),
                status=Order.Status.PAID,
                city='Москва',
                address='ул. Примерная, д. 1',
            ),
        )
        if created:
            OrderItem.objects.create(order=order, product=products[0], title=products[0].title,
                                      price=products[0].price, quantity=1)
            OrderItem.objects.create(order=order, product=products[3], title=products[3].title,
                                      price=products[3].price, quantity=1)
            Payment.objects.create(order=order, card_last4='4242', status=Payment.Status.SUCCESS,
                                    processed_at=timezone.now())

        self.stdout.write(self.style.SUCCESS('Демоданные готовы.'))
