import json
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from mantenciones.forms import InspeccionForm
from .utils import obtener_datos_camion_autocompletado, generar_pdf_enap_diario, generar_pdf_mantencion_tecnica
from .models import (
    CategoriaChecklist, ItemChecklist, Inspeccion, 
    ResultadoItem, RegistroLubricantes, RegistroDiario
)
from core.models import DocumentoMantencion, EstadoCamion, Mantencion, Camion, Remolque, AsignacionTractoRemolque
from mantenciones import models
from django.db.models import Q
from django.core.mail import EmailMessage
from django.conf import settings
import os

@login_required
def crear_inspeccion(request):
    """Vista para crear una nueva inspección con checklist dinámico"""
    
    if request.method == 'POST':
        form = InspeccionForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Guardamos la Inspección
                    inspeccion = form.save(commit=False)
                    inspeccion.fecha_ingreso = timezone.localtime(timezone.now())
                    inspeccion.save()
                    
                    # 2. Procesar resultados del checklist
                    resultados_raw = request.POST.get('resultados_checklist', '[]')
                    resultados_data = json.loads(resultados_raw)
                    
                    for data in resultados_data:
                        print(f"DEBUG: Guardando Item ID {data['item_id']} - Estado: '{data['estado']}'")
                        try:
                            item = ItemChecklist.objects.get(id=data['item_id'])
                            ResultadoItem.objects.create(
                                inspeccion=inspeccion,
                                item=item,
                                estado=data['estado'],
                                observacion=data.get('observacion', '')
                            )
                        except ItemChecklist.DoesNotExist:
                            continue
                    
                    # 3. Obtener datos auto-completados
                    datos_autocompletado = obtener_datos_camion_autocompletado(inspeccion.vehiculo)
                    datos_autocompletado['apto_trabajar'] = 'SI' if inspeccion.es_apto_operar else 'NO'
                    fecha_chile = timezone.localtime(inspeccion.fecha_ingreso)
                    datos_autocompletado['fecha_inspeccion'] = fecha_chile.strftime('%d/%m/%Y %H:%M')
                    
                    # 4. Generar PDF
                    resultados_items = inspeccion.resultados.all().select_related('item')
                    if inspeccion.tipo_inspeccion == 'DIARIO':
                        ruta_pdf = generar_pdf_enap_diario(inspeccion, resultados_items, datos_autocompletado)                    
                    else:
                        ruta_pdf = generar_pdf_mantencion_tecnica(inspeccion, resultados_items, datos_autocompletado)

                    print(f"DEBUG: La ruta del PDF es -> {ruta_pdf}")
                    
                    # 5. Guardar registro en RegistroDiario
                    registro_diario = RegistroDiario.objects.create(
                        vehiculo=inspeccion.vehiculo,
                        revisado_por=inspeccion.responsable,
                        km_actual=inspeccion.km_registro,
                        es_apto=inspeccion.es_apto_operar,
                        check_datos=json.dumps(resultados_data),
                        novedades=inspeccion.observaciones
                    )
                    
                    # 6. Crear la Mantención "Cabecera" siempre (necesaria para el documento)
                    nueva_meta = inspeccion.km_registro
                    if inspeccion.renovó_aceite:
                        nueva_meta = inspeccion.km_registro + inspeccion.vehiculo.intervalo_mantencion

                    nueva_mantencion = Mantencion.objects.create(
                        camion=inspeccion.vehiculo,
                        taller='ZMC',
                        fecha_mantencion=timezone.now().date(),
                        km_mantencion=inspeccion.km_registro,
                        km_proxima_mantencion=nueva_meta,
                        observaciones=f"Checklist realizado por {inspeccion.responsable}.",
                        fecha_creacion=timezone.now()
                    )

                    # 7. Guardar el registro del PDF en DocumentoMantencion
                    if ruta_pdf:
                        DocumentoMantencion.objects.create(
                            mantencion=nueva_mantencion,
                            nombre_archivo=f"Checklist_{inspeccion.vehiculo.patente}_{inspeccion.fecha_ingreso.strftime('%Y%m%d')}.pdf",
                            ruta_archivo=ruta_pdf,
                            tipo_documento='CHECKLIST_ENAP',
                            fecha_subida=timezone.now()
                        )
                    
                    # 8. SOLO si se renovó aceite, crear el registro específico de lubricantes
                    if inspeccion.renovó_aceite:
                        RegistroLubricantes.objects.create(
                            inspeccion=inspeccion,
                            tipo_lubricante="ACEITE MOTOR",
                            renovado=True,
                            proximo_cambio_km=nueva_meta
                        )

                    # 9. Actualizar estado actual del camión
                    if hasattr(inspeccion.vehiculo, 'estado_actual'):
                        inspeccion.vehiculo.estado_actual.kilometraje = inspeccion.km_registro
                        inspeccion.vehiculo.estado_actual.save()

                    # --- NUEVO: ENVÍO DE CORREO AUTOMÁTICO CON EL PDF ---
                    if ruta_pdf and os.path.exists(ruta_pdf):
                        try:
                            destinatarios = ['iancuevas7321@gmail.com', 'gestion.flota.zmc@gmail.com']
                            sujeto = f"📝 NUEVO CHECKLIST: {inspeccion.vehiculo.patente} - {inspeccion.tipo_inspeccion}"
                            cuerpo = (
                                f"Se ha registrado una nueva inspección.\n\n"
                                f"Unidad: {inspeccion.vehiculo.patente}\n"
                                f"Responsable: {inspeccion.responsable}\n"
                                f"Kilometraje: {inspeccion.km_registro}\n"
                                f"Apto para operar: {'SÍ' if inspeccion.es_apto_operar else 'NO'}\n"
                                f"Fecha: {datos_autocompletado['fecha_inspeccion']}\n\n"
                                f"Se adjunta el informe PDF."
                            )

                            email = EmailMessage(
                                subject=sujeto,
                                body=cuerpo,
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                to=destinatarios,
                            )

                            with open(ruta_pdf, 'rb') as f:
                                email.attach(f"Checklist_{inspeccion.vehiculo.patente}.pdf", f.read(), 'application/pdf')

                            email.send()
                            print(f"DEBUG: Correo enviado con éxito para {inspeccion.vehiculo.patente}")
                        except Exception as e_mail:
                            print(f"ERROR al enviar correo: {e_mail}")
                    # --- FIN BLOQUE CORREO ---

                    messages.success(
                        request, 
                        f"¡Inspección de {inspeccion.vehiculo.patente} completada! PDF generado."
                    )
                    return redirect('camion_list')
                    
            except json.JSONDecodeError:
                messages.error(request, "Error procesando el checklist. Intenta nuevamente.")
            except Exception as e:
                messages.error(request, f"Error al guardar: {str(e)}")
                print(f"Error crítico: {e}")
    
    else:
        form = InspeccionForm()
    
    categorias = CategoriaChecklist.objects.all().order_by('orden')
    context = {
        'form': form,
        'categorias': categorias
    }
    return render(request, 'mantenciones/crear_inspeccion.html', context)

