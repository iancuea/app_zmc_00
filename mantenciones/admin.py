from django.contrib import admin

from django.contrib import admin
from .models import (
    Inspeccion, CategoriaChecklist, ItemChecklist, 
    ResultadoItem, RegistroLubricantes,RegistroDiario
)

# Esto permite editar los ítems directamente dentro de la categoría
class ItemChecklistInline(admin.TabularInline):
    model = ItemChecklist
    extra = 1

@admin.register(CategoriaChecklist)
class CategoriaChecklistAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden')
    inlines = [ItemChecklistInline]

# Esto permite ver los resultados del B-R-M dentro de la Inspección
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
    list_display = ('id_inspeccion', 'vehiculo', 'km_registro', 'tipo_inspeccion', 'es_apto_operar')
    list_filter = ('tipo_inspeccion', 'es_apto_operar', 'vehiculo')
    search_fields = ('vehiculo__patente',)

admin.site.register(ItemChecklist)

@admin.register(RegistroDiario)
class RegistroDiarioAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'fecha', 'km_actual', 'revisado_por', 'es_apto')
    list_filter = ('es_apto', 'fecha')