"""
core/design_tokens.py
Fuente única de verdad para la paleta ZMC.
Usar en correos HTML, lógica Python y cualquier valor de color dinámico.
Sincronizar con core/static/core/css/tokens.css si se modifica algo.
"""

class Colors:
    # Paleta principal
    PRIMARY        = "#0E305D"   # Azul Industrial Corporativo
    SECONDARY      = "#F3C613"   # Amarillo Vial

    # Estados operacionales
    SUCCESS        = "#2ECC71"   # Verde operativo
    ERROR          = "#E74C3C"   # Rojo crítico

    # Fondos (UI oscura)
    BG_DARK        = "#121212"
    BG_SURFACE     = "#1E1E1E"

    # Texto sobre fondo oscuro
    TEXT_PRIMARY   = "#E8ECF0"
    TEXT_SECONDARY = "#9BA3AE"
    TEXT_MUTED     = "#555F6B"

    # Texto sobre fondo claro (formularios, tablas)
    TEXT_ON_LIGHT  = "#1A2733"

    # Derivados para bordes y fondos sutiles
    PRIMARY_TINT   = "#F0F4FA"   # Azul muy claro para fondos de tabla
    PRIMARY_BORDER = "#B0C4DE"   # Azul suave para bordes
    ERROR_TINT     = "#FDF0F0"
    SUCCESS_TINT   = "#F0FDF4"
    SECONDARY_TINT = "#FFFDF0"


class StatusColors:
    """Semántica operacional de flota."""
    VENCIDO      = Colors.ERROR      # Mantención vencida
    PROXIMO      = Colors.SECONDARY  # Próxima ≤ 30 días
    PROGRAMADO   = Colors.PRIMARY    # Dentro del horizonte
    OPERATIVO    = Colors.SUCCESS    # Camión operativo
    FUERA_LINEA  = Colors.ERROR      # Camión fuera de línea

    # Texto sobre cada fondo de badge
    TEXT_ON_VENCIDO    = "#FFFFFF"
    TEXT_ON_PROXIMO    = Colors.PRIMARY   # Texto oscuro sobre amarillo
    TEXT_ON_PROGRAMADO = "#FFFFFF"
    TEXT_ON_OPERATIVO  = "#FFFFFF"


class Typography:
    FAMILY = "'Inter', system-ui, -apple-system, sans-serif"
    FAMILY_MONO = "'JetBrains Mono', 'Courier New', monospace"