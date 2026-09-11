from django.urls import path

from orders import views

urlpatterns = [
    path('basket', views.BasketView.as_view()),
    # /api/orders (список + создание) и /api/order/{id} (получение +
    # подтверждение) — два разных префикса, ровно как их использует реальный
    # JS пакета (cart.js/historyOrder.js бьют в .../orders, order-detail.js —
    # в .../order/<id>), не опечатка
    path('orders', views.OrderListCreateView.as_view()),
    path('order/<int:order_id>', views.OrderDetailView.as_view()),
    path('order/<int:order_id>/register', views.OrderCheckoutRegisterView.as_view()),
    path('payment/<int:order_id>', views.PaymentView.as_view()),
]
