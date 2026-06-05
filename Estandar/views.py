from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Medidas, Regla,  MedidasUnidades, Proyecto, Unidades, Estandar
from django.contrib.auth.models import User, Group
from django.contrib.messages import get_messages
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import io
from groq import Groq
import csv, io
from django.conf import settings


@login_required
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
        if request.user.groups.filter(name='admins').exists():
            return redirect('administrador')
        return redirect('base')

    medidas = Medidas.objects.all()
    relaciones = MedidasUnidades.objects.select_related('medida', 'unidad').all()
    es_admin = request.user.groups.filter(name='admins').count() > 0
    print("Usuario actual:", request.user.username)
    print("Grupos reales en esta BD:", list(request.user.groups.values_list('name', flat=True)))

    return render(request, 'formulario.html', {
        'medidas': medidas,
        'relaciones': relaciones,
        'admin': es_admin,
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
            print("API KEY:", settings.GROQ_API_KEY)
            client = Groq(api_key=settings.GROQ_API_KEY) 
            nombre=request.POST.get('nombre')
            estandar_id=int(request.POST.get('estandar'))
            csv_file=request.FILES.get('fileInput')
            
            estandar  = Estandar.objects.prefetch_related('reglas').get(id=estandar_id)
            reglas_dict = {r.id: r for r in estandar.reglas.all()}
            reglas  = [reglas_dict[id] for id in estandar.orden if id in reglas_dict]

            #Sacamos todas las reglas
            reglas_info = "\n".join([
                f"{i+1}. {r.nombre}: medida={r.nombre_medida}, unidad={r.nombre_unidad}, min={r.minimo}, max={r.maximo}"
                for i, r in enumerate(reglas)
            ])

            contenido_csv  = csv_file.read().decode('utf-8')
            csv_file.seek(0)
            print("Orden de reglas:", [r.nombre for r in reglas])
            prompt = f"""
            Con el siguiente CSV

            {contenido_csv}

            Y el siguiente estándar con estas reglas en orden
            {reglas_info}

            Tienes que:
            1. Reordena las columnas del CSV para que coincidan con el orden de las reglas que te paso, deja siempre los pacientes en la primera columna
            2. Renombra las columnas que coincidan con alguna regla, si no coinciden dejalas despúes de las reglas en orden
            3. Transformar las unidades de cada columna para que coincidan con las unidades de las reglas, pasalas ya convertidas, no con formulas
            4. Devuelve ÚNICAMENTE el CSV resultante separado por ; sin explicaciones ni markdown
            """
            
            client   = Groq(api_key=settings.GROQ_API_KEY)
            respuesta = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}]
            )
            csv_transformado = respuesta.choices[0].message.content.strip()
            
            

            from django.core.files.base import ContentFile
            proyecto = Proyecto.objects.create(
                nombre=nombre,
                estandard=estandar.nombre,
            )
            proyecto.file.save(
                f"{nombre}.csv",
                ContentFile(csv_transformado.encode('utf-8'))
            
            )
            return redirect('excel', pk=proyecto.pk) 

    estandares = Estandar.objects.all()
    return render(request, 'hola.html' , {'estandares': estandares} )

def crear_estandar(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        reglas    = request.POST.getlist('reglas')
        estandar = Estandar.objects.create(
            nombre=nombre,
            orden=[int(id) for id in reglas]  
        )
        estandar.reglas.set(Regla.objects.filter(id__in=reglas))
        return redirect('administrador')

    return redirect('departamento')

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
                login(request, user)
                request.session['usuario_id'] = user.id
                return redirect('/estandar/administrador/')
            else:
                if id == departamento:
                    request.session['usuario_id'] = user.id
                    login(request, user)
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

@login_required
def excel(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk)
    UMBRAL_CUIDADO  = 1
    UMBRAL_URGENTE  = 3
    UMBRAL_PELIGRO  = 5
    
    df = pd.read_csv(proyecto.file.path, sep=';')

    estandar = Estandar.objects.prefetch_related('reglas').filter(nombre=proyecto.estandard).first()
    reglas = {}
    if estandar:
        reglas = {r.nombre_medida.strip().lower(): r for r in estandar.reglas.all()}
      
    #print("REGLAS KEYS:", list(reglas.keys()))
    #print("COLUMNAS CSV:", df.columns.tolist())
    #for col in df.columns:
     #   print(f"  '{col}' -> norm: '{col.strip().lower()}' -> en reglas: {col.strip().lower() in reglas}")      
            
    def nivel_fila(row):
        fuera = 0
        for col, valor in row.items():
            col_norm = col.strip().lower()
            # Busca qué regla corresponde a esta columna
            regla_match = next((r for key, r in reglas.items() if key in col_norm), None)
            if regla_match is None:
                continue
            try:
                v = float(valor)
            except (ValueError, TypeError):
                continue
            if v < regla_match.minimo or v > regla_match.maximo:
                fuera += 1
        if fuera >= UMBRAL_PELIGRO:  return 'peligro'
        if fuera >= UMBRAL_URGENTE:  return 'urgente'
        if fuera >= UMBRAL_CUIDADO:  return 'cuidado'
        return 'ok'
    
    niveles = df.apply(nivel_fila, axis=1).tolist()
    
    context = {
        'proyecto':  proyecto,
        'columns':   df.columns.tolist(),
        'rows_con_nivel':  list(zip(df.values.tolist(), niveles)),
        'niveles':   niveles,
        'umbral_cuidado': UMBRAL_CUIDADO,
        'umbral_urgente': UMBRAL_URGENTE,
        'umbral_peligro': UMBRAL_PELIGRO,
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

@login_required
def crear(request):
    return render(request, 'crear.html', {
        'reglas': Regla.objects.all()
    })

@login_required   
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

@login_required
def abrir(request):
    proyectos = Proyecto.objects.all()
    return render(request, 'abrir.html', {'proyectos': proyectos})



