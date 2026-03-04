from datetime import date
from django.shortcuts import render, get_object_or_404
from .models import Camion, EstadoCamion, Mantencion, DocumentacionGeneral, Remolque, AsignacionTractoRemolque
from django.http import JsonResponse
from django.db.models import Max, Prefetch
from .utils import evaluar_salud_entidad
from itertools import groupby
from operator import attrgetter
from django.contrib.auth.decorators import login_required



@login_required
def camion_list(request):
    # 1. Prefetch para TRACTO: Excluimos DIARIAS y ordenamos (2026 arriba)
    prefetch_mants_camion = Prefetch(
        'mantenciones', 
        queryset=Mantencion.objects.exclude(tipo_mantencion='DIARIA').order_by('-fecha_mantencion').prefetch_related('documentos'),
        to_attr='mantenciones_reales'
    )

    # 2. Prefetch para REMOLQUE: Lo mismo
    prefetch_mants_remolque = Prefetch(
    'asignaciontractoremolque_set__remolque__mantenciones_remolque',
    queryset=Mantencion.objects.exclude(tipo_mantencion='DIARIA').order_by('-fecha_mantencion').prefetch_related('documentos'),
    to_attr='mants_reales_rem'
    )

    # 3. Queryset Maestro
    queryset = Camion.objects.filter(activo=True).select_related(
        "estado_actual"
    ).prefetch_related(
        prefetch_mants_camion,
        prefetch_mants_remolque,
        "asignaciontractoremolque_set__remolque__estado_actual"
    )

    camiones_data = []
    for c in queryset:
        # Ahora c.mantenciones_reales[0] será SÍ O SÍ la del 10/01/26
        c.ultima_m = c.mantenciones_reales[0] if c.mantenciones_reales else None
        c.docs_drive = []
        if c.mantenciones_reales:
            for m in c.mantenciones_reales:
                for d in m.documentos.all():
                    if d.ruta_archivo and 'http' in d.ruta_archivo:
                        c.docs_drive.append(d)

        c.salud_calculada = evaluar_salud_entidad(c)    
        
        # Lógica de Remolque
        asignacion = c.asignaciontractoremolque_set.filter(activo=True).first()
        if asignacion and asignacion.remolque:
            rem = asignacion.remolque
            m_rem = getattr(rem, 'mants_reales_rem', [])
            rem.ultima_m = m_rem[0] if m_rem else None
            rem.docs_drive = []
            for mr in m_rem:
                for dr in mr.documentos.all():
                    if dr.ruta_archivo and 'http' in dr.ruta_archivo:
                        rem.docs_drive.append(dr)
            rem.salud_calculada = evaluar_salud_entidad(rem)
            c.remolque_vinculado = rem
        
        camiones_data.append(c)
        
    # 2. FILTROS
    estado_filtro = request.GET.get("estado")
    if estado_filtro:
        camiones_data = [c for c in camiones_data if c.salud_calculada["codigo"] == estado_filtro]

    # 3. ORDENAMIENTO (Crucial para que groupby no falle)
    ordenar = request.GET.get("orden")
    
    def obtener_llave_orden(c):
        # Si no tiene estado_actual o base, usamos un string vacío para que no tire error
        base_id = c.estado_actual.base_actual if (c.estado_actual and c.estado_actual.base_actual) else "ZZZ"
        prioridad = c.salud_calculada.get("prioridad", 3)
        
        if ordenar == "urgencia":
            return (prioridad, base_id)
        return (base_id, prioridad)

    camiones_data.sort(key=obtener_llave_orden)

    # 4. AGRUPAMIENTO (Aquí estaba el error)
    camiones_por_base = []
    # Usamos la misma lógica de la llave de ordenamiento para agrupar
    for base_code, grupo in groupby(camiones_data, key=lambda c: c.estado_actual.base_actual if (c.estado_actual and c.estado_actual.base_actual) else "SIN_BASE"):
        lista_grupo = list(grupo)
        
        # Buscamos el nombre bonito de la base
        if base_code != "SIN_BASE":
            base_display = lista_grupo[0].estado_actual.get_base_actual_display()
        else:
            base_display = "Unidades sin Base Asignada"

        camiones_por_base.append({
            "base": base_display,
            "camiones": lista_grupo
        })

    context = {
        "camiones_por_base": camiones_por_base,
        "estado_seleccionado": estado_filtro,
        "orden": ordenar,
    }
    return render(request, "core/camion_list.html", context)

