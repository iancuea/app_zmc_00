from django.shortcuts import render, get_object_or_404
from .models import Camion, EstadoCamion, Mantencion, DocumentacionGeneral
from django.http import JsonResponse
from django.db.models import Max
from .utils import estado_mantencion, estado_documento, ESTADO_PRIORIDAD


def camion_list(request):
    camiones = Camion.objects.all()

    # --- FILTRO POR ESTADO ---
    estado = request.GET.get("estado")
    if estado:
        camiones = [
            c for c in camiones
            if c.estado_mantencion()["codigo"] == estado
        ]

    # --- ORDENAR POR PRIORIDAD ---
    ordenar = request.GET.get("orden")
    if ordenar == "urgencia":
        camiones = sorted(
            camiones,
            key=lambda c: c.prioridad_mantencion()
        )

    context = {
        "camiones": camiones,
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

    camiones = Camion.objects.filter(activo=True).select_related("estado_actual")

    for camion in camiones:
        estado_global = "OK"
        prioridad_global = ESTADO_PRIORIDAD["OK"]
        motivos = []

        estado_actual = getattr(camion, "estado_actual", None)
        km_actual = estado_actual.kilometraje if estado_actual else None

        # 🔧 Mantención
        ultima_mantencion = camion.mantenciones.order_by("-fecha_mantencion").first()
        if ultima_mantencion:
            estado, motivo = estado_mantencion(
                km_actual,
                ultima_mantencion.km_proxima_mantencion
            )
            if ESTADO_PRIORIDAD[estado] > prioridad_global:
                estado_global = estado
                prioridad_global = ESTADO_PRIORIDAD[estado]
            if motivo:
                motivos.append(motivo)

        # 📄 Documentación del camión
        documentos = DocumentacionGeneral.objects.filter(
            tipo_entidad="CAMION",
            id_referencia=camion.id_camion
        )

        for doc in documentos:
            estado, motivo = estado_documento(doc.fecha_vencimiento)
            if ESTADO_PRIORIDAD[estado] > prioridad_global:
                estado_global = estado
                prioridad_global = ESTADO_PRIORIDAD[estado]
            if motivo:
                motivos.append(f"{doc.get_categoria_display()}: {motivo}")

        resultado.append({
            "id_camion": camion.id_camion,
            "patente": camion.patente,
            "estado": estado_global,
            "urgencia": prioridad_global,
            "conductor": estado_actual.conductor.nombre if estado_actual and estado_actual.conductor else None,
            "motivos": motivos
        })

    # Orden por urgencia (más crítico primero)
    resultado.sort(key=lambda x: x["urgencia"], reverse=True)

    return JsonResponse(resultado, safe=False)