from datetime import date

# Prioridad numérica (más alto = más urgente)
ESTADO_PRIORIDAD = {
    "VENCIDO": 4,
    "CRITICO": 3,
    "PROXIMO": 2,
    "OK": 1,
}

def estado_mantencion(km_actual, km_proxima):
    if km_actual is None or km_proxima is None:
        return "OK", None

    restantes = km_proxima - km_actual

    if restantes < 0:
        return "VENCIDO", f"Mantención vencida por {-restantes} km"
    elif restantes <= 3000:
        return "CRITICO", f"Mantención vence en {restantes} km"
    elif restantes <= 10000:
        return "PROXIMO", f"Mantención vence en {restantes} km"
    return "OK", None


def estado_documento(fecha_vencimiento):
    # 1. El Guardia: Si no hay fecha, el documento es eterno y está OK
    if fecha_vencimiento is None:
        return "OK", None

    hoy = date.today()
    # 2. Ahora sí, calculamos los días con seguridad
    dias = (fecha_vencimiento - hoy).days

    if dias < 0:
        return "VENCIDO", f"Vencido hace {-dias} días"
    elif dias <= 7:
        return "CRITICO", f"Vence en {dias} días"
    elif dias <= 15:
        return "PROXIMO", f"Vence en {dias} días"
    
    return "OK", None