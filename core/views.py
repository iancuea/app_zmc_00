from datetime import date
from django.shortcuts import render, get_object_or_404
from .models import Camion, EstadoCamion, Mantencion, DocumentacionGeneral, Remolque, AsignacionTractoRemolque
from django.http import JsonResponse
from django.db.models import Max
from .utils import estado_mantencion, estado_documento, ESTADO_PRIORIDAD
from itertools import groupby
from operator import attrgetter


def camion_list(request):
    camiones = list(
        Camion.objects.select_related(
            "estado_actual",
            "estado_actual__conductor"
        )
    )

    # --- FILTRO POR ESTADO DE MANTENCIÓN ---
    estado = request.GET.get("estado")
    if estado:
        camiones = [
            c for c in camiones
            if c.estado_mantencion()["codigo"] == estado
        ]

    # --- ORDENAR POR URGENCIA ---
    ordenar = request.GET.get("orden")
    if ordenar == "urgencia":
        camiones.sort(key=lambda c: c.prioridad_mantencion())

    # --- ORDEN BASE (SIEMPRE, para agrupar bien) ---
    camiones.sort(
        key=lambda c: (
            c.estado_actual.base_actual if c.estado_actual else "ZZZ",
            c.prioridad_mantencion()
        )
    )

    # --- AGRUPAR POR BASE ---
    camiones_por_base = []
    for base, grupo in groupby(
        camiones,
        key=lambda c: (
            c.estado_actual.get_base_actual_display()
            if c.estado_actual
            else "SIN BASE"
        )
    ):
        camiones_por_base.append({
            "base": base,
            "camiones": list(grupo)
        })

    context = {
        "camiones_por_base": camiones_por_base,
        "estado_seleccionado": estado,
        "orden": ordenar,
    }

    return render(request, "core/camion_list.html", context)

def camion_detail(request, pk):
    # 1. Obtenemos el camión o lanzamos 404
    camion = get_object_or_404(Camion, id_camion=pk)
    
    # 2. Traemos las mantenciones ordenadas por fecha (usando related_name 'mantenciones')
    mantenciones = camion.mantenciones.all().order_by('-fecha_mantencion')
    
    # 3. Traemos la documentación vinculada (usando related_name 'documentos_general')
    # Esto evita usar id_referencia manualmente y es más seguro
    documentos = camion.documentos_general.all().order_by('fecha_vencimiento')
    
    # 4. Buscamos si tiene un remolque asignado actualmente
    asignacion = AsignacionTractoRemolque.objects.filter(camion=camion, activo=True).first()
    remolque_vinculado = asignacion.remolque if asignacion else None

    # 5. Lógica de Semáforo (Salud del Camión)
    prioridad_global = 1
    estado_final = "OK"
    motivos = []

    # --- Chequeo de Mantención (Kilometraje) ---
    ultima_m = mantenciones.first()
    km_actual = camion.estado_actual.kilometraje if hasattr(camion, 'estado_actual') else 0
    
    if ultima_m and ultima_m.km_proxima_mantencion:
        # Usamos tu función de negocio estado_mantencion
        est, motivo = estado_mantencion(km_actual, ultima_m.km_proxima_mantencion)
        if ESTADO_PRIORIDAD[est] > prioridad_global:
            estado_final = est
            prioridad_global = ESTADO_PRIORIDAD[est]
        if motivo:
            motivos.append(f"Mecánica: {motivo}")

    # --- Chequeo de Documentos (Fechas) ---
    for doc in documentos:
        # Usamos tu función estado_documento (la que ya maneja None para el Padrón)
        est_d, motivo_d = estado_documento(doc.fecha_vencimiento)
        
        if ESTADO_PRIORIDAD[est_d] > prioridad_global:
            estado_final = est_d
            prioridad_global = ESTADO_PRIORIDAD[est_d]
        
        if motivo_d:
            motivos.append(f"{doc.get_categoria_display()}: {motivo_d}")

    context = {
        'camion': camion,
        'mantenciones': mantenciones,
        'documentos': documentos,
        'remolque_vinculado': remolque_vinculado,
        'estado_mant': {
            'codigo': estado_final,
            'label': estado_final,
            'css': f"estado-{estado_final.lower()}",
            'motivos': motivos
        }
    }
    return render(request, 'core/camion_detail.html', context)

