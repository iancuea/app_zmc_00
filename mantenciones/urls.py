from django.urls import path
from . import views

app_name = 'mantenciones'

urlpatterns = [
    path('nueva/', views.crear_inspeccion, name='crear_inspeccion'),
]