import re

from rest_framework import serializers


def validate_phone_format(value):
    """Мягкая проверка телефона: пустое значение пропускаем (обязательность
    поля -- забота required/allow_blank конкретного сериализатора), а если
    что-то введено -- после удаления пробелов/скобок/тире должно остаться
    10 цифр (без кода страны) или 11 цифр, начинающихся на 7 или 8."""

    if not value:
        return
    digits = re.sub(r'\D', '', value)
    valid_11 = len(digits) == 11 and digits[0] in '78'
    valid_10 = len(digits) == 10
    if not (valid_11 or valid_10):
        raise serializers.ValidationError(
            'Некорректный формат телефона -- ожидается 10-11 цифр, например +7 900 000-00-00'
        )
