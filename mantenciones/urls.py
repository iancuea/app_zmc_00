"""
mantenciones/urls.py
Rutas URL para crear inspecciones, APIs de autocompletado de datos y proyecciones de Carta Gantt.
"""

from django.urls import path
from . import views

app_name = 'mantenciones'

urlpatterns = [
    path('nueva/', views.crear_inspeccion, name='crear_inspeccion'),
    path('api/datos-autocompletado/<int:camion_id>/', views.api_datos_autocompletado, name='api_datos_autocompletado'),
    path('api/categorias/<str:tipo_inspeccion>/', views.api_categorias_por_tipo, name='api_categorias_por_tipo'),
    path('api/remolque-asignado/<int:camion_id>/', views.api_remolque_asignado, name='api_remolque_asignado'),
    # 🚀 Nueva ruta predictiva para la Carta Gantt 2027
    path('api/gantt-proyeccion/', views.api_gantt_proyeccion, name='api_gantt_proyeccion'),
    path('gantt-panel/', views.vista_gantt_mvp, name='vista_gantt_mvp'),
]