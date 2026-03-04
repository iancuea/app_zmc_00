from datetime import date

# Prioridades: Menor número = Mayor Urgencia (para ordenar)
# 1: VENCIDA/O, 2: CRITICA/O, 3: OK
PRIORIDAD_MAP = {
    "VENCIDA": 1, "VENCIDO": 1,
    "CRITICA": 2, "CRITICO": 2,
    "OK": 3, "SIN_DATOS": 4
}

# core/utils.py
from datetime import date

PRIORIDAD_MAP = {"VENCIDA": 1, "CRITICA": 2, "OK": 3, "SIN_DATOS": 4}
def evaluar_salud_entidad(entidad):
    peor_estado = "OK"
    motivos = []
    km_restantes = None
    meta_km = 0  # <--- Iniciamos la variable para el HTML
    
    # 1. Identificar si es Camión o Remolque
    es_camion = hasattr(entidad, 'id_camion')
    
    # 2. LÓGICA MECÁNICA: Prioridad absoluta a la tabla Mantencion
    if es_camion:
        ultima_m = entidad.mantenciones.exclude(tipo_mantencion='DIARIA').order_by('-fecha_mantencion').first()  
        km_actual = entidad.estado_actual.kilometraje if entidad.estado_actual else 0
        
        # --- NUEVA REGLA DINÁMICA DE INTERVALO ---
        from core.models import AsignacionTractoRemolque
        tiene_remolque = AsignacionTractoRemolque.objects.filter(camion=entidad, activo=True).exists()
        
        if tiene_remolque:
            intervalo = 40000  # Tracto con remolque asociado
        else:
            intervalo = 25000  # Camión solo o rígido
        # -----------------------------------------
        
    else:
        # Lógica para Remolques
        ultima_m = entidad.mantenciones_remolque.exclude(tipo_mantencion='DIARIA').order_by('-fecha_mantencion').first()
        km_actual = float(getattr(entidad, 'kilometraje_acumulado', 0))
        intervalo = 25000 # O el que definas para los tanques

    if ultima_m:
        # Prioridad 1: Valor manual ingresado en el Admin
        if ultima_m.km_proxima_mantencion:
            meta_km = ultima_m.km_proxima_mantencion
        # Prioridad 2: Cálculo automático (KM salida taller + intervalo)
        elif ultima_m.km_mantencion:
            meta_km = ultima_m.km_mantencion + intervalo
        
        if meta_km > 0:
            km_restantes = meta_km - km_actual

    # Evaluar semáforo mecánico
    if km_restantes is not None:
        if km_restantes <= 0:
            peor_estado = "VENCIDA"
            motivos.append(f"Mecánica Vencida ({int(km_restantes)} km)")
        elif km_restantes <= 1000:
            if peor_estado == "OK": peor_estado = "CRITICA"
            motivos.append(f"Mecánica Crítica ({int(km_restantes)} km)")
    # Si no hay mantención en tabla Mantenciones, intentamos con la de aceite (tu lógica actual)
    elif es_camion and hasattr(entidad, 'km_restantes'):
        km_restantes = entidad.km_restantes()
        
    # 3. LÓGICA DOCUMENTACIÓN
    docs = entidad.documentos_general.all()
    hoy = date.today()
    for doc in docs:
        if not doc.fecha_vencimiento: continue
        dias = (doc.fecha_vencimiento - hoy).days
        if dias < 0:
            peor_estado = "VENCIDA"
            motivos.append(f"{doc.get_categoria_display()}: Vencido")
        elif dias <= 15:
            if peor_estado == "OK": peor_estado = "CRITICA"
            motivos.append(f"{doc.get_categoria_display()}: Vence en {dias} días")

    return {
        "codigo": peor_estado,
        "css": f"estado-{peor_estado.lower()}",
        "label": peor_estado,
        "prioridad": PRIORIDAD_MAP.get(peor_estado, 3),
        "motivos": motivos,
        "proxima_km": meta_km,  # <--- PASAMOS EL DATO CALCULADO AL DICCIONARIO
        "km_restantes": km_restantes
    }