def remolque_detail(request, pk):
    remolque = get_object_or_404(Remolque, id_remolque=pk)
    mantenciones = remolque.mantenciones_remolque.all().order_by('-fecha_mantencion')
    asignacion = AsignacionTractoRemolque.objects.filter(remolque=remolque, activo=True).first()
    camion_vinculado = asignacion.camion if asignacion else None

    prioridad_global = 1
    estado_final = "OK"
    motivos = []

    # 🔧 Chequeo de última mantención
    ultima_m = mantenciones.first()
    if ultima_m and ultima_m.km_proxima_mantencion:
        km_actual = float(remolque.kilometraje_acumulado)
        est, motivo = estado_mantencion(km_actual, ultima_m.km_proxima_mantencion)
        if ESTADO_PRIORIDAD[est] > prioridad_global:
            estado_final = est
            prioridad_global = ESTADO_PRIORIDAD[est]
        if motivo: motivos.append(f"Mecánica: {motivo}")

    # 📄 Chequeo de documentos (CORREGIDO) ---
    # Obtenemos todos los documentos vinculados a este remolque
    documentos = remolque.documentos_general.all()
    for doc in documentos:
        est_d, motivo_d = estado_documento(doc.fecha_vencimiento)
        if ESTADO_PRIORIDAD[est_d] > prioridad_global:
            estado_final = est_d
            prioridad_global = ESTADO_PRIORIDAD[est_d]
        if motivo_d: motivos.append(f"{doc.get_categoria_display()}: {motivo_d}")

    context = {
        'remolque': remolque,
        'mantenciones': mantenciones,
        'documentos': documentos, # ¡Agregado para el HTML!
        'camion_vinculado': camion_vinculado,
        'estado_mant': {
            'codigo': estado_final,
            'label': estado_final,
            'css': f"estado-{estado_final.lower()}",
            'motivos': motivos
        }
    }
    return render(request, 'core/remolque_detail.html', context)

def api_camion_detalle(request, camion_id):
    camion = get_object_or_404(Camion, id_camion=camion_id)

    estado = None
    kilometraje = None

    if hasattr(camion, 'estado_actual'):
        estado = camion.estado_actual.estado_operativo
        kilometraje = camion.estado_actual.kilometraje

    km_restantes = camion.km_restantes()

    return JsonResponse({
        "id_camion": camion.id_camion,
        "patente": camion.patente,
        "estado_operativo": estado,
        "kilometraje_actual": kilometraje,
        "km_restantes": km_restantes,
    })

def api_estado_camiones(request):
    resultado = []
    camiones = Camion.objects.filter(activo=True).select_related("estado_actual")

    for camion in camiones:
        prioridad_global = ESTADO_PRIORIDAD["OK"]
        estado_global = "OK"
        motivos_tracto = []
        
        estado_actual = getattr(camion, "estado_actual", None)
        km_actual = estado_actual.kilometraje if estado_actual else 0

        # --- 🚜 Mantención Tracto ---
        ultima_m = camion.mantenciones.order_by("-fecha_mantencion").first()
        if ultima_m:
            est, motivo = estado_mantencion(km_actual, ultima_m.km_proxima_mantencion)
            if ESTADO_PRIORIDAD[est] > prioridad_global:
                estado_global = est
                prioridad_global = ESTADO_PRIORIDAD[est]
            if motivo: motivos_tracto.append(f"Tracto: {motivo}")

        # --- 📄 Documentos Tracto (CORREGIDO) ---
        # Usamos el related_name 'documentos_general'
        for doc in camion.documentos_general.all():
            est, motivo = estado_documento(doc.fecha_vencimiento)
            if ESTADO_PRIORIDAD[est] > prioridad_global:
                estado_global = est
                prioridad_global = ESTADO_PRIORIDAD[est]
            if motivo: motivos_tracto.append(f"Doc Tracto ({doc.get_categoria_display()}): {motivo}")

        # --- 🚛 DATOS REMOLQUE ASIGNADO ---
        motivos_remolque = []
        id_remolque = None
        estado_rem_css = "estado-ok"
        
        asignacion = camion.asignacion_actual 

        if asignacion:
            rem = asignacion.remolque
            id_remolque = rem.id_remolque
            
            # 🔧 Mantención Remolque
            ultima_m_r = rem.mantenciones_remolque.order_by("-fecha_mantencion").first()
            if ultima_m_r:
                est, motivo = estado_mantencion(float(rem.kilometraje_acumulado), ultima_m_r.km_proxima_mantencion)
                if ESTADO_PRIORIDAD[est] > 1:
                    estado_rem_css = f"estado-{est.lower()}"
                if motivo: motivos_remolque.append(f"Remolque: {motivo}")

            # 📄 Documentos Remolque (CORREGIDO) ---
            # Usamos el related_name del remolque
            for doc in rem.documentos_general.all():
                est, motivo = estado_documento(doc.fecha_vencimiento)
                if ESTADO_PRIORIDAD[est] > 1:
                    estado_rem_css = f"estado-{est.lower()}"
                if motivo: motivos_remolque.append(f"Doc Remolque ({doc.get_categoria_display()}): {motivo}")

        resultado.append({
            "id_camion": camion.id_camion,
            "id_remolque": id_remolque,
            "estado": estado_global,
            "motivos": motivos_tracto,
            "motivos_remolque": motivos_remolque,
            "estado_remolque_css": estado_rem_css
        })
    return JsonResponse(resultado, safe=False)

