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
from django.db.models import Q, Max, Min
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import datetime, timedelta

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
                    
                    # --- NUEVA LÓGICA DE MANTENCIÓN Y PRÓXIMA META (KAUFMANN/FTL) ---
                    intervalo_base = 20000 

                    if inspeccion.camion.modelo:
                        if inspeccion.camion.modelo.marca == 'Mercedes-Benz':
                            intervalo_base = 40000  
                        else:
                            intervalo_base = 30000  

                    # Ajuste por Tipo de Operación
                    if inspeccion.camion.tipo_operacion == 'SEVERO':
                        intervalo_base = intervalo_base * 0.25  
                    elif inspeccion.camion.tipo_operacion == 'MIXTO':
                        intervalo_base = intervalo_base * 0.5   

                    # Cálculo de la meta según el tipo de reporte
                    if inspeccion.tipo_inspeccion == 'DIARIO':
                        if inspeccion.renovó_aceite:
                            nueva_meta = inspeccion.km_registro + intervalo_base
                        else:
                            # Si es diario sin cambio de aceite, busca la meta anterior
                            ultima_m = Mantencion.objects.filter(camion=inspeccion.camion).last()
                            nueva_meta = ultima_m.km_proxima_mantencion if ultima_m else inspeccion.km_registro
                    else:
                        # Si es una preventiva (SM1, SM2, etc.), se setea la nueva meta obligatoriamente
                        nueva_meta = inspeccion.km_registro + intervalo_base

                    # Guardar la mantención técnica en el historial
                    nueva_mantencion = Mantencion.objects.create(
                        camion=inspeccion.camion,
                        taller='ZMC',
                        fecha_mantencion=timezone.now().date(),
                        km_mantencion=inspeccion.km_registro,
                        km_proxima_mantencion=nueva_meta,
                        observaciones=f"Servicio {inspeccion.tipo_inspeccion} realizado por {inspeccion.responsable}."
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

@login_required 
def vista_gantt_mvp(request):
    """Renderiza el contenedor básico del MVP de la Carta Gantt"""
    return render(request, 'mantenciones/gantt_mvp.html')

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
        
        # --- NUEVA LÓGICA DE SUGERENCIA ---
        sugerencia = "DIARIO"
        paquetes_sugeridos = []
        
        # Buscamos cuántas mantenciones preventivas tiene este camión
        conteo_preventivas = Inspeccion.objects.filter(
            camion=camion
        ).exclude(tipo_inspeccion='DIARIO').count()
        
        if camion.modelo:
            # Calculamos la posición en el ciclo (ej: 1 al 8 o 1 al 16)
            posicion = (conteo_preventivas % CronogramaPlan.objects.filter(modelo=camion.modelo).count()) + 1
            
            plan = CronogramaPlan.objects.filter(
                modelo=camion.modelo, 
                posicion_ciclo=posicion
            ).first()
            
            if plan:
                paquetes_sugeridos = plan.paquetes_json # Ej: ["SM2", "MB1"]
                sugerencia = f"Sugerido: {', '.join(paquetes_sugeridos)}"

        return JsonResponse({
            'success': True,
            'datos': datos,
            'sugerencia_mantenimiento': {
                'texto': sugerencia,
                'paquetes': paquetes_sugeridos
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

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
    camion_id = request.GET.get('camion_id') # Enviamos el ID por parámetro
    
    try:
        # Filtro base por categoría
        # Si es una mantención preventiva, el 'tipo_inspeccion' vendrá como "SM2", "SM1", etc.
        
        if tipo_inspeccion == 'DIARIO':
            q_items = Q(nivel_servicio='DIARIO')
        else:
            # Lógica de Herencia: Si es SM2, traemos tareas de SM1 y SM2
            # Determinamos los niveles a cargar (esto depende de cómo nombres tus niveles)
            niveles_a_cargar = [tipo_inspeccion]
            if "SM" in tipo_inspeccion:
                num = int(tipo_inspeccion.replace("SM", ""))
                niveles_a_cargar = [f"SM{i}" for i in range(1, num + 1)]
            
            q_items = Q(nivel_servicio__in=niveles_a_cargar)
            if camion_id:
                camion = Camion.objects.get(id_camion=camion_id)
                q_items &= Q(modelo=camion.modelo)

        categorias = CategoriaChecklist.objects.all().order_by('orden')
        
        categorias_con_items = []
        for cat in categorias:
            # Filtramos ítems dinámicamente según modelo y nivel
            items = ItemChecklist.objects.filter(
                q_items, 
                categoria=cat
            ).values('id', 'nombre', 'es_critico', 'tipo_respuesta', 'es_opcional', 'referencia_tecnica', 'codigo_sap')
            
            if items.exists():
                categorias_con_items.append({
                    'id': cat.id,
                    'nombre': cat.nombre,
                    'items': list(items)
                })
        
        return JsonResponse({'success': True, 'categorias': categorias_con_items})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

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
    
@require_http_methods(["GET"])
def api_gantt_proyeccion(request):
    """
    Genera la proyección predictiva de mantenciones preventivas para la flota
    desde el día de hoy hasta el 31 de Enero de 2027 basada en telemetría diaria.
    """
    fecha_hoy = timezone.now()
    fecha_limite = datetime(2027, 1, 31, 23, 59, 59)
    
    # Validar zona horaria para evitar choques entre objetos Aware y Naive
    if timezone.is_aware(fecha_hoy):
        fecha_limite = timezone.make_aware(fecha_limite)
        
    data_gantt = []
    
    # 1. Obtener todos los camiones activos usando tu modelo Camion
    camiones_activos = Camion.objects.filter(activo=True)
    
    for camion in camiones_activos:
        # 2. Punto de partida: Kilometraje desde tu modelo EstadoCamion
        estado = EstadoCamion.objects.filter(camion=camion).first()
        if not estado or estado.kilometraje is None:
            continue  # Si no tiene estado operativo base, saltar para evitar caídas
            
        km_simulado = float(estado.kilometraje)
        
        # 3. Calcular la Tasa de Uso Diaria Real usando tu modelo RegistroDiario (Últimos 30 días)
        fecha_hace_mes = fecha_hoy - timedelta(days=30)
        registros_mes = RegistroDiario.objects.filter(
            vehiculo=camion,
            fecha__gte=fecha_hace_mes
        ).order_by('fecha')
        
        if registros_mes.count() >= 2:
            agg = registros_mes.aggregate(
                km_max=Max('km_actual'),
                km_min=Min('km_actual'),
                fecha_max=Max('fecha'),
                fecha_min=Min('fecha')
            )
            delta_km = agg['km_max'] - agg['km_min']
            delta_dias = (agg['fecha_max'] - agg['fecha_min']).days or 1
            
            # Si el cálculo da 0 o negativo por error de tipeo, resguardamos con fallback seguro
            km_diario_promedio = float(delta_km / delta_dias)
            if km_diario_promedio <= 0:
                km_diario_promedio = 150.0
        else:
            # Coeficiente estándar de uso diario si el camión es nuevo o no registra rutas
            km_diario_promedio = 150.0 
            
        # 4. Cargar la matriz de pautas teóricas desde tu modelo CronogramaPlan
        plan_maestro = CronogramaPlan.objects.filter(modelo=camion.modelo).first()
        if plan_maestro and plan_maestro.paquetes_json:
            ciclo_planes = plan_maestro.paquetes_json  # Lee directo el array jsonb de Postgres
            intervalo = int(plan_maestro.intervalo_teorico or camion.intervalo_mantencion or 25000)
        else:
            # Respaldo secuencial clásico si el modelo no tiene cronograma asociado
            ciclo_planes = ["SM1", "SM2", "SM3", "SM4"]
            intervalo = int(camion.intervalo_mantencion or 25000)
            
        # 5. Buscar último hito real en taller usando tu modelo Mantencion
        ultima_mantencion = Mantencion.objects.filter(
            camion=camion, 
            tipo_mantencion='TALLER'
        ).order_by('-fecha_mantencion').first()
        
        if ultima_mantencion and ultima_mantencion.km_proxima_mantencion:
            proximo_km_mantencion = float(ultima_mantencion.km_proxima_mantencion)
        else:
            # Si arranca limpio, calculamos matemáticamente el próximo umbral teórico
            proximo_km_mantencion = float(((int(km_simulado) // intervalo) + 1) * intervalo)
            
        fecha_simulada = fecha_hoy
        
        # 6. Simulación matemática temporal día a día hacia el horizonte de Enero 2027
        while fecha_simulada <= fecha_limite:
            km_simulado += km_diario_promedio
            fecha_simulada += timedelta(days=1)
            
            # Condición de activación preventiva: El camión alcanzó los kilómetros del servicio
            if km_simulado >= proximo_km_mantencion:
                # Calcular la pauta técnica correspondiente según el ciclo dinámico
                posicion_en_ciclo = int(proximo_km_mantencion // intervalo) - 1
                nombre_plan = ciclo_planes[posicion_en_ciclo % len(ciclo_planes)]
                
                # Seteo estético para la Gantt: Diferenciar motores/cajas (MB, SC, ST) de Chasis estándar (SM, SIM)
                color_render = "#e056fd" if any(x in nombre_plan for x in ["MB", "SC", "ST"]) else "#30336b"
                
                data_gantt.append({
                    "id": f"pred_{camion.id_camion}_{int(proximo_km_mantencion)}",
                    "text": f"🚚 {camion.patente} - Mantención {nombre_plan}",
                    "start_date": fecha_simulada.strftime("%Y-%m-%d"),
                    "end_date": (fecha_simulada + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "km_proyectado": int(proximo_km_mantencion),
                    "patente": camion.patente,
                    "color": color_render
                })
                
                # Desplazar el objetivo al siguiente servicio preventivo
                proximo_km_mantencion += intervalo
                
    return JsonResponse(data_gantt, safe=False)
