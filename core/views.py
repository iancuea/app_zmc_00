from django.shortcuts import render, get_object_or_404
from .models import Camion, EstadoCamion, Mantencion
from django.http import JsonResponse


def camion_list(request):
    camiones = Camion.objects.all().order_by('patente')
    return render(request, 'core/camion_list.html', {
        'camiones': camiones
    })

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