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
    ]