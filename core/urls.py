"""
core/urls.py
Rutas URL de la aplicación core para listados, detalles y APIs de camiones y remolques.
"""

from django.urls import path
from . import views
from .views import api_estado_camiones

app_name = 'core'

urlpatterns = [
    path('camiones/', views.camion_list, name='camion_list'),
    path('camiones/<int:pk>/', views.camion_detail, name='camion_detail'),
    path('api/camion/<int:camion_id>/', views.api_camion_detalle, name='api_camion_detalle'),
    path("api/camiones/estado/", api_estado_camiones, name="api_estado_camiones"),
    path('remolque/<int:pk>/', views.remolque_detail, name='remolque_detail'),
]
