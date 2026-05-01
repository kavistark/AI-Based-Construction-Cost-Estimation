from django.urls import path
from . import views

urlpatterns = [
    path('home/',          views.home_view,     name='home'),
    path('style/',         views.image_style_view, name='image_style'),
    path('result/',   views.result_view,   name='result'),
    path('',    views.login_view,    name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/',   views.logout_view,   name='logout'),
    path('profile/',  views.profile_view,  name='profile'),
    # AJAX live estimate (no DB save)
    path('api/estimate/', views.ajax_estimate, name='ajax_estimate'),
]