@require_http_methods(["GET"])
def api_datos_autocompletado(request, camion_id):
    """
    API que retorna los datos que se auto-completan al seleccionar un camión
    """
    try:
        camion = get_object_or_404(Camion, id_camion=camion_id)
        datos = obtener_datos_camion_autocompletado(camion)
        
        return JsonResponse({
            'success': True,
            'datos': datos
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["GET"])
def api_categorias_por_tipo(request, tipo_inspeccion):
    """
    API que retorna todas las categorías de checklist
    """
    try:
        categorias = CategoriaChecklist.objects.filter(
            Q(filtro_tipo=tipo_inspeccion) | Q(filtro_tipo='AMBOS')
        ).prefetch_related('items').order_by('orden')
        
        categorias_con_items = []
        for cat in categorias:
            items = ItemChecklist.objects.filter(categoria=cat).values(
                'id', 
                'nombre', 
                'es_critico', 
                'tipo_respuesta',
                'es_opcional'  # <-- AGREGAR ESTO
            )            
            cat_data = {
                'id': cat.id,
                'nombre': cat.nombre,
                'orden': cat.orden,
                'items': list(items)
            }
            categorias_con_items.append(cat_data)
        
        return JsonResponse({
            'success': True,
            'categorias': categorias_con_items
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@require_http_methods(["GET"])
def api_remolque_asignado(request, camion_id):
    """
    API que verifica si un camión tiene remolque asignado
    """
    try:
        camion = get_object_or_404(Camion, id_camion=camion_id)
        asignacion = AsignacionTractoRemolque.objects.filter(
            camion=camion,
            activo=True
        ).first()
        
        if asignacion:
            return JsonResponse({
                'success': True,
                'tiene_remolque': True,
                'remolque_id': asignacion.remolque.id_remolque,
                'remolque_patente': asignacion.remolque.patente
            })
        else:
            return JsonResponse({
                'success': True,
                'tiene_remolque': False
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    