def api_remolque_detalle(request, remolque_id):
    rem = get_object_or_404(Remolque, id_remolque=remolque_id)
    
    # Buscamos la última mantención usando el related_name que definiste
    ultima_m = rem.mantenciones_remolque.order_by("-fecha_mantencion").first()
    km_proxima = ultima_m.km_proxima_mantencion if ultima_m else 0
    
    # Cálculo de km restantes
    km_actual = float(rem.kilometraje_acumulado)
    km_restantes = km_proxima - km_actual if km_proxima > 0 else 0

    docs_vencidos = rem.documentos_general.filter(fecha_vencimiento__lt=date.today()).count()

    return JsonResponse({
        "id_remolque": rem.id_remolque,
        "patente": rem.patente,
        "estado_operativo": rem.get_estado_operativo_display(),
        "kilometraje_acumulado": km_actual,
        "km_restantes": km_restantes,
        "proxima_km": km_proxima,
        "alertas_documentos": docs_vencidos,
    })

def api_estado_salud_remolque(request, remolque_id):
    """
    Evalúa mantenciones y documentos solo para un remolque específico.
    """
    rem = get_object_or_404(Remolque, id_remolque=remolque_id)
    prioridad_global = 1 # OK
    estado_final = "OK"
    motivos = []

    # 1. Chequeo de Mantención
    ultima_m = rem.mantenciones_remolque.order_by("-fecha_mantencion").first()
    if ultima_m:
        # Usamos tus funciones auxiliares estado_mantencion
        est, motivo = estado_mantencion(float(rem.kilometraje_acumulado), ultima_m.km_proxima_mantencion)
        if ESTADO_PRIORIDAD[est] > prioridad_global:
            estado_final = est
            prioridad_global = ESTADO_PRIORIDAD[est]
        if motivo: motivos.append(f"Mecánica: {motivo}")

    # 2. Chequeo de Documentos
    docs = rem.documentos_general.all()    
    
    for doc in docs:
        if doc.fecha_vencimiento is None:
            est = "OK"
            motivo = None
        else:
            # 2. Llamada a tu función de negocio corregida
            est, motivo = estado_documento(doc.fecha_vencimiento)

        # 3. Mapeo de Prioridades para el Semáforo Global
        # Ajustamos tus etiquetas a los niveles de prioridad (OK=1, PROXIMO=2, CRITICO/VENCIDO=3)
        prioridad_doc = 1
        if est == "VENCIDO" or est == "CRITICO":
            prioridad_doc = 3
            # Mapeamos a "CRITICO" para que el CSS pinte de rojo
            est_para_css = "CRITICO" 
        elif est == "PROXIMO":
            prioridad_doc = 2
            est_para_css = "WARNING"
        else:
            est_para_css = "OK"

        # 4. Actualización del estado global de la entidad (Camión/Remolque)
        if prioridad_doc > prioridad_global:
            estado_final = est_para_css
            prioridad_global = prioridad_doc

        # 5. Registro del motivo para mostrar en el tooltip o lista
        if motivo:
            motivos.append(f"{doc.get_categoria_display()}: {motivo}")

    return JsonResponse({
        "estado": estado_final,
        "css": f"estado-{estado_final.lower()}",
        "label": estado_final,
        "motivos": motivos
    })

