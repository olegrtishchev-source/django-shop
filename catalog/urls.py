from django.urls import path

from catalog import views

urlpatterns = [
    path('tags', views.TagListView.as_view()),
    path('categories', views.CategoryListView.as_view()),
    path('catalog', views.CatalogView.as_view()),
    path('products/popular', views.PopularProductsView.as_view()),
    path('products/limited', views.LimitedProductsView.as_view()),
    path('banners', views.BannersView.as_view()),
    path('sales', views.SalesView.as_view()),
    path('product/<int:pk>', views.ProductDetailView.as_view()),
    path('product/<int:pk>/reviews', views.ProductReviewsView.as_view()),
    path('compare', views.CompareView.as_view()),
]
