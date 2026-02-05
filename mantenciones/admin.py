from django.contrib import admin

from django.contrib import admin
from .models import (
    Inspeccion, CategoriaChecklist, ItemChecklist, 
    ResultadoItem, RegistroLubricantes
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
    extra = 0

@admin.register(Inspeccion)
class InspeccionAdmin(admin.ModelAdmin):
    list_display = ('id_inspeccion', 'camion', 'responsable', 'fecha_ingreso', 'apto_operacion')
    list_filter = ('apto_operacion', 'camion', 'fecha_ingreso')
    search_fields = ('camion__patente', 'responsable')
    inlines = [ResultadoItemInline, RegistroLubricantesInline]

admin.site.register(ItemChecklist)