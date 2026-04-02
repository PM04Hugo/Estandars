from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
import json
from .models import Medidas


def formulario(request):
    medidas = Medidas.objects.prefetch_related('unidades').all()
    return render(request, 'formulario.html', {'medidas': medidas})
def form(request):
    return render(request, 'form.html')
def base(request):
    return render(request, 'hola.html')

# Create your views here.
