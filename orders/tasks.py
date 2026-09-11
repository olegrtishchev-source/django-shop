import random

from celery import shared_task
from django.utils import timezone

# ТЗ (стр. 5-6): "если введённый номер чётный и не заканчивается на ноль, то
# оплата подтверждается; если введённый номер нечётный или заканчивается на
# ноль, то сервис генерирует случайную ошибку оплаты". PaymentInputSerializer
# уже отсеивает нечётные номера синхронно при отправке формы (до постановки
# в очередь) — так что на практике здесь остаётся актуальна только проверка
# "заканчивается на 0", но логика написана буквально по ТЗ целиком, а не
# упрощена под то, что фактически достижимо.
_RANDOM_ERRORS = [
    'Банк отклонил операцию',
    'Недостаточно средств на счёте',
    'Платёжная система временно недоступна',
    'Превышен лимит операций по карте',
]


@shared_task
def process_payment(order_id, number):
    # Импорт моделей — внутри таска, а не на уровне модуля: celery.py
    # импортирует orders.tasks при старте воркера до полной инициализации
    # Django-приложений, ранний импорт моделей на этом этапе падает
    from orders.models import Order, Payment

    try:
        order = Order.objects.select_related('payment').get(pk=order_id)
    except Order.DoesNotExist:
        return

    is_success = int(number) % 2 == 0 and not number.endswith('0')

    payment = order.payment
    payment.processed_at = timezone.now()
    if is_success:
        payment.status = Payment.Status.SUCCESS
        payment.error_message = ''
        order.status = Order.Status.PAID
    else:
        payment.status = Payment.Status.FAILED
        payment.error_message = random.choice(_RANDOM_ERRORS)
        order.status = Order.Status.NOT_PAID
    payment.save(update_fields=['status', 'error_message', 'processed_at'])
    order.save(update_fields=['status'])
