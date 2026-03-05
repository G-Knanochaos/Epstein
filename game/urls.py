from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('play/', views.game, name='game'),
    path('check/', views.check_guess, name='check_guess'),
]
