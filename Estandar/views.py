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
from django.core.files.base import ContentFile
import io
from groq import Groq
import csv, io
from django.conf import settings
import unicodedata
import json


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
        client = Groq(api_key=settings.GROQ_API_KEY)
        nombre = request.POST.get('nombre')
        estandar_id = int(request.POST.get('estandar'))
        csv_file = request.FILES.get('fileInput')

        estandar = Estandar.objects.prefetch_related('reglas').get(id=estandar_id)
        reglas_dict = {r.id: r for r in estandar.reglas.all()}
        reglas = [reglas_dict[id] for id in estandar.orden if id in reglas_dict]

        reglas_info = "\n".join([
            f"{i+1}. {r.nombre}: medida={r.nombre_medida}, unidad={r.nombre_unidad}, min={r.minimo}, max={r.maximo}"
            for i, r in enumerate(reglas)
        ])

        contenido_csv = csv_file.read().decode('utf-8')
        csv_file.seek(0)
        df = pd.read_csv(io.StringIO(contenido_csv), sep=';')
        primera_col = df.iloc[:, 0]
        df_sin_primera = df.iloc[:, 1:]
        contenido_sin_pacientes = df_sin_primera.to_csv(index=False, sep=';')

        prompt_detectar = f"""
        El siguiente CSV tiene estas columnas:
        {', '.join(df_sin_primera.columns.tolist())}

        Y el estándar espera estas unidades:
        {reglas_info}

        Detecta qué columnas necesitan conversión de unidades.
        Devuelve ÚNICAMENTE este JSON sin markdown:
        [
        {{"columna": "Temperatura", "de": "°C", "a": "°F"}}
        ]
        Si no hay conversiones necesarias devuelve [].
        """
        import json
        respuesta = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_detectar}]
        )
        contenido = respuesta.choices[0].message.content.strip()
        contenido = contenido.split('```json')[-1].split('```')[0].strip() if '```' in contenido else contenido
        transformaciones = json.loads(contenido)

        if transformaciones:
            
            request.session['csv_pendiente'] = contenido_sin_pacientes
            request.session['primera_col'] = primera_col.tolist()
            request.session['transformaciones'] = transformaciones
            request.session['nombre'] = nombre
            request.session['estandar_id'] = estandar_id
            return redirect('confirmar_transformaciones')

        else:
           
            prompt_transformar = f"""
            Con el siguiente CSV:
            {contenido_sin_pacientes}

            Y el siguiente estándar:
            {reglas_info}

            Tienes que:
            1. Reordena las columnas para que coincidan con el orden de las reglas
            2. Renombra las columnas que coincidan con las reglas regla, en caso de que no coincida con una regla deja esa columna para el final
            4. Devuelve ÚNICAMENTE el CSV resultante separado por ; sin explicaciones ni markdown
            """
            respuesta2 = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt_transformar}]
            )
            csv_transformado = respuesta2.choices[0].message.content.strip()
            df_transformado = pd.read_csv(io.StringIO(csv_transformado), sep=';')
            df_final = pd.concat([primera_col.reset_index(drop=True), df_transformado.reset_index(drop=True)], axis=1)
            csv_final = df_final.to_csv(index=False, sep=';')

            proyecto = Proyecto.objects.create(nombre=nombre, estandard=estandar.nombre)
            proyecto.file.save(f"{nombre}.csv", ContentFile(csv_final.encode('utf-8')))
            return redirect('excel', pk=proyecto.pk)

    estandares = Estandar.objects.all()
    return render(request, 'hola.html', {'estandares': estandares})


