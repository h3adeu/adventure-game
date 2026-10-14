from django.urls import path
from . import views

app_name = 'game'

urlpatterns = [
    path('', views.home, name='home'),
    path('game/start/', views.start_game, name='start_game'),
    path('game/action/', views.game_action, name='game_action'),
]