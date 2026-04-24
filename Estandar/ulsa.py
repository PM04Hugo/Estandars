from django.urls import path, include
from estandar import views

urlpatterns = [
    path('',views.administrador , name='administrador'), #Por la misma razón listalibros será la inicio"
    #path('administrador/',views.administrador, name='administrador'),
    path('unir/',views.unir, name='unir'),
    ]