@login_required
def confirmar_transformaciones(request):
    csv_pendiente = request.session.get('csv_pendiente')
    
    if csv_pendiente is None:
        # Redirige al inicio o muestra un error amigable
        messages.error(request, 'No hay ningún CSV pendiente de confirmación.')
        return redirect('base')
    transformaciones = request.session.get('transformaciones', [])

    if request.method == 'POST':
        aceptadas_idx = request.POST.getlist('aceptadas')
        aceptadas = [t for i, t in enumerate(transformaciones) if str(i) in aceptadas_idx]
        columnas_excluidas = [t['columna'] for t in transformaciones if t not in aceptadas]

        csv_pendiente = request.session['csv_pendiente']
        primera_col = pd.Series(request.session['primera_col'])
        nombre = request.session['nombre']
        estandar_id = request.session['estandar_id']
        estandar = Estandar.objects.prefetch_related('reglas').get(id=estandar_id)
        reglas_dict = {r.id: r for r in estandar.reglas.all()}
        reglas = [reglas_dict[id] for id in estandar.orden if id in reglas_dict]
        reglas_info = "\n".join([
            f"{i+1}. {r.nombre}: medida={r.nombre_medida}, unidad={r.nombre_unidad}"
            for i, r in enumerate(reglas)
        ])

        transformaciones_info = "\n".join([
            f"- '{t['columna']}': de {t['de']} a {t['a']}"
            for t in aceptadas
        ]) or "Ninguna"
        
        if aceptadas:
            # prompt a la IA solo si hay transformaciones aceptadas
            prompt_transformar = f"""
            Con el siguiente CSV:
            {csv_pendiente}

            Y el siguiente estándar:
            {reglas_info}

            Tienes que:
            1. Reordena las columnas para que coincidan con el orden de las reglas
            2. Renombra las columnas que coincidan con las reglas regla, en caso de que no coincida con una regla deja esa columna para el final
            3. Transforma ÚNICAMENTE estas columnas: {transformaciones_info}, nada de formulas, solo valores transformados
            4. El resto de columnas déjalas con sus valores originales
            5. Devuelve ÚNICAMENTE el CSV resultante separado por ; sin explicaciones ni markdown
            """
            client = Groq(api_key=settings.GROQ_API_KEY)
            respuesta = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt_transformar}]
            )
            csv_transformado = respuesta.choices[0].message.content.strip()
            df_transformado = pd.read_csv(io.StringIO(csv_transformado), sep=';')


            columnas_excluidas_reales = []
            for t in transformaciones:
                if t not in aceptadas:
                    col_match = next(
                        (col for col in df_transformado.columns 
                        if t['columna'].strip().lower() in col.strip().lower() 
                        or col.strip().lower() in t['columna'].strip().lower()),
                        None
                    )
                    if col_match:
                        columnas_excluidas_reales.append(col_match)

            df_final = pd.concat([primera_col.reset_index(drop=True), df_transformado.reset_index(drop=True)], axis=1)
            csv_final = df_final.to_csv(index=False, sep=';')

            proyecto = Proyecto.objects.create(
                nombre=nombre,
                estandard=estandar.nombre,
                columnas_excluidas=columnas_excluidas_reales,  
            )
            proyecto.file.save(
                f"{nombre}.csv", 
                ContentFile(csv_final.encode('utf-8'))
            )
            for key in ['csv_pendiente', 'primera_col', 'transformaciones', 'nombre', 'estandar_id']:
                del request.session[key]

            return redirect('excel', pk=proyecto.pk)
        
        else:
            
            prompt_transformar = f"""
            Con el siguiente CSV:
            {csv_pendiente}

            Y el siguiente estándar:
            {reglas_info}

            Tienes que:
            1. Reordena las columnas para que coincidan con el orden de las reglas
            2. Renombra las columnas que coincidan con las reglas regla, en caso de que no coincida con una regla deja esa columna para el final
            3. Devuelve ÚNICAMENTE el CSV resultante separado por ; sin explicaciones ni markdown
            """
            client = Groq(api_key=settings.GROQ_API_KEY)
            respuesta = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt_transformar}]
            )
            csv_transformado = respuesta.choices[0].message.content.strip()
            df_transformado = pd.read_csv(io.StringIO(csv_transformado), sep=';')
            df_final = pd.concat([primera_col.reset_index(drop=True), df_transformado.reset_index(drop=True)], axis=1)
            csv_final = df_final.to_csv(index=False, sep=';')

            proyecto = Proyecto.objects.create(
                nombre=nombre,
                estandard=estandar.nombre,
                columnas_excluidas=columnas_excluidas,
            )
            proyecto.file.save(f"{nombre}.csv", ContentFile(csv_final.encode('utf-8')))

            for key in ['csv_pendiente', 'primera_col', 'transformaciones', 'nombre', 'estandar_id']:
                del request.session[key]

            return redirect('excel', pk=proyecto.pk)
        
    return render(request, 'confirmar_transformaciones.html', {
        'transformaciones': list(enumerate(transformaciones)),
    })

