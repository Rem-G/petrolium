from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('map/', views.map, name='map'),
    path('station/', views.station, name='station'),
    #path('update/', views.force_update, name='update'),
    #path('forcestations/', views.force_json_stations)
]