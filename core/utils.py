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
    
    # 1. Identificar si es Camión o Remolque
    es_camion = hasattr(entidad, 'id_camion')
    
    # 2. LÓGICA MECÁNICA: Prioridad absoluta a la tabla Mantencion
    if es_camion:
        ultima_m = entidad.mantenciones.all().first()
        km_actual = entidad.estado_actual.kilometraje if entidad.estado_actual else 0
        intervalo = entidad.intervalo_mantencion  # Sacamos el dato del modelo Camion
    else:
        ultima_m = entidad.mantenciones_remolque.all().first()
        km_actual = float(getattr(entidad, 'kilometraje_acumulado', 0))
        intervalo = 0 # O el intervalo que definas para remolques

    if ultima_m:
        # SI EL CAMPO MANUAL TIENE DATO, USA ESE (Prioridad manual)
        if ultima_m.km_proxima_mantencion:
            km_restantes = ultima_m.km_proxima_mantencion - km_actual
        # SI ESTÁ VACÍO, CALCULA AUTOMÁTICAMENTE: (KM Salida Taller + Intervalo Camión)
        elif ultima_m.km_mantencion:
            meta_automatica = ultima_m.km_mantencion + intervalo
            km_restantes = meta_automatica - km_actual

    # Evaluar semáforo mecánico
    if km_restantes is not None:
        if km_restantes <= 0:
            peor_estado = "VENCIDA"
            motivos.append(f"Mecánica Vencida ({int(km_restantes)} km)")
        elif km_restantes <= 1000:
            if peor_estado == "OK": peor_estado = "CRITICA"
            motivos.append(f"Mecánica Crítica ({int(km_restantes)} km)")

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
        "motivos": motivos
    }