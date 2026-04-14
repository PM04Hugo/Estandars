from django.urls import path
from estandar import views

urlpatterns = [
    path('',views.base, name='base'), #Por la misma razón listalibros será la inicio"
    path('formulario',views.formulario, name='formulario'), #Por la misma razón listalibros será la inicio
    path('form/',views.form, name='form'),
    path('administrador/',views.administrador, name='administrador'),
    path('excel.html',views.excel, name='excel'),
    #path('',views.lista_libros,name='libros'), #Por la misma razón listalibros será la inicio
    #No entiendo porque no hacerlo to en config/urls.py al poner 't'odo se quita el comentario
    #path('libros/<int:id>',views.detalle_libro,name='detalle_libro'),
    #path('crear/', views.crearLibro, name='crearLibro'),
    #path('login/', views.login_view, name='login'),
    #path('logout/', views.logout_view, name='logout'), #Modificar esto es lo de casa_libro
    ]