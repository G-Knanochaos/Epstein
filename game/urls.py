from django.urls import path
from . import views

urlpatterns = [
    path('', views.game, name='game'),
    path('check/', views.check_guess, name='check_guess'),
]