@login_required
def camion_detail(request, pk):
    # 1. Prefetch filtrado: Solo mantenciones reales para el historial técnico
    # Así el usuario ve reparaciones, no checklists infinitos
    prefetch_reales = Prefetch(
        'mantenciones', 
        queryset=Mantencion.objects.exclude(tipo_mantencion='DIARIA').order_by('-fecha_mantencion'),
        to_attr='historial_tecnico'
    )

    # 2. Obtenemos el camión
    camion = get_object_or_404(
        Camion.objects.select_related('estado_actual').prefetch_related(
            prefetch_reales, 
            'mantenciones__documentos', # Necesitamos los docs de todas para el historial
            'documentos_general'
        ), 
        id_camion=pk
    )
    
    # 3. Datos para el contexto
    # Usamos el atributo 'historial_tecnico' que creamos en el prefetch
    mantenciones = camion.historial_tecnico 
    documentos = camion.documentos_general.all()
    
    # 4. Remolque vinculado
    asignacion = camion.asignaciontractoremolque_set.filter(activo=True).first()
    remolque_vinculado = asignacion.remolque if asignacion else None

    # 5. Calculamos salud (evaluar_salud_entidad ya debería usar el filtro interno)
    salud = evaluar_salud_entidad(camion)

    context = {
        'camion': camion,
        'mantenciones': mantenciones,
        'documentos': documentos,
        'remolque_vinculado': remolque_vinculado,
        'estado_mant': salud 
    }
    return render(request, 'core/camion_detail.html', context)

@login_required
def remolque_detail(request, pk):
    # 1. Obtenemos el remolque optimizado
    # Traemos de un golpe documentos y mantenciones para que la salud no dispare más queries
    remolque = get_object_or_404(
        Remolque.objects.prefetch_related(
            'mantenciones_remolque', 
            'documentos_general'
        ), 
        id_remolque=pk
    )
    
    # 2. Datos para las tablas del template
    mantenciones = remolque.mantenciones_remolque.all().order_by('-fecha_mantencion')
    documentos = remolque.documentos_general.all().order_by('fecha_vencimiento')
    
    # 3. Camión vinculado (usando la relación inversa de tu modelo)
    # AsignacionTractoRemolque tiene un ForeignKey a Remolque con related_name por defecto o el que definiste
    asignacion = remolque.asignaciontractoremolque_set.filter(activo=True).first()
    camion_vinculado = asignacion.camion if asignacion else None

    # 4. LA MAGIA: Usamos la "Única Verdad"
    # Esta función detectará que es un Remolque y aplicará sus reglas específicas
    salud = evaluar_salud_entidad(remolque)

    context = {
        'remolque': remolque,
        'mantenciones': mantenciones,
        'documentos': documentos,
        'camion_vinculado': camion_vinculado,
        'estado_mant': salud  # Contiene: codigo, label, css, prioridad y motivos
    }
    return render(request, 'core/remolque_detail.html', context)

def api_camion_detalle(request, camion_id):
    # Traemos con prefetch para los documentos
    camion = get_object_or_404(
        Camion.objects.prefetch_related('mantenciones__documentos'), 
        id_camion=camion_id
    )

    estado = camion.estado_actual.estado_operativo if hasattr(camion, 'estado_actual') else None
    kilometraje = camion.estado_actual.kilometraje if hasattr(camion, 'estado_actual') else None

    # Buscamos la última real para la fecha
    m_reales = camion.mantenciones.exclude(tipo_mantencion='DIARIA').order_by('-fecha_mantencion')
    u_m = m_reales.first()
    
    docs_drive = []
    for m in m_reales:
        for d in m.documentos.all():
            if d.ruta_archivo and 'http' in d.ruta_archivo:
                docs_drive.append({
                    "nombre": d.nombre_archivo or "Documento",
                    "ruta": d.ruta_archivo
                })

    return JsonResponse({
        "id_camion": camion.id_camion,
        "patente": camion.patente,
        "estado_operativo": estado,
        "kilometraje_actual": kilometraje,
        "km_restantes": camion.km_restantes(),
        "ultima_mantencion_real": u_m.fecha_mantencion.strftime('%d/%m/%Y') if u_m else "Sin datos",
        "documentos_drive": docs_drive,
    })

