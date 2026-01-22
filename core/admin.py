from django.contrib import admin
from .models import (
    Empresa,
    Camion,
    Mantencion,
    EstadoCamion,
    HistorialEstadoCamion,
    DocumentoMantencion
)

admin.site.register(Empresa)

class MantencionInline(admin.TabularInline):
    model = Mantencion
    extra = 0


class HistorialEstadoInline(admin.TabularInline):
    model = HistorialEstadoCamion
    extra = 0
    readonly_fields = ('fecha_evento',)


class DocumentoMantencionInline(admin.TabularInline):
    model = DocumentoMantencion
    extra = 0

@admin.register(Camion)
class CamionAdmin(admin.ModelAdmin):
    list_display = (
        'patente',
        'activo',
        'rol_operativo',
        'taller_mantencion',
        'km_restantes',
        'estado_actual_display'
    )

    list_filter = ('activo', 'rol_operativo', 'taller_mantencion')
    search_fields = ('patente', 'vin')
    inlines = [MantencionInline, HistorialEstadoInline]

    def estado_actual_display(self, obj):
        return getattr(obj.estado_actual, 'estado_operativo', 'SIN ESTADO')

    estado_actual_display.short_description = 'Estado actual'


@admin.register(EstadoCamion)
class EstadoCamionAdmin(admin.ModelAdmin):
    list_display = ('camion', 'estado_operativo', 'kilometraje', 'fecha_actualizacion')
    list_filter = ('estado_operativo',)


@admin.register(Mantencion)
class MantencionAdmin(admin.ModelAdmin):
    list_display = ('camion', 'fecha_mantencion', 'taller', 'km_proxima_mantencion')
    inlines = [DocumentoMantencionInline]


@admin.register(DocumentoMantencion)
class DocumentoMantencionAdmin(admin.ModelAdmin):
    list_display = ('mantencion', 'nombre_archivo', 'tipo_documento', 'fecha_subida')

