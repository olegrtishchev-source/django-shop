from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product
from catalog.serializers import ProductShortSerializer
from orders.serializers import BasketItemInputSerializer


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
      текстовому примечанию в swagger.yaml): computed `basketCount` во
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
        # тихо чистим сессию от таких «осиротевших» позиций кий
        if len(products) != len(basket):
            self._save_basket(request, {pid: qty for pid, qty in basket.items() if pid in products})

        return items
