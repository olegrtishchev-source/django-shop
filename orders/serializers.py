from rest_framework import serializers


class BasketItemInputSerializer(serializers.Serializer):
    """Тело POST/DELETE /api/basket — `{id, count}`, ровно то, что шлют
    addToBasket()/removeFromBasket() в app.js. В реальном JS `count` всегда
    положительное число (кнопки +/- шлют 1, кнопка «Купить» на детальной
    странице — выбранное на степпере количество, но не меньше 1) — по умолчанию
    тоже 1, как и в addToBasket(item, count = 1)."""

    id = serializers.IntegerField()
    count = serializers.IntegerField(min_value=1, default=1)