def crear_estandar(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        reglas    = request.POST.getlist('reglas')
        
        #Los umbrales
        cuidado = int(request.POST.get('cuidado') or 1)
        urgente = int(request.POST.get('urgente') or 3)
        peligro = int(request.POST.get('peligro') or 5)
        estandar = Estandar.objects.create(
            nombre=nombre,
            orden=[int(id) for id in reglas],
            UMBRAL_CUIDADO=cuidado,
            UMBRAL_URGENTE=urgente,
            UMBRAL_PELIGRO=peligro
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
            if id == departamento or id ==4:
                request.session['usuario_id'] = user.id
                login(request, user)
                #request.session['departamento'] = user.departamento
                return redirect('/home/')
            else:
                messages.errorx(request, 'Departamento incorrecto')
        else:
            messages.error(request, 'Credenciales inválidas o departamento incorrecto')

    return render(request, 'login.html', {'departamento': departamento})

def logout_view(request):
    logout(request)
    return redirect('departamento')

@login_required
def excel(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk)
    
    
    df = pd.read_csv(proyecto.file.path, sep=';')

    def normalizar(texto):
        return unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8').strip().lower()

    estandar = Estandar.objects.prefetch_related('reglas').filter(nombre=proyecto.estandard).first()
    reglas = {}
    if estandar:
        reglas = {normalizar(r.nombre_medida): r for r in estandar.reglas.all()}
      
    UMBRAL_CUIDADO  = estandar.UMBRAL_CUIDADO 
    UMBRAL_URGENTE  = estandar.UMBRAL_URGENTE 
    UMBRAL_PELIGRO  = estandar.UMBRAL_PELIGRO 
    columnas_excluidas = proyecto.columnas_excluidas
    
    #print("REGLAS KEYS:", list(reglas.keys()))
    #print("COLUMNAS CSV:", df.columns.tolist())
    #for col in df.columns:
     #   print(f"  '{col}' -> norm: '{col.strip().lower()}' -> en reglas: {col.strip().lower() in reglas}")      
           
   
    def es_excluida(col):
        col_norm = normalizar(col)
        return any(normalizar(excl) in col_norm or col_norm in normalizar(excl)
                for excl in columnas_excluidas)
        
    print("REGLAS DICT:", list(reglas.keys()))

    def nivel_fila(row):
        fuera = 0
        cols_error = []
        for col, valor in row.items():
            if es_excluida(col):
                continue
            col_norm = normalizar(col.split('(')[0])
            regla_match = next(
                (r for key, r in reglas.items() 
                if normalizar(key.split('(')[0]) in col_norm       
                or col_norm in normalizar(key.split('(')[0])),      
                None
            )
            if regla_match is None:
                continue
            try:
                v = float(valor)
            except (ValueError, TypeError):
                continue
            if v < regla_match.minimo or v > regla_match.maximo:
                fuera += 1
                cols_error.append(col)
        if fuera == 0:
            return 'ok', []
        if fuera >= UMBRAL_PELIGRO:   nivel = 'peligro'
        elif fuera >= UMBRAL_URGENTE: nivel = 'urgente'
        elif fuera >= UMBRAL_CUIDADO: nivel = 'cuidado'
        else:                         nivel = 'ok'
        return nivel, cols_error

    resultados = df.apply(nivel_fila, axis=1).tolist()
    niveles = [r[0] for r in resultados]
    cols_error_por_fila = [r[1] for r in resultados]

    filas_confirmadas = set(proyecto.filas_confirmadas)

    rows_con_nivel = [] #Un poco bestia pra cosas tochas
    for i, (row_vals, nivel, cols_error) in enumerate(zip(df.values.tolist(), niveles, cols_error_por_fila)):
        if i in filas_confirmadas:
            nivel = 'ok'
            cols_error = []
        celdas = [{'valor': val, 'error': col in cols_error}
                for col, val in zip(df.columns.tolist(), row_vals)]
        rows_con_nivel.append((celdas, nivel))

    context = {
        'proyecto':       proyecto,
        'columns':        df.columns.tolist(),
        'rows_con_nivel': rows_con_nivel,
        'umbral_cuidado': UMBRAL_CUIDADO,
        'umbral_urgente': UMBRAL_URGENTE,
        'umbral_peligro': UMBRAL_PELIGRO,
    }
    return render(request, 'excel.html', context)

@login_required
@require_POST
def confirmar_fila(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk)
    data = json.loads(request.body)
    index = data.get('index')
    if index is not None and index not in proyecto.filas_confirmadas:
        proyecto.filas_confirmadas.append(index)
        proyecto.save()
    return JsonResponse({'ok': True})

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
    return render(request, 'verificar.html', {'reglas': reglas, 'cuidado': request.POST.get('cuidado', 1),'urgente': request.POST.get('urgente', 3),'peligro': request.POST.get('peligro', 5),})

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

@login_required
def regla_escoger(request):
    reglas = Regla.objects.all()
    return render(request, 'regla_escoger.html', {'reglas': reglas})

@login_required
def estandar_escoger(request):
    if request.user.groups.filter(name='admins').exists():
        estandares = Estandar.objects.all()
        return render(request, 'estandar_escoger.html', {'estandares': estandares})
    else:
        messages.error(request, 'Acceso denegado: No eres un administrador')
        return redirect('base')
    
@login_required
def estandar_listar(request):
    if request.user.groups.filter(name='admins').exists():
        estandares = Estandar.objects.all()
        return render(request, 'estandar_listar.html', {'estandares': estandares})
    else:
        messages.error(request, 'Acceso denegado: No eres un administrador')
        return redirect('base')

@login_required
def regla_listar(request):
    reglas = Regla.objects.all()
    return render(request, 'regla_listar.html', {'reglas': reglas})

@login_required
def estandar_borrar(request, pk):
    if not request.user.groups.filter(name='admins').exists():
        messages.error(request, 'Acceso denegado: No eres un administrador')
        return redirect('base')
    
    estandar = get_object_or_404(Estandar, pk=pk)
    if request.method == 'POST':
        estandar.delete()
        messages.success(request, f'Estándar "{estandar.nombre}" eliminado.')
    return redirect('estandar_listar')

@login_required
def regla_borrar(request, pk):
    if not request.user.groups.filter(name='admins').exists():
        messages.error(request, 'Acceso denegado: No eres un administrador')
        return redirect('base')

    regla = get_object_or_404(Regla, pk=pk)
    if request.method == 'POST':
        regla.delete()
        messages.success(request, f'Regla "{regla.nombre}" eliminada.')
    return redirect('regla_listar')

@login_required
def proyecto_escoger(request):
    return render(request, 'proyecto_escoger.html')

@login_required
def proyecto_listar(request):
    proyectos = Proyecto.objects.all()
    return render(request, 'proyecto_listar.html', {'proyectos': proyectos})

@login_required
def proyecto_borrar(request, pk):
    if not request.user.groups.filter(name='admins').exists():
        messages.error(request, 'Acceso denegado: No eres un administrador')
        return redirect('base')

    proyecto = get_object_or_404(Proyecto, pk=pk)
    if request.method == 'POST':
        if proyecto.file:
            proyecto.file.delete(save=False)
        proyecto.delete()
        messages.success(request, f'Proyecto "{proyecto.nombre}" eliminado.')
    return redirect('proyecto_listar')

def home(request):
    context = {
        'total_estandares': Estandar.objects.count(),
        'total_reglas': Regla.objects.count(),
        'total_proyectos': Proyecto.objects.count(),
        'total_medidas': Medidas.objects.count(),
        'estandares': Estandar.objects.all(),
    }
    return render(request, 'home.html', context)
