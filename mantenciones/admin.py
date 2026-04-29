"""
mantenciones/admin.py
Configuración del panel de administración para inspecciones, categorías, items y resultados.
"""

from django.contrib import admin
from .models import (
    Inspeccion, CategoriaChecklist, ItemChecklist, 
    ResultadoItem, RegistroLubricantes,RegistroDiario,CronogramaPlan
)

# Esto permite editar los ítems directamente dentro de la categoría
"""Inline para editar ItemChecklist dentro de CategoriaChecklistAdmin"""
class ItemChecklistInline(admin.TabularInline):
    model = ItemChecklist
    extra = 1

@admin.register(CategoriaChecklist)
class CategoriaChecklistAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden')
    inlines = [ItemChecklistInline]

# Esto permite ver los resultados del B-R-M dentro de la Inspección
"""Inline para mostrar ResultadoItem dentro de InspeccionAdmin"""
class ResultadoItemInline(admin.TabularInline):
    model = ResultadoItem
    extra = 0
    can_delete = False

class RegistroLubricantesInline(admin.TabularInline):
    model = RegistroLubricantes
    extra = 1

@admin.register(Inspeccion)
class InspeccionAdmin(admin.ModelAdmin):
    # Usamos los nombres reales de tu modelo
    list_display = ('id_inspeccion', 'camion', 'km_registro', 'tipo_inspeccion', 'es_apto_operar')
    list_filter = ('tipo_inspeccion', 'es_apto_operar', 'camion')
    search_fields = ('camion__patente',)

@admin.register(RegistroDiario)
class RegistroDiarioAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'fecha', 'km_actual', 'revisado_por', 'es_apto')
    list_filter = ('es_apto', 'fecha')

@admin.register(ItemChecklist)
class ItemChecklistAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nivel_servicio', 'modelo', 'referencia_tecnica', 'codigo_sap')
    list_filter = ('nivel_servicio', 'modelo', 'categoria')
    search_fields = ('nombre', 'codigo_sap')

@admin.register(CronogramaPlan)
class CronogramaPlanAdmin(admin.ModelAdmin):
    list_display = ('modelo', 'posicion_ciclo', 'intervalo_teorico', 'paquetes_json')
    list_filter = ('modelo',)