from django.urls import path, include
from estandar import views

urlpatterns = [
    path('',views.administrador , name='administrador'), #Por la misma razón listalibros será la inicio"
    #path('administrador/',views.administrador, name='administrador'),
    path('unir/',views.unir, name='unir'),
    path('crear/', views.crear, name='crear'),
    path('verificar/', views.verificar, name='verificar'),
    path('tabla_preview/', views.tabla_preview, name='tabla_preview'),
    path('crear_estandar/', views.crear_estandar, name='crear_estandar'),
    path('estandar_escoger/', views.estandar_escoger, name='estandar_escoger'),
    path('estandar_listar/', views.estandar_listar, name='estandar_listar'),
    path('estandar/<int:pk>/borrar/', views.estandar_borrar, name='estandar_borrar'),
    ]