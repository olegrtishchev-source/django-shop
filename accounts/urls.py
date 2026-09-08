from django.urls import path

from accounts import views

urlpatterns = [
    path('sign-in', views.SignInView.as_view()),
    path('sign-up', views.SignUpView.as_view()),
    path('sign-out', views.SignOutView.as_view()),
    path('profile', views.ProfileView.as_view()),
    path('profile/password', views.ProfilePasswordView.as_view()),
    path('profile/avatar', views.ProfileAvatarView.as_view()),
]
