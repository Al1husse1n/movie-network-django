from django.urls import path
from . import views
from django.views.generic import RedirectView
app_name = 'myapp'

urlpatterns = [
    path("login/", views.login_view, name='login'),
    path("signup/", views.signUp_view, name="signup"),
    path('home/',views.home_view, name="home"),
    path('logout/',views.logout_view,name="logout"),
    path('<int:communityId>/get',views.get_community,name='getCommunity'),
    path('compose/',views.compose_post, name='compose'),
    path('', RedirectView.as_view(url='/home/', permanent=True)),
    path('profile/', views.profile_view, name='profile'),
    path('editprofile/', views.edit_profile, name="editProfile"),
    path('changeprofile/', views.change_profile, name='changeProfile'),
    path('description/', views.description, name='description')
]