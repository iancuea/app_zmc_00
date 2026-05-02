"""
mantenciones/admin.py
Configuración del panel de administración para inspecciones, categorías, items y resultados.
"""

from django.contrib import admin
from .models import (
    Inspeccion, CategoriaChecklist, ItemChecklist, 
    ResultadoItem, RegistroLubricantes,RegistroDiario,CronogramaPlan,Componente, Repuesto, KitComponente, InsumoUtilizado
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

@admin.register(Componente)
class ComponenteAdmin(admin.ModelAdmin):
    # Mostramos los datos clave que extrajimos del PDF
    list_display = ('nombre', 'categoria', 'capacidad_fluido', 'especificacion_fluido', 'modelo')
    # Filtros laterales para navegar rápido entre motores, cajas o diferenciales
    list_filter = ('categoria', 'modelo')
    search_fields = ('nombre', 'especificacion_fluido')
    ordering = ('modelo', 'categoria')

@admin.register(Repuesto)
class RepuestoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_zmc', 'tipo', 'unidad_medida', 'stock_minimo')
    list_filter = ('tipo',)
    search_fields = ('nombre', 'codigo_zmc')

@admin.register(KitComponente)
class KitComponenteAdmin(admin.ModelAdmin):
    # Esto te permite ver qué repuestos pide cada plan (SM1, SM2, etc.)
    list_display = ('plan_asociado', 'componente', 'repuesto', 'cantidad_necesaria')
    list_filter = ('plan_asociado', 'componente__modelo')
    # Buscador para encontrar qué kits usan un repuesto específico
    search_fields = ('componente__nombre', 'repuesto__nombre')

@admin.register(InsumoUtilizado)
class InsumoUtilizadoAdmin(admin.ModelAdmin):
    list_display = ('inspeccion', 'repuesto', 'cantidad_usada')
    list_filter = ('repuesto__tipo',)
    date_hierarchy = 'inspeccion__fecha_ingreso'