from django.urls import path

from orders import views

urlpatterns = [
    path('basket', views.BasketView.as_view()),
]
