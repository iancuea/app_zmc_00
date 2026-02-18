from django.urls import path
from . import views

app_name = 'mantenciones'

urlpatterns = [
    path('nueva/', views.crear_inspeccion, name='crear_inspeccion'),
    path('api/datos-autocompletado/<int:camion_id>/', views.api_datos_autocompletado, name='api_datos_autocompletado'),
    path('api/categorias/<str:tipo_inspeccion>/', views.api_categorias_por_tipo, name='api_categorias_por_tipo'),
    path('api/remolque-asignado/<int:camion_id>/', views.api_remolque_asignado, name='api_remolque_asignado'),
]