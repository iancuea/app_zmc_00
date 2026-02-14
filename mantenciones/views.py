import json
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db import transaction
from django.contrib import messages

from mantenciones.forms import InspeccionForm

# Importamos modelos de ambas apps
from .models import (
    CategoriaChecklist, ItemChecklist, Inspeccion, 
    ResultadoItem, RegistroLubricantes
)
from core.models import EstadoCamion, Mantencion 

def crear_inspeccion(request):
    if request.method == 'POST':
        form = InspeccionForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Guardamos la nueva Inspección (Registro Técnico detallado)
                    inspeccion = form.save(commit=False)
                    inspeccion.fecha_ingreso = timezone.now()
                    inspeccion.save()

                    # 2. Actualizamos el Kilometraje Actual (Dashboard Tarjeta)
                    camion = inspeccion.camion
                    estado = getattr(camion, 'estado_actual', None)
                    if estado:
                        estado.kilometraje = inspeccion.kilometraje_unidad
                        estado.save()

                    # 3. Procesamos el Checklist B-R-M (JSON)
                    checklist_raw = request.POST.get('checklist_json')
                    if checklist_raw:
                        checklist_data = json.loads(checklist_raw)
                        for data in checklist_data:
                            item = ItemChecklist.objects.get(id=data['id'])
                            ResultadoItem.objects.create(
                                inspeccion=inspeccion,
                                item=item,
                                estado=data['estado']
                            )

                    # 4. ACTUALIZACIÓN DEL LOG E HISTORIAL (Tabla core 'mantenciones')
                    aceite_renovado = request.POST.get('aceite_motor_renovado') == 'true'
                    
                    if aceite_renovado:
                        # Calculamos la meta basada en el intervalo del camión (25k, 50k, etc.)
                        nueva_meta = inspeccion.kilometraje_unidad + camion.intervalo_mantencion
                        
                        # Guardamos en la tabla NUEVA (Lubricantes) para auditoría técnica
                        RegistroLubricantes.objects.create(
                            inspeccion=inspeccion,
                            tipo_lubricante="ACEITE MOTOR",
                            renovado=True,
                            proximo_cambio_km=nueva_meta
                        )

                        # --- EL HISTORIAL: CREAMOS UN NUEVO REGISTRO EN EL LOG ---
                        # Usamos .create() para que aparezca como una nueva fila en el Log de Mantenciones
                        Mantencion.objects.create(
                            camion=camion,
                            taller='ZMC',
                            fecha_mantencion=timezone.now().date(),
                            km_mantencion=inspeccion.kilometraje_unidad,
                            km_proxima_mantencion=nueva_meta,
                            # Combinamos responsable y observaciones para el detalle del Log
                            observaciones=f"Realizado por {inspeccion.responsable}. {inspeccion.observaciones or ''}",
                            fecha_creacion=timezone.now()
                        )
                    # ------------------------------------------------------------

                messages.success(request, f"¡Mantención de {camion.patente} exitosa! Log y Semáforo actualizados.")
                return redirect('camion_list')

            except Exception as e:
                messages.error(request, f"Error al guardar: {e}")
                print(f"Error crítico en view: {e}")
        else:
            messages.error(request, "Formulario inválido.")
    
    else:
        form = InspeccionForm()

    categorias = CategoriaChecklist.objects.all().order_by('orden')
    return render(request, 'mantenciones/crear_inspeccion.html', {
        'form': form,
        'categorias': categorias
    })