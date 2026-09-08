from django.urls import path

from catalog import views

urlpatterns = [
    path('tags', views.TagListView.as_view()),
]
