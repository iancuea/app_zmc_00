"""
Utilidades para reportes y generación de PDFs de inspecciones
"""
from datetime import datetime
from django.utils import timezone
from core.models import DocumentacionGeneral
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os

def obtener_datos_camion_autocompletado(camion):
    """
    Retorna un diccionario con todos los datos que se auto-llenan 
    basado en el camión seleccionado
    """
    datos = {
        'fecha_inspeccion': timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M'),
        'lugar_inspeccion': camion.estado_actual.get_base_actual_display() if hasattr(camion, 'estado_actual') else 'N/A',
        'contratista': 'ENAP',
        'contrato': 'Transporte de Productos Líquidos',
        'conductor_nombre': '',
        'conductor_antiguedad': '',
        'fecha_control': '',
        'apto_trabajar': '',
        'camion_marca': camion.marca or 'N/A',
        'camion_modelo': camion.modelo or 'N/A',
        'camion_patente': camion.patente,
        'camion_anio': camion.anio or 'N/A',
        'camion_odometro': '',  # Se pasa desde el form (km_registro)
        'camion_vto_rt': 'N/A',
        'camion_vto_pc': 'N/A',
        'camion_vto_soap': 'N/A',
        'camion_vto_tc8': 'N/A',
        'remolque_marca': 'N/A',
        'remolque_modelo': 'N/A',
        'remolque_anio': 'N/A',
        'remolque_patente': 'N/A',
        'remolque_capacidad': 'N/A',
        'remolque_vto_rt': 'N/A',
        'remolque_vto_pc': 'N/A',
        'remolque_vto_soap': 'N/A',
        'remolque_vto_tc8': 'N/A',
        'tiene_remolque': False,
    }
    
    # Llenar datos del conductor
    if hasattr(camion, 'estado_actual') and camion.estado_actual.conductor:
        conductor = camion.estado_actual.conductor
        datos['conductor_nombre'] = conductor.nombre
        # NOTA: Si en futuro agregamos campo 'antiguedad' al Conductor, descomentar:
        # datos['conductor_antiguedad'] = conductor.antiguedad
        datos['fecha_control'] = timezone.now().strftime('%d/%m/%Y')
    
    # Buscar documentos del camión
    docs_camion = DocumentacionGeneral.objects.filter(
        camion=camion,
        tipo_entidad='CAMION'
    )
    for doc in docs_camion:
        if doc.categoria == 'REVISION_TECNICA':
            datos['camion_vto_rt'] = doc.fecha_vencimiento.strftime('%d/%m/%Y') if doc.fecha_vencimiento else 'N/A'
        elif doc.categoria == 'PERMISO_CIRCULACION':
            datos['camion_vto_pc'] = doc.fecha_vencimiento.strftime('%d/%m/%Y') if doc.fecha_vencimiento else 'N/A'
        elif doc.categoria == 'SOAP':
            datos['camion_vto_soap'] = doc.fecha_vencimiento.strftime('%d/%m/%Y') if doc.fecha_vencimiento else 'N/A'
        elif doc.categoria == 'TC8':
            datos['camion_vto_tc8'] = doc.fecha_vencimiento.strftime('%d/%m/%Y') if doc.fecha_vencimiento else 'N/A'
    
    # Verificar si tiene remolque asignado
    from core.models import AsignacionTractoRemolque
    asignacion = AsignacionTractoRemolque.objects.filter(
        camion=camion,
        activo=True
    ).first()
    
    if asignacion:
        remolque = asignacion.remolque
        datos['tiene_remolque'] = True
        datos['remolque_marca'] = remolque.marca or 'N/A'
        datos['remolque_modelo'] = remolque.modelo or 'N/A'
        datos['remolque_anio'] = remolque.anio or 'N/A'
        datos['remolque_patente'] = remolque.patente
        datos['remolque_capacidad'] = str(remolque.capacidad_carga) if remolque.capacidad_carga else 'N/A'
        
        # Buscar documentos del remolque
        docs_remolque = DocumentacionGeneral.objects.filter(
            remolque=remolque,
            tipo_entidad='REMOLQUE'
        )
        for doc in docs_remolque:
            if doc.categoria == 'REVISION_TECNICA':
                datos['remolque_vto_rt'] = doc.fecha_vencimiento.strftime('%d/%m/%Y') if doc.fecha_vencimiento else 'N/A'
            elif doc.categoria == 'PERMISO_CIRCULACION':
                datos['remolque_vto_pc'] = doc.fecha_vencimiento.strftime('%d/%m/%Y') if doc.fecha_vencimiento else 'N/A'
            elif doc.categoria == 'SOAP':
                datos['remolque_vto_soap'] = doc.fecha_vencimiento.strftime('%d/%m/%Y') if doc.fecha_vencimiento else 'N/A'
            elif doc.categoria == 'TC8':
                datos['remolque_vto_tc8'] = doc.fecha_vencimiento.strftime('%d/%m/%Y') if doc.fecha_vencimiento else 'N/A'
    
    return datos

