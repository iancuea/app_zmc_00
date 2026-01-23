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
    hoy = date.today()
    dias = (fecha_vencimiento - hoy).days

    if dias < 0:
        return "VENCIDO", f"Documento vencido hace {-dias} días"
    elif dias <= 7:
        return "CRITICO", f"Documento vence en {dias} días"
    elif dias <= 15:
        return "PROXIMO", f"Documento vence en {dias} días"
    return "OK", None
