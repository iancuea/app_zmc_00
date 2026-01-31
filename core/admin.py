from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Empresa,
    Camion,
    Remolque, # Nuevo
    AsignacionTractoRemolque, # Nuevo
    Mantencion,
    EstadoCamion,
    HistorialEstadoCamion,
    DocumentoMantencion,
    Conductor,
    DocumentacionGeneral,
    HistorialEstadoRemolque,
    EstadoRemolque
)

admin.site.register(Empresa)

# --- INLINES ---

class AsignacionInline(admin.TabularInline):
    model = AsignacionTractoRemolque
    extra = 1
    fields = ('remolque', 'km_inicio_camion', 'activo', 'fecha_desde', 'fecha_hasta')
    readonly_fields = ('fecha_desde',)

class MantencionInline(admin.TabularInline):
    model = Mantencion
    extra = 0
    # Agregamos remolque para que se vea en el listado del camión si aplica
    fields = ('fecha_mantencion', 'taller', 'remolque', 'km_proxima_mantencion')

class HistorialEstadoInline(admin.TabularInline):
    model = HistorialEstadoCamion
    extra = 0
    readonly_fields = ('fecha_evento',)

class DocumentoMantencionInline(admin.TabularInline):
    model = DocumentoMantencion
    extra = 0

class HistorialEstadoRemolqueInline(admin.TabularInline):
    model = HistorialEstadoRemolque
    extra = 0
    readonly_fields = ('fecha_evento',)

# --- CONFIGURACIONES PRINCIPALES ---

@admin.register(Camion)
class CamionAdmin(admin.ModelAdmin):
    search_fields = ['patente']
    list_display = (
        'patente',
        'activo',
        'rol_operativo',
        'km_restantes',
        'estado_actual_display',
        'remolque_actual' # Agregamos una columna para ver el remolque enganchado
    )
    list_filter = ('activo', 'rol_operativo')
    search_fields = ('patente',)
    # Agregamos AsignacionInline para enganchar/desenganchar remolques desde aquí
    inlines = [AsignacionInline, MantencionInline, HistorialEstadoInline]

    def estado_actual_display(self, obj):
        return getattr(obj.estado_actual, 'estado_operativo', 'SIN ESTADO')
    
    def remolque_actual(self, obj):
        asignacion = obj.asignaciontractoremolque_set.filter(activo=True).first()
        return asignacion.remolque.patente if asignacion else "Sin Remolque"

    estado_actual_display.short_description = 'Estado actual'
    remolque_actual.short_description = 'Remolque Activo'

@admin.register(Remolque)
class RemolqueAdmin(admin.ModelAdmin):
    search_fields = ['patente']
    list_display = ('patente', 'tipo_remolque', 'estado_actual_display', 'activo')
    inlines = [AsignacionInline, HistorialEstadoRemolqueInline] # Verás sus conductores y su historial

    def estado_actual_display(self, obj):
        return getattr(obj.estado_actual, 'estado_operativo', 'SIN ESTADO')
    estado_actual_display.short_description = 'Estado'

@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    search_fields = ['patente']
    list_display = ('nombre', 'rut', 'activo')
    search_fields = ('nombre', 'rut')

@admin.register(AsignacionTractoRemolque)
class AsignacionTractoRemolqueAdmin(admin.ModelAdmin):
    list_display = ('camion', 'remolque', 'fecha_desde', 'activo')

@admin.register(Mantencion)
class MantencionAdmin(admin.ModelAdmin):
    list_display = ('id_mantencion', 'get_unidad', 'fecha_mantencion', 'taller', 'km_proxima_mantencion')
    list_filter = ('taller', 'fecha_mantencion')
    # Ayuda a que los selects no sean lentos si tienes muchos camiones
    raw_id_fields = ('camion', 'remolque') 
    inlines = [DocumentoMantencionInline]

    def get_unidad(self, obj):
        # Usamos getattr para evitar el AttributeError si obj.camion es None
        camion = getattr(obj, 'camion', None)
        remolque = getattr(obj, 'remolque', None)

        if camion:
            return format_html('🚜 <b>{}</b>', camion.patente)
        if remolque:
            return format_html('🚛 <b>{}</b>', remolque.patente)
        
        return "Nueva Mantención"

    get_unidad.short_description = 'Unidad'

@admin.register(EstadoCamion)
class EstadoCamionAdmin(admin.ModelAdmin):
    list_display = ('camion', 'estado_operativo', 'kilometraje', 'fecha_actualizacion', 'conductor')
    list_filter = ('estado_operativo',)

@admin.register(EstadoRemolque)
class EstadoRemolqueAdmin(admin.ModelAdmin):
    list_display = ('remolque', 'estado_operativo', 'get_base_actual', 'fecha_actualizacion')
    # Importante: agrégala a readonly_fields para que no intente guardarla
    readonly_fields = ('get_base_actual', 'fecha_actualizacion')
    
    # Define los campos que se verán al editar para que no aparezca base_actual como input
    fields = ('remolque', 'estado_operativo', 'get_base_actual', 'observacion')

    def get_base_actual(self, obj):
        return obj.base_actual
    get_base_actual.short_description = 'Ubicación (Heredada)'

@admin.register(DocumentoMantencion)
class DocumentoMantencionAdmin(admin.ModelAdmin):
    list_display = ('mantencion', 'nombre_archivo', 'tipo_documento', 'fecha_subida')

@admin.register(DocumentacionGeneral)
class DocumentacionGeneralAdmin(admin.ModelAdmin):
    # 1. Quitamos 'get_entidad_nombre' (que usaba id_referencia) y ponemos 'get_vinculo'
    list_display = ('id_documento', 'tipo_entidad', 'get_vinculo', 'categoria', 'fecha_vencimiento', 'estado', 'ver_pdf')
    list_filter = ('tipo_entidad', 'categoria')
    list_display_links = ('id_documento', 'tipo_entidad')
    
    # 2. IMPORTANTE: El buscador ahora debe apuntar a campos que existan. 
    # Podemos buscar por patente de camión o nombre de conductor directamente:
    search_fields = ('camion__patente', 'remolque__patente', 'conductor__nombre', 'categoria')
    
    # 3. Autocompletado para que no pida IDs de memoria
    autocomplete_fields = ['camion', 'remolque', 'conductor']

    # 4. Organización del formulario
    fieldsets = (
        ('Información del Documento', {
            'fields': ('tipo_entidad', 'categoria', 'fecha_vencimiento', 'archivo', 'url_drive')
        }),
        ('Relación con Equipo o Personal', {
            'fields': ('camion', 'remolque', 'conductor'),
            'description': 'Selecciona solo el campo que corresponda al tipo de entidad elegido arriba.'
        }),
    )

    def get_vinculo(self, obj):
        """Muestra la patente o nombre real sin usar id_referencia"""
        if obj.camion:
            return format_html('🚜 <strong>{}</strong>', obj.camion.patente)
        if obj.remolque:
            return format_html('🚛 <strong>{}</strong>', obj.remolque.patente)
        if obj.conductor:
            return format_html('👤 <strong>{}</strong>', obj.conductor.nombre)
        return format_html('<span style="color: #999;">Sin asignar</span>')
    
    get_vinculo.short_description = 'Equipo / Personal'

    def ver_pdf(self, obj):
        """Link directo al archivo almacenado"""
        if obj.archivo:
            return format_html('<a href="{}" target="_blank" style="color: #264b5d; font-weight: bold;">📄 Ver PDF</a>', obj.archivo.url)
        return "—"
    ver_pdf.short_description = 'Archivo'
