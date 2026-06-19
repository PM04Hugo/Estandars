from django.urls import path, include
from estandar import views

urlpatterns = [
    path('',views.base, name='base'), #Por la misma razón listalibros será la inicio"
    path('formulario',views.formulario, name='formulario'), #Por la misma razón listalibros será la inicio
    path('form/',views.form, name='form'),
    #path('administrador/',views.administrador, name='administrador'),
    path('excel/<int:pk>/',views.excel, name='excel'),
    #path('administrador/unir/',views.unir, name='unir'),
    path('administrador/', include('estandar.ulsa')),
    path('documento/', views.documento, name='documento'),
    path('abrir/', views.abrir, name='abrir'),
    path('confirmar_transformaciones/', views.confirmar_transformaciones, name='confirmar_transformaciones'),
    path('proyecto/<int:pk>/confirmar_fila/', views.confirmar_fila, name='confirmar_fila'),
    path('regla_escoger', views.regla_escoger, name='regla_escoger'),
    path('regla_listar/', views.regla_listar, name='regla_listar'),
    path('regla/<int:pk>/borrar/', views.regla_borrar, name='regla_borrar'),
    path('proyecto_escoger', views.proyecto_escoger, name='proyecto_escoger'),
    path('proyecto_listar/', views.proyecto_listar, name='proyecto_listar'),
    path('proyecto_borrar/<int:pk>/', views.proyecto_borrar, name='proyecto_borrar'),
    ]