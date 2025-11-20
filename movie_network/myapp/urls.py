from django.urls import path
from . import views

app_name = 'myapp'

urlpatterns = [
    path("login/", views.login_view, name='login'),
    path("signup/", views.signUp_view, name="signup"),
    path('home/',views.home_view, name="home")
]