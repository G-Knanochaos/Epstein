from django.urls import path
from . import views

urlpatterns = [
    path('sw.js', views.service_worker, name='service_worker'),
    path('', views.landing, name='landing'),
    path('play/', views.game, name='game'),
    path('info/', views.info, name='info'),
    path('privacy/', views.privacy, name='privacy'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('disclaimer/', views.disclaimer, name='disclaimer'),
    path('check/', views.check_guess, name='check_guess'),
]
