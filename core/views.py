from django.shortcuts import render, get_object_or_404
from .models import Camion, EstadoCamion, Mantencion, DocumentacionGeneral
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

def camion_detail(request, id_camion):
    camion = get_object_or_404(Camion, id_camion=id_camion)

    estado = EstadoCamion.objects.filter(camion_id=id_camion).first()

    mantenciones = Mantencion.objects.filter(camion_id=id_camion).order_by('-fecha_mantencion')

    return render(request, 'core/camion_detail.html', {
        'camion': camion,
        'estado': estado,
        'mantenciones': mantenciones,
    })

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
    # Traemos los camiones activos
    camiones = Camion.objects.filter(activo=True).select_related("estado_actual")

    for camion in camiones:
        # --- 🚜 DATOS TRACTO (CAMIÓN) ---
        prioridad_global = ESTADO_PRIORIDAD["OK"]
        estado_global = "OK"
        motivos_tracto = []
        
        estado_actual = getattr(camion, "estado_actual", None)
        km_actual = estado_actual.kilometraje if estado_actual else 0

        # Mantención Tracto
        ultima_m = camion.mantenciones.order_by("-fecha_mantencion").first()
        if ultima_m:
            est, motivo = estado_mantencion(km_actual, ultima_m.km_proxima_mantencion)
            if ESTADO_PRIORIDAD[est] > prioridad_global:
                estado_global = est
                prioridad_global = ESTADO_PRIORIDAD[est]
            if motivo: motivos_tracto.append(f"Tracto: {motivo}")

        # Documentos Tracto
        docs_t = DocumentacionGeneral.objects.filter(tipo_entidad="CAMION", id_referencia=camion.id_camion)
        for doc in docs_t:
            est, motivo = estado_documento(doc.fecha_vencimiento)
            if ESTADO_PRIORIDAD[est] > prioridad_global:
                estado_global = est
                prioridad_global = ESTADO_PRIORIDAD[est]
            if motivo: motivos_tracto.append(f"Doc Tracto ({doc.get_categoria_display()}): {motivo}")

        # --- 🚛 DATOS REMOLQUE ASIGNADO ---
        motivos_remolque = []
        id_remolque = None
        estado_rem_css = "estado-ok" # Clase CSS para el remolque
        
        asignacion = camion.asignacion_actual 

        if asignacion:
            rem = asignacion.remolque
            id_remolque = rem.id_remolque
            
            # 🔧 Mantención Remolque
            ultima_m_r = rem.mantenciones_remolque.order_by("-fecha_mantencion").first()
            if ultima_m_r:
                est, motivo = estado_mantencion(float(rem.kilometraje_acumulado), ultima_m_r.km_proxima_mantencion)
                # Si el remolque está mal, el color de su fila cambia
                if ESTADO_PRIORIDAD[est] > 1:
                    estado_rem_css = f"estado-{est.lower()}"
                if motivo: motivos_remolque.append(f"Remolque: {motivo}")

            # 📄 Documentos Remolque
            docs_r = DocumentacionGeneral.objects.filter(tipo_entidad="REMOLQUE", id_referencia=rem.id_remolque)
            for doc in docs_r:
                est, motivo = estado_documento(doc.fecha_vencimiento)
                if ESTADO_PRIORIDAD[est] > 1:
                    # Guardamos la clase (ej: estado-vencido o estado-critico)
                    estado_rem_css = f"estado-{est.lower()}"
                if motivo: motivos_remolque.append(f"Doc Remolque ({doc.get_categoria_display()}): {motivo}")

        # --- CONSTRUCCIÓN DE RESPUESTA ---
        resultado.append({
            "id_camion": camion.id_camion,
            "id_remolque": id_remolque,
            "estado": estado_global,             # Color para el tracto
            "motivos": motivos_tracto,           # Motivos tracto
            "motivos_remolque": motivos_remolque, # Motivos remolque
            "estado_remolque_css": estado_rem_css # Clase para la fila del remolque
        })

    return JsonResponse(resultado, safe=False)