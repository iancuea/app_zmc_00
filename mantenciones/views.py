"""
mantenciones/views.py
Vistas para crear inspecciones de mantenimiento con generación de PDF y envío de correos.
Implementa APIs para autocompletado de datos, categorías y validación de remolques asignados.
"""

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
    ResultadoItem, RegistroLubricantes, RegistroDiario, CronogramaPlan
)
from core.models import DocumentoMantencion, EstadoCamion, Mantencion, Camion, Remolque, AsignacionTractoRemolque
from mantenciones import models
from django.db.models import Q
from django.core.mail import EmailMessage
from django.conf import settings
import os

@login_required
def crear_inspeccion(request):
    """
    Procesa la creación de una inspección con su checklist.
    
    Flujo:
    1. Guarda inspección y resultados en BD (transacción atómica)
    2. Genera PDF del reporte (diario o técnico)
    3. Envía correo con el PDF adjunto
    4. Redirige a la página de creación
    """
    
    """Vista para crear una nueva inspección con checklist dinámico"""
    
    if request.method == 'POST':
        form = InspeccionForm(request.POST)
        
        if form.is_valid():
            ruta_pdf = None  
            try:
                # 1. BLOQUE DE BASE DE DATOS (Transacción Atómica)
                with transaction.atomic():
                    # Guardamos la Inspección
                    inspeccion = form.save(commit=False)
                    inspeccion.fecha_ingreso = timezone.localtime(timezone.now())
                    inspeccion.save()
                    
                    # Procesar resultados del checklist
                    resultados_raw = request.POST.get('resultados_checklist', '[]')
                    resultados_data = json.loads(resultados_raw)
                    
                    for data in resultados_data:
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
                    
                    # Datos autocompletado (solo para lógica interna aquí)
                    datos_autocompletado = obtener_datos_camion_autocompletado(inspeccion.camion)
                    datos_autocompletado['apto_trabajar'] = 'SI' if inspeccion.es_apto_operar else 'NO'
                    fecha_chile = timezone.localtime(inspeccion.fecha_ingreso)
                    datos_autocompletado['fecha_inspeccion'] = fecha_chile.strftime('%d/%m/%Y %H:%M')

                    # Guardar en RegistroDiario
                    RegistroDiario.objects.create(
                        vehiculo=inspeccion.camion,
                        revisado_por=inspeccion.responsable,
                        km_actual=inspeccion.km_registro,
                        es_apto=inspeccion.es_apto_operar,
                        check_datos=json.dumps(resultados_data),
                        novedades=inspeccion.observaciones
                    )
                    
                    # Lógica de Mantención y Próxima Meta
                    nueva_meta = inspeccion.km_registro
                    if inspeccion.renovó_aceite:
                        nueva_meta = inspeccion.km_registro + inspeccion.camion.intervalo_mantencion

                    nueva_mantencion = Mantencion.objects.create(
                        camion=inspeccion.camion,
                        taller='ZMC',
                        fecha_mantencion=timezone.now().date(),
                        km_mantencion=inspeccion.km_registro,
                        km_proxima_mantencion=nueva_meta,
                        observaciones=f"Checklist realizado por {inspeccion.responsable}."
                    )

                    # Actualizar KM actual del camión
                    if hasattr(inspeccion.camion, 'estado_actual'):
                        inspeccion.camion.estado_actual.kilometraje = inspeccion.km_registro
                        inspeccion.camion.estado_actual.save()

                # --- 2. BLOQUE DE GENERACIÓN (FUERA DE LA TRANSACCIÓN) ---
                # Ahora que la transacción cerró, los resultados_items EXISTEN en la DB.
                resultados_items = ResultadoItem.objects.filter(inspeccion=inspeccion).select_related('item')

                if inspeccion.tipo_inspeccion == 'DIARIO':
                    ruta_pdf = generar_pdf_enap_diario(inspeccion, resultados_items, datos_autocompletado)                     
                else:
                    ruta_pdf = generar_pdf_mantencion_tecnica(inspeccion, resultados_items, datos_autocompletado)

                # Registrar el PDF generado en la base de datos
                if ruta_pdf:
                    DocumentoMantencion.objects.create(
                        mantencion=nueva_mantencion,
                        nombre_archivo=f"Checklist_{inspeccion.camion.patente}_{inspeccion.fecha_ingreso.strftime('%Y%m%d')}.pdf",
                        ruta_archivo=ruta_pdf,
                        tipo_documento='CHECKLIST_ENAP'
                    )

                # --- BLOQUE DE CORREO (FUERA DE LA TRANSACCIÓN) ---
                if ruta_pdf and os.path.exists(ruta_pdf):
                    try:
                        destinatarios = ['iancuevas7321@gmail.com', 'gestion.flota.zmc@gmail.com','bsantanav@gmail.com']
                        sujeto = f"📝 NUEVO CHECKLIST: {inspeccion.camion.patente} - {inspeccion.tipo_inspeccion}"
                        
                        # Cuerpo del mensaje con formato profesional
                        cuerpo = (
                            f"Se ha registrado una nueva inspección en el sistema.\n\n"
                            f"--- DETALLES DE LA UNIDAD ---\n"
                            f" Unidad: {inspeccion.camion.patente}\n"
                            f" Responsable: {inspeccion.responsable}\n"
                            f" Kilometraje: {inspeccion.km_registro:,} KM\n"
                            f" Fecha/Hora: {datos_autocompletado['fecha_inspeccion']}\n"
                            f" Contrato: {datos_autocompletado.get('contrato', 'GENERAL')}\n\n"
                            f"--- ESTADO DE OPERACIÓN ---\n"
                            f" ¿Apto para trabajar?: {'SÍ' if inspeccion.es_apto_operar else 'NO'}\n"
                            f" ¿Renovó Aceite?: {'SÍ' if inspeccion.renovó_aceite else 'NO'}\n"
                            f" Observaciones: {inspeccion.observaciones if inspeccion.observaciones else 'Sin observaciones.'}\n\n"
                            f"Se adjunta el informe técnico detallado en formato PDF.\n\n"
                            f"Atentamente,\n"
                            f"Sistema de Gestión de Flota ZMC"
                        )

                        email = EmailMessage(
                            subject=sujeto,
                            body=cuerpo,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=destinatarios,
                        )

                        # Adjuntamos el archivo con un nombre más limpio
                        with open(ruta_pdf, 'rb') as f:
                            email.attach(f"Checklist_{inspeccion.camion.patente}_{inspeccion.fecha_ingreso.strftime('%d-%m-%Y')}.pdf", f.read(), 'application/pdf')

                        email.send()
                        print(f"DEBUG: Correo enviado con éxito para {inspeccion.camion.patente}")

                    except Exception as e_mail:
                        print(f"ERROR al enviar correo: {e_mail}")

                # --- 4. REDIRECT (EVITA DUPLICADOS AL REFRESCAR) ---
                messages.success(request, f"✅ Inspección enviada y reporte enviado por correo.")
                return redirect('/mantenciones/nueva/')

            except Exception as e:
                messages.error(request, f"Error crítico: {str(e)}")
                print(f"Error: {e}")
    
    else:
        form = InspeccionForm()
    
    categorias = CategoriaChecklist.objects.all().order_by('orden')
    return render(request, 'mantenciones/crear_inspeccion.html', {'form': form, 'categorias': categorias})

@require_http_methods(["GET"])
def api_datos_autocompletado(request, camion_id):
    """
    API que retorna todos los datos del camión para auto-llenar el formulario:
    - Datos del camión: marca, modelo, patente, año
    - Datos del conductor: nombre, antigüedad
    - Vencimientos de documentos
    - Datos del remolque (si está asignado)
    """
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
    API que retorna todas las categorías y sus items filtrando por tipo de inspección.
    
    Retorna:
    - DIARIO: Solo categorías de checklist diario
    - MANTENCION: Solo categorías de mantención técnica
    - AMBOS: Categorías comunes
    """
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
    API que verifica si un camión tiene un remolque asignado actualmente.
    
    Retorna:
    - tiene_remolque: True si hay remolque activo
    - remolque_id y remolque_patente (si existe)
    """
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
    
