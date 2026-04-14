from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
import json
from .models import Medidas, Regla,  MedidasUnidades, Proyecto
from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import make_password, check_password


def formulario(request):
    if request.method == 'POST':
        Regla.objects.create(
            nombre=request.POST.get('regla'),
            nombre_medida=request.POST.get('nombre'),
            nombre_unidad=request.POST.get('unidades'),
            descripcion=request.POST.get('descripcion'),
            minimo=float(request.POST.get('minimo')),
            maximo=float(request.POST.get('maximo')),
        )
        return redirect('base')

    medidas = Medidas.objects.all()
    relaciones = MedidasUnidades.objects.select_related('medida', 'unidad').all()

    return render(request, 'formulario.html', {
        'medidas': medidas,
        'relaciones': relaciones,
    })

def form(request): #Formulario solo podría x usuario no se como hacerlo aún
    return render(request, 'form.html')

def administrador(request):
    return render(request, 'administrador.html')

@login_required
def base(request):
    if request.method == 'POST':
        Proyecto.objects.create(
            nombre=request.POST.get('nombre'),
            estandard=request.POST.get('estandar'),
            file=request.FILES.get('fileInput')
        )
        return redirect('excel.html') 

    return render(request, 'hola.html')
    


def login_view(request, departamento):
    if request.method == 'POST':
        usuario = request.POST['usuario']
        password = request.POST['password']
        user = authenticate(username=usuario, password=password)
        if user is not None:
            id = user.groups.values_list('id', flat=True).first()
            if id==4:
                request.session['usuario_id'] = user.id
                return redirect('/estandar/administrador/')
            else:
                if id == departamento:
                    request.session['usuario_id'] = user.id
                    #request.session['departamento'] = user.departamento
                    return redirect('/estandar/')
                else:
                    messages.error(request, 'Departamento incorrecto')
        else:
            messages.error(request, 'Credenciales inválidas o departamento incorrecto')

    return render(request, 'login.html', {'departamento': departamento})

def logout_view(request):
    logout(request)
    return redirect('login')

def excel(request):
    return render(request, 'excel.html')

def departamento(request):
    return render(request, 'departamento.html')

def registro_view(request):
    if request.method == 'POST':
        usuario = request.POST['usuario']
        password = request.POST['password']
        departamento = int(request.POST['departamento'])
        
        if User.objects.filter(username=usuario).exists():
            messages.error(request, 'El nombre de usuario ya está en uso')
            return render(request, 'registro.html')
        

        user = User.objects.create_user(username=usuario, password=password)
        match departamento:
            case 1:
                my_group = Group.objects.get(name='Urgencias') 
                
            case 2:
                my_group = Group.objects.get(name='Diagnostico')
            case 3:
                my_group = Group.objects.get(name='General')
            case _:
                messages.error(request, 'Departamento no válido')
                return render(request, 'registro.html')
                
        my_group.user_set.add(user)
        user.save()
        return redirect('/login/' + str(departamento))
            
    return render(request, 'registro.html')
        
        #if not Usuario.objects.filter(usuario=usuario).exists():
         #   User.objects.create(
          #      usuario=usuario,
           #     password=make_password(password),  # ← hashea la contraseña
            #    departamento=departamento
            #)
           # messages.success(request, 'Usuario registrado exitosamente')
           # return redirect('login/' + str(departamento))
        #else:
         #   messages.error(request, 'El usuario ya existe')
    #return render(request, 'registro.html')

# Create your views here.