def generar_pdf_mantencion_tecnica(inspeccion, resultados_items, datos_autocompletado):
    return 0

def generar_pdf_enap_diario(inspeccion, resultados_items, datos_autocompletado):
    # Crear directorio
    tipo_insp = inspeccion.get_tipo_inspeccion_display().lower()
    directorio = f'media/reportes_diarios/{tipo_insp}/'
    os.makedirs(directorio, exist_ok=True)
    
    fecha_str = timezone.now().strftime('%Y%m%d_%H%M%S')
    patente = inspeccion.vehiculo.patente
    nombre_pdf = f'reporte_{fecha_str}_{patente}.pdf'
    ruta_pdf = os.path.join(directorio, nombre_pdf)
    
    # Reducimos márgenes para que quepa todo como en la foto
    doc = SimpleDocTemplate(ruta_pdf, pagesize=letter,
                            rightMargin=30, leftMargin=30, 
                            topMargin=30, bottomMargin=30)
    story = []
    
    # Estilos con tamaños aumentados
    title_style = ParagraphStyle('Title', fontSize=14, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=10)
    header_label = ParagraphStyle('Label', fontSize=11, fontName='Helvetica-Bold', spaceBefore=8, spaceAfter=4)
    
    # Estilo de tabla para datos: Letra 10 (Clara y grande)
    # Usamos fondo beige suave para los encabezados de celda como en tu foto
    base_style = [
        ['GRID', (0,0), (-1,-1), 0.7, colors.black],
        ['FONTSIZE', (0,0), (-1,-1), 11], 
        ['VALIGN', (0,0), (-1,-1), 'MIDDLE'],
        ['LEFTPADDING', (0,0), (-1,-1), 10],
        ['TOPPADDING', (0,0), (-1,-1), 6],
        ['BOTTOMPADDING', (0,0), (-1,-1), 6],
    ]

    # --- PÁGINA 1: CARÁTULA COMPLETA ---
    story.append(Paragraph("ZMC TRANSPORTES - ENAP", title_style))
    story.append(Paragraph("INSPECCIÓN DUEÑOS CAMIONES TANQUE", title_style))

    # 1. SECCIÓN INFORMACIÓN
    story.append(Paragraph("INFORMACIÓN", header_label))
    info_data = [
        ['Fecha Inspección:', datos_autocompletado['fecha_inspeccion'], 
         'Lugar:', datos_autocompletado['lugar_inspeccion']],
        ['Contratista:', 'ZENON MACIAS Y CIA. LTDA.', 
         'Contrato:', datos_autocompletado['contrato']],
    ]
    t1 = Table(info_data, colWidths=[1.3*inch, 2.45*inch, 1.3*inch, 2.45*inch])
    t1.setStyle(TableStyle(base_style + [('FONTSIZE', (0,0), (-1,-1), 9)]))
    story.append(t1)

    # 2. SECCIÓN CONDUCTOR
    story.append(Paragraph("CONDUCTOR", header_label))
    cond_data = [
        ['Nombre Conductor:', datos_autocompletado['conductor_nombre'], '', ''], # Fila 1
        ['Antigüedad:', datos_autocompletado.get('conductor_antiguedad', 'N/A'), 'Licencia:', 'A1/A2/D'], # Fila 2
        ['Fecha Control:', datos_autocompletado['fecha_control'], 'Lugar:', datos_autocompletado['lugar_inspeccion']], # Fila 3
        ['¿Apto para Trabajar?:', datos_autocompletado['apto_trabajar'], 'Observaciones:', ''], # Fila 4
    ]
    t2 = Table(cond_data, colWidths=[1.8*inch, 1.95*inch, 1.3*inch, 2.45*inch])
    t2.setStyle(TableStyle([
        ['GRID', (0,0), (-1,-1), 0.7, colors.black],
        ['FONTSIZE', (0,0), (-1,-1), 11], 
        ['VALIGN', (0,0), (-1,-1), 'MIDDLE'],
        ['LEFTPADDING', (0,0), (-1,-1), 10],
        ['TOPPADDING', (0,0), (-1,-1), 6],
        ['BOTTOMPADDING', (0,0), (-1,-1), 6],
        ['SPAN', (1, 0), (3, 0)], 
    ]))
    story.append(t2)
    #story.append(Spacer(1, 15))

    # 3. SECCIÓN CAMIÓN (6 columnas para que quepa todo el detalle técnico)
    story.append(Paragraph("CAMIÓN", header_label))
    c_w = 7.5*inch / 6
    camion_data = [
        ['Marca:', datos_autocompletado['camion_marca'], 'Modelo:', datos_autocompletado['camion_modelo'], 'Año:', datos_autocompletado['camion_anio']],
        ['Patente:', datos_autocompletado['camion_patente'], 'Odómetro:', f"{inspeccion.km_registro:,}", 'Vto. RT:', datos_autocompletado['camion_vto_rt']],
        ['Vto. PC:', datos_autocompletado['camion_vto_pc'], 'Vto. SOAP:', datos_autocompletado['camion_vto_soap'], 'Vto. TC8:', datos_autocompletado['camion_vto_tc8']],
    ]
    t3 = Table(camion_data, colWidths=[c_w]*6)
    t3.setStyle(TableStyle(base_style + [('FONTSIZE', (0,0), (-1,-1), 9)])) # Bajamos a 9 solo aquí para que no se amontone
    story.append(t3)

    # 4. SECCIÓN ESTANQUE
    story.append(Paragraph("ESTANQUE / REMOLQUE", header_label))
    est_data = [
        ['Marca:',  datos_autocompletado['remolque_marca'], 'Modelo:', datos_autocompletado['remolque_modelo'], 'Año:', datos_autocompletado['remolque_anio']],
        ['Patente:', datos_autocompletado['remolque_patente'], 'Cap. m³:', datos_autocompletado['remolque_capacidad'], 'Vto. RT:', 'N/A'],
        ['Vto. PC:', 'N/A', 'Vto. TC8:', 'N/A', 'F. Hermeticidad:', 'N/A'],
    ]
    t4 = Table(est_data, colWidths=[c_w]*6)
    t4.setStyle(TableStyle(base_style + [('FONTSIZE', (0,0), (-1,-1), 9)]))
    story.append(t4)

    # --- SALTO DE PÁGINA ---
    story.append(PageBreak())

    # --- PÁGINA 2 EN ADELANTE: CHECKLIST ---
    story.append(Paragraph("DETALLE DE ITEMS DE INSPECCIÓN", title_style))
    
    # Agrupar items por categoría
    items_por_categoria = {}
    for resultado in resultados_items:
        cat = resultado.item.categoria.nombre
        if cat not in items_por_categoria: items_por_categoria[cat] = []
        items_por_categoria[cat].append(resultado)

    for categoria, resultados in items_por_categoria.items():
        story.append(Paragraph(categoria.upper(), header_label))
        data = [['N°', 'Descripción', 'Estado', 'Observación']]
        for idx, res in enumerate(resultados, 1):
            data.append([str(idx), res.item.nombre, res.get_estado_display(), res.observacion or ''])
        
        # El checklist tiene letra 10 para máxima claridad
        t_check = Table(data, colWidths=[0.5*inch, 3.4*inch, 1.2*inch, 2.4*inch])
        t_check.setStyle(TableStyle([
            ['GRID', (0,0), (-1,-1), 0.5, colors.black],
            ['FONTSIZE', (0,0), (-1,-1), 10],
            ['BACKGROUND', (0,0), (-1,0), colors.lightgrey],
            ['FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'],
        ]))
        story.append(t_check)
        story.append(Spacer(1, 10))

    # Firmas
    story.append(Spacer(1, 40))
    firma_data = [
        ['_______________________', '_______________________'],
        [f'Firma: {inspeccion.responsable}', 'Firma: Representante ZMC'],
        ['Responsable Inspección', 'Control de Flota']
    ]
    t_firma = Table(firma_data, colWidths=[3.75*inch, 3.75*inch])
    t_firma.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTSIZE', (0,0), (-1,-1), 10)]))
    story.append(t_firma)

    doc.build(story)
    return ruta_pdf