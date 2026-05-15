from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Medidas, Regla,  MedidasUnidades, Proyecto, Unidades
from django.contrib.auth.models import User, Group
from django.contrib.messages import get_messages
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import io


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

@login_required
def administrador(request):
    if User.objects.filter(id=request.session.get('usuario_id'), groups__name='admins').exists(): 
        return render(request, 'administrador.html')
    else:
        messages.error(request, 'Acceso denegado: No eres un administrador')
        return redirect('login/1')

@login_required
def base(request):
    return render(request, 'bases.html')

@login_required
def documento(request):
    if request.method == 'POST':
        proyecto=Proyecto.objects.create(
            nombre=request.POST.get('nombre'),
            estandard=request.POST.get('estandar'),
            file=request.FILES.get('fileInput')
        )
        return redirect('excel', pk=proyecto.pk) 

    return render(request, 'hola.html')



@login_required
def unir(request):
    if User.objects.filter(id=request.session.get('usuario_id'), groups__name='admins').exists(): 
        if request.method == 'POST':
            maximo=float(request.POST.get('maximo'))
            minimo=float(request.POST.get('minimo'))
            
            
            
            crear_medida = request.POST.get('crearMedida') == 'on'
            crear_unidad = request.POST.get('crearUnidad') == 'on'
            nombre_medida = request.POST.get('medida')
            nombre_unidad = request.POST.get('unidades')
    
            if crear_medida:
                medida, _ = Medidas.objects.get_or_create(nombre=nombre_medida)
            else:
                medida = Medidas.objects.get(nombre__iexact=request.POST.get('medida'))
            
            if crear_unidad:
                unidad, _ = Unidades.objects.get_or_create(nombre=nombre_unidad)
            else:
                unidad = Unidades.objects.get(nombre__iexact=request.POST.get('unidades'))
            
            if MedidasUnidades.objects.filter(medida=medida, unidad=unidad).exists():
                storage = get_messages(request)
                list(storage) 
                messages.error(request, f'La relación "{medida} - {unidad}" ya existe')
                return redirect('unir')
            
            elif maximo<=minimo :
                storage = get_messages(request)
                list(storage) 
                messages.error(request, f'El valor máximo debe ser mayor que el mínimo')
                return redirect('unir')

            if maximo<=20:
                step=0.1
            elif maximo<=200:
                step=1  
            else:
                step=10   
                
            MedidasUnidades.objects.create(
                medida=medida,
                unidad=unidad,
                maximo=maximo,
                minimo=minimo,
                step=step
                
            )
            return redirect('administrador') 
        medidas = Medidas.objects.all()
        relaciones = MedidasUnidades.objects.select_related('medida', 'unidad').all()
        unidades = Unidades.objects.all()

        return render(request, 'unir.html', {
            'medidas': medidas,
            'relaciones': relaciones,
            'unidades': unidades,
        })

    else:
        messages.error(request, 'Acceso denegado: No eres un administrador')
        return redirect('login/1')


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
                    messages.errorx(request, 'Departamento incorrecto')
        else:
            messages.error(request, 'Credenciales inválidas o departamento incorrecto')

    return render(request, 'login.html', {'departamento': departamento})

def logout_view(request):
    logout(request)
    return redirect('login')

def excel(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk)
    
    df = pd.read_csv(proyecto.file.path, sep=';')
    
    context = {
        'proyecto': proyecto,
        'columns': df.columns.tolist(),
        'rows': df.values.tolist(),
    }
    return render(request, 'excel.html', context)

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


@require_POST
def preview(request):
    csv_file = request.FILES.get('fileInput')
    estandar = request.POST.get('estandar')

    if not csv_file or not estandar:
        return JsonResponse({'error': 'Faltan datos.'}, status=400)

    try:
        df = pd.read_csv(io.BytesIO(csv_file.read()), sep=';')
        df = df.fillna('')  # ← sustituye NaN por string vacío directamente
        df = df.iloc[:20, :5]

        return JsonResponse({
            'columns': df.columns.tolist(),
            'rows':    df.head(20).values.tolist(),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def crear(request):
    return render(request, 'crear.html', {
        'reglas': Regla.objects.all()
    })
    
def verificar(request):
    ids = request.POST.getlist('reglas') 
    reglas = Regla.objects.filter(id__in=ids)
    return render(request, 'verificar.html', {'reglas': reglas})

@require_POST
def tabla_preview(request):
    ids = request.POST.getlist('reglas')
    reglas = Regla.objects.filter(id__in=ids)
    reglas_ordenadas = sorted(reglas, key=lambda r: ids.index(str(r.id)))

    columns = [r.nombre for r in reglas_ordenadas]
    df = pd.DataFrame(columns=columns, index=range(5))  # ← DataFrame vacío con 5 filas
    df = df.fillna('')

    return JsonResponse({
        'columns': df.columns.tolist(),
        'rows':    df.values.tolist(),
    })
