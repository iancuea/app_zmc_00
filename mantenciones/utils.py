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
        'fecha_inspeccion': timezone.now().strftime('%d/%m/%Y %H:%M'),
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


def generar_pdf_inspeccion(inspeccion, resultados_items, datos_autocompletado):
    """
    Genera un PDF de inspección con el formato mostrado en las imágenes
    
    Args:
        inspeccion: Objeto Inspeccion
        resultados_items: QuerySet de ResultadoItem
        datos_autocompletado: Diccionario con datos pre-llenados
    
    Returns:
        path: Ruta del archivo PDF generado
    """
    
    # Crear directorio si no existe
    tipo_insp = inspeccion.get_tipo_inspeccion_display().lower()
    directorio = f'media/reportes_diarios/{tipo_insp}/'
    os.makedirs(directorio, exist_ok=True)
    
    # Nombre del archivo
    fecha_str = timezone.now().strftime('%Y%m%d_%H%M%S')
    patente = inspeccion.vehiculo.patente
    nombre_pdf = f'reporte_{fecha_str}_{patente}.pdf'
    ruta_pdf = os.path.join(directorio, nombre_pdf)
    
    # Crear documento PDF
    doc = SimpleDocTemplate(ruta_pdf, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.black,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    # --- ENCABEZADO CON LOGO ---
    story.append(Paragraph("ZMC TRANSPORTES - ENAP", title_style))
    story.append(Paragraph(f"INSPECCIÓN {inspeccion.get_tipo_inspeccion_display().upper()}", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # --- SECCIÓN INFORMACIÓN ---
    story.append(Paragraph("INFORMACIÓN", header_style))
    info_data = [
        ['Fecha Inspección:', datos_autocompletado['fecha_inspeccion'], 'Lugar Inspección:', datos_autocompletado['lugar_inspeccion']],
        ['Contratista:', datos_autocompletado['contratista'], 'Contrato:', datos_autocompletado['contrato']],
    ]
    info_table = Table(info_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.15*inch))
    
    # --- SECCIÓN CONDUCTOR ---
    story.append(Paragraph("CONDUCTOR", header_style))
    conductor_data = [
        ['Nombre:', datos_autocompletado['conductor_nombre'], 'Antigüedad:', datos_autocompletado['conductor_antiguedad']],
        ['Fecha Control:', datos_autocompletado['fecha_control'], '¿Apto para Trabajar?:', 'SI' if inspeccion.es_apto_operar else 'NO'],
    ]
    conductor_table = Table(conductor_data, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
    conductor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(conductor_table)
    story.append(Spacer(1, 0.15*inch))
    
    # --- SECCIÓN CAMIÓN ---
    story.append(Paragraph("CAMIÓN", header_style))
    camion_data = [
        ['Marca:', datos_autocompletado['camion_marca'], 'Modelo:', datos_autocompletado['camion_modelo'], 'Año:', str(datos_autocompletado['camion_anio'])],
        ['Patente:', datos_autocompletado['camion_patente'], 'Odómetro:', str(inspeccion.km_registro), 'Vto. RT:', datos_autocompletado['camion_vto_rt']],
        ['Vto. PC:', datos_autocompletado['camion_vto_pc'], 'Vto. SOAP:', datos_autocompletado['camion_vto_soap'], 'Vto. TC8:', datos_autocompletado['camion_vto_tc8']],
    ]
    camion_table = Table(camion_data, colWidths=[1.3*inch, 1.7*inch, 1.3*inch, 1.7*inch, 1.3*inch, 1.7*inch])
    camion_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(camion_table)
    story.append(Spacer(1, 0.15*inch))
    
    # --- SECCIÓN ESTANQUE (si tiene remolque) ---
    if datos_autocompletado['tiene_remolque']:
        story.append(Paragraph("ESTANQUE / REMOLQUE", header_style))
        estanque_data = [
            ['Marca:', datos_autocompletado['remolque_marca'], 'Modelo:', datos_autocompletado['remolque_modelo'], 'Año:', str(datos_autocompletado['remolque_anio'])],
            ['Patente:', datos_autocompletado['remolque_patente'], 'Cap. m³:', datos_autocompletado['remolque_capacidad'], 'Vto. RT:', datos_autocompletado['remolque_vto_rt']],
            ['Vto. PC:', datos_autocompletado['remolque_vto_pc'], 'Vto. SOAP:', datos_autocompletado['remolque_vto_soap'], 'Vto. TC8:', datos_autocompletado['remolque_vto_tc8']],
        ]
        estanque_table = Table(estanque_data, colWidths=[1.3*inch, 1.7*inch, 1.3*inch, 1.7*inch, 1.3*inch, 1.7*inch])
        estanque_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(estanque_table)
        story.append(Spacer(1, 0.15*inch))
    
    # --- SECCIÓN CHECKLIST ---
    story.append(Paragraph("ITEMS DE INSPECCIÓN", header_style))
    
    # Agrupar items por categoría
    items_por_categoria = {}
    for resultado in resultados_items:
        categoria = resultado.item.categoria.nombre
        if categoria not in items_por_categoria:
            items_por_categoria[categoria] = []
        items_por_categoria[categoria].append(resultado)
    
    # Crear tabla para cada categoría
    for categoria, resultados in items_por_categoria.items():
        story.append(Paragraph(f"{categoria}", ParagraphStyle(
            'SubHeader',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.black,
            spaceAfter=4,
            fontName='Helvetica-Bold'
        )))
        
        checklist_data = [['N°', 'Descripción', 'Respuesta', 'Observación']]
        for idx, resultado in enumerate(resultados, 1):
            respuesta_display = resultado.get_estado_display() if hasattr(resultado, 'get_estado_display') else resultado.estado
            checklist_data.append([
                str(idx),
                resultado.item.nombre,
                respuesta_display,
                resultado.observacion or ''
            ])
        
        checklist_table = Table(checklist_data, colWidths=[0.4*inch, 3.2*inch, 1*inch, 1.4*inch])
        checklist_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(checklist_table)
        story.append(Spacer(1, 0.1*inch))
    
    # --- OBSERVACIONES GENERALES ---
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("OBSERVACIONES GENERALES", header_style))
    obs_box = Table([
        [inspeccion.observaciones or '']
    ], colWidths=[7.5*inch])
    obs_box.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 40),  # Espacio para firma
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(obs_box)
    
    # --- FIRMAS ---
    story.append(Spacer(1, 0.3*inch))
    firma_data = [
        ['_____________________', '_____________________'],
        ['Firma Responsable', 'Firma Dueño o Representante'],
    ]
    firma_table = Table(firma_data, colWidths=[3.75*inch, 3.75*inch])
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(firma_table)
    
    # Construir PDF
    doc.build(story)
    
    return ruta_pdf