def api_estado_camiones(request):
    """
    API Corregida: Filtra DIARIAS y ordena por fecha descendente.
    """
    resultado = []
    
    camiones = Camion.objects.filter(activo=True).select_related(
        "estado_actual"
    ).prefetch_related(
        "mantenciones__documentos",
        "asignaciontractoremolque_set__remolque__mantenciones_remolque__documentos"
    )

    for camion in camiones:
        salud_tracto = evaluar_salud_entidad(camion)
        
        # --- B. DOCUMENTOS Y FECHA TRACTO (FILTRADO Y ORDENADO) ---
        docs_tracto = []
        # Excluimos las diarias y ponemos la más reciente (2026) arriba
        m_reales = camion.mantenciones.exclude(tipo_mantencion='DIARIA').order_by('-fecha_mantencion')
        
        u_m_t = m_reales.first()
        fecha_um_t = u_m_t.fecha_mantencion.strftime('%d/%m/%y') if u_m_t and u_m_t.fecha_mantencion else ""
        
        for m in m_reales:
            for d in m.documentos.all():
                if d.ruta_archivo and 'http' in d.ruta_archivo:
                    docs_tracto.append({
                        "nombre": d.nombre_archivo or "Ver Mantención",
                        "ruta": d.ruta_archivo
                    })

        # --- C. DATOS DEL REMOLQUE (FILTRADO Y ORDENADO) ---
        motivos_remolque = []
        docs_remolque = []
        fecha_um_r = ""
        id_remolque = None
        estado_rem_css = "estado-ok"
        
        asignacion = camion.asignacion_actual 
        if asignacion:
            rem = asignacion.remolque
            id_remolque = rem.id_remolque
            salud_rem = evaluar_salud_entidad(rem)
            motivos_remolque = salud_rem["motivos"]
            estado_rem_css = salud_rem["css"]
            
            # Filtro igual para el remolque
            m_reales_rem = rem.mantenciones_remolque.exclude(tipo_mantencion='DIARIA').order_by('-fecha_mantencion')
            u_m_r = m_reales_rem.first()
            fecha_um_r = u_m_r.fecha_mantencion.strftime('%d/%m/%y') if u_m_r and u_m_r.fecha_mantencion else ""
            
            for mr in m_reales_rem:
                for dr in mr.documentos.all():
                    if dr.ruta_archivo and 'http' in dr.ruta_archivo:
                        docs_remolque.append({
                            "nombre": dr.nombre_archivo or "Ver Doc",
                            "ruta": dr.ruta_archivo
                        })

        resultado.append({
            "id_camion": camion.id_camion,
            "id_remolque": id_remolque,
            "estado": salud_tracto["codigo"],
            "css": salud_tracto["css"],
            "motivos": salud_tracto["motivos"],
            "documentos": docs_tracto,
            "fecha_um": fecha_um_t,
            "motivos_remolque": motivos_remolque,
            "documentos_remolque": docs_remolque,
            "fecha_um_remolque": fecha_um_r,
            "estado_remolque_css": estado_rem_css
        })

    return JsonResponse(resultado, safe=False)

def api_remolque_detalle(request, remolque_id):
    """
    Retorna los datos técnicos y de salud de un remolque para modales o detalles rápidos.
    """
    # 1. Traemos el remolque optimizado
    rem = get_object_or_404(
        Remolque.objects.prefetch_related('mantenciones_remolque', 'documentos_general'), 
        id_remolque=remolque_id
    )
    
    # 2. Obtenemos el veredicto de salud centralizado
    salud = evaluar_salud_entidad(rem)
    
    # 3. Datos técnicos específicos
    ultima_m = rem.mantenciones_remolque.all().first() # Ya viene ordenado si usas el prefetch de la view anterior
    km_proxima = ultima_m.km_proxima_mantencion if ultima_m else 0
    km_actual = float(rem.kilometraje_acumulado)
    
    # Calculamos km_restantes de forma consistente
    km_restantes = km_proxima - km_actual if km_proxima > 0 else 0

    # 4. Construimos la respuesta unificada
    return JsonResponse({
        "id_remolque": rem.id_remolque,
        "patente": rem.patente,
        "estado_operativo": rem.get_estado_operativo_display(),
        "kilometraje_acumulado": km_actual,
        "km_restantes": km_restantes,
        "proxima_km": km_proxima,
        # Salud centralizada
        "estado_salud": salud["codigo"],
        "css_salud": salud["css"],
        "motivos": salud["motivos"],
        # Cantidad de alertas (filtrando de la lista de motivos de salud)
        "total_alertas": len(salud["motivos"]),
    })

def api_estado_salud_remolque(request, remolque_id):
    """
    Evalúa mantenciones y documentos usando la lógica centralizada
    para mantener consistencia en todo el sistema.
    """
    # 1. Traemos el remolque con sus documentos y mantenciones de una vez (Optimizado)
    rem = get_object_or_404(
        Remolque.objects.prefetch_related('documentos_general', 'mantenciones_remolque'), 
        id_remolque=remolque_id
    )

    # 2. Llamamos a la "Única Verdad" en utils.py
    # Pasamos el objeto y la lógica centralizada decide el color y los motivos
    salud = evaluar_salud_entidad(rem)

    # 3. Retornamos el JSON que el JavaScript ya conoce
    return JsonResponse({
        "estado": salud["codigo"],
        "css": salud["css"],
        "label": salud["label"],
        "motivos": salud["motivos"]
    })
