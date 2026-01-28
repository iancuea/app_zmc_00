from django.db import models
from datetime import date
from django.core.exceptions import ValidationError
# Create your models here.

# Opciones de Base (Magallanes)
BASE_CHOICES = [
    ('SOMBRERO', 'Sombrero'),
    ('GREGORIO', 'Gregorio'),
    ('CULLEN', 'Cullen'),
    ('POSESION', 'Posesión'),
    ('PUNTA_ARENAS', 'Punta Arenas'),
]

# Estados Operativos (según tu imagen)
ESTADO_OPERATIVO_CHOICES = [
    ('OPERATIVO', 'Operativo'),
    ('EN_MANTENCION', 'En Mantención'),
    ('NO_OPERATIVO', 'No Operativo'),
    ('FUERA_DE_SERVICIO', 'Fuera de Servicio'),
]

class Empresa(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=20, unique=True)
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

#---------ENTIDADES-------

class Camion(models.Model):
    id_camion = models.AutoField(primary_key=True)
    patente = models.CharField(max_length=10, unique=True)
    vin = models.CharField(max_length=17, unique=True, blank=True, null=True)
    marca = models.CharField(max_length=50, blank=True, null=True)
    modelo = models.CharField(max_length=50, blank=True, null=True)
    anio = models.IntegerField(blank=True, null=True)

    tipo_camion = models.CharField(max_length=50)
    tipo_carga = models.CharField(max_length=30, blank=True, null=True)

    ROL_OPERATIVO_CHOICES = [
        ('TITULAR', 'Titular'),
        ('BACKUP', 'Backup'),
    ]
    rol_operativo = models.CharField(max_length=10, choices=ROL_OPERATIVO_CHOICES)

    capacidad_m3 = models.IntegerField()

    TALLER_CHOICES = [
        ('ZMC', 'ZMC'),
        ('KAUFMANN', 'Kaufmann'),
    ]
    taller_mantencion = models.CharField(max_length=10, choices=TALLER_CHOICES)

    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'camiones'

    def km_restantes(self):
        ultima = self.mantenciones.order_by('-fecha_mantencion').first()
        estado = getattr(self, 'estado_actual', None)

        if not ultima or not estado:
            return None

        if ultima.km_proxima_mantencion is None or estado.kilometraje is None:
            return None

        return ultima.km_proxima_mantencion - estado.kilometraje
    
    def estado_mantencion(self):
        km = self.km_restantes()

        if km is None:
            return {
                "codigo": "SIN_DATOS",
                "label": "SIN DATOS",
                "css": "estado-muted",
                "prioridad": 5,
            }

        if km <= 0:
            return {
                "codigo": "VENCIDA",
                "label": "VENCIDA",
                "css": "estado-danger",
                "prioridad": 1,
            }

        if km <= 1000:
            return {
                "codigo": "CRITICA",
                "label": "CRÍTICA",
                "css": "estado-warning",
                "prioridad": 2,
            }

        return {
            "codigo": "OK",
            "label": "OK",
            "css": "estado-ok",
            "prioridad": 3,
        }

    @property
    def asignacion_actual(self):
        """Retorna la asignación activa si existe, usando la tabla intermedia."""
        from .models import AsignacionTractoRemolque
        return AsignacionTractoRemolque.objects.filter(
            camion=self, 
            activo=True
        ).select_related('remolque').first()

    @property
    def tiene_remolque(self):
        """Verifica de forma rápida si tiene un remolque enganchado."""
        return self.asignacion_actual is not None

    def prioridad_mantencion(self):
        return self.estado_mantencion()["prioridad"]

    def __str__(self):
        return self.patente

class Conductor(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conductor"
        verbose_name_plural = "Conductores"

    def __str__(self):
        return f"{self.nombre} ({self.rut})" 

class Remolque(models.Model):
    # Opciones para el estado operativo
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('mantenimiento', 'En Mantención'),
        ('ruta', 'En Ruta'),
        ('baja', 'De Baja'),
    ]
    id_remolque = models.AutoField(primary_key=True, db_column='id_remolque')
    patente = models.CharField(max_length=20, unique=True, verbose_name="Patente")
    marca = models.CharField(max_length=100, blank=True, null=True)
    modelo = models.CharField(max_length=100, blank=True, null=True)
    anio = models.PositiveIntegerField(blank=True, null=True, verbose_name="Año")
    tipo_remolque = models.CharField(max_length=50, blank=True, null=True)
    capacidad_carga = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    n_ejes = models.PositiveIntegerField(default=2)
    
    # Este es el campo clave para tus mantenciones futuras
    kilometraje_acumulado = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00,
        help_text="Suma de kilómetros recorridos por los tractos asignados"
    )
    
    estado_operativo = models.CharField(
        max_length=50, 
        choices=ESTADO_CHOICES, 
        default='disponible'
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'remolques' # Forzamos el nombre de la tabla para que coincida con el SQL
        verbose_name = 'Remolque'
        verbose_name_plural = 'Remolques'

    def __str__(self):
        return f"{self.patente} - {self.tipo_remolque}"

class Mantencion(models.Model):
    # 1. Definir la llave primaria exacta
    id_mantencion = models.AutoField(
        primary_key=True, 
        db_column='id_mantencion'
    )

    # 2. Forzar el nombre de la columna para Camion
    camion = models.ForeignKey(
        'Camion', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        db_column='id_camion',  # <-- Esto arregla el error "no existe camion_id"
        related_name='mantenciones'
    )

    # 3. Forzar el nombre de la columna para Remolque (por si acaso)
    remolque = models.ForeignKey(
        'Remolque', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        db_column='id_remolque', # <-- Evita el mismo error con remolques
        related_name='mantenciones_remolque'
    )
    taller = models.CharField(max_length=10)
    fecha_mantencion = models.DateField()
    km_mantencion = models.IntegerField(blank=True, null=True)
    km_proxima_mantencion = models.IntegerField(blank=True, null=True)
    km_restantes = models.IntegerField(blank=True, null=True)
    dias_revision_tecnica = models.IntegerField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'mantenciones'

    @property
    def km_restantes_calculados(self):
        if self.km_proxima_mantencion is None or self.km_mantencion is None:
            return None
        return self.km_proxima_mantencion - self.km_mantencion

    def __str__(self):
        return f"{self.camion.patente} - {self.fecha_mantencion}"

#---------AUXILIARES-------

class AsignacionTractoRemolque(models.Model):
    # Relaciones
    id_asignacion = models.AutoField(
        primary_key=True, 
        db_column='id_asignacion'
    )
    camion = models.ForeignKey(
        'Camion', 
        on_delete=models.CASCADE, 
        db_column='id_camion'  # <-- Esto arregla el error de la columna que no existe
    )
    remolque = models.ForeignKey(
        'Remolque', 
        on_delete=models.CASCADE, 
        db_column='id_remolque' # <-- Esto también
    )
    
    # Datos de la asignación
    fecha_desde = models.DateTimeField(auto_now_add=True)
    fecha_hasta = models.DateTimeField(null=True, blank=True)
    
    # Muy importante para el cálculo de kms futuros
    km_inicio_camion = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Kilometraje del camión al momento de realizar el enganche"
    )
    
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el remolque está actualmente enganchado a este camión"
    )

    def clean(self):
        # Solo validamos si el usuario está intentando activar esta asignación
        if self.activo:
            # 1. Verificar si el CAMIÓN ya tiene otro remolque activo
            query_camion = AsignacionTractoRemolque.objects.filter(
                camion=self.camion, 
                activo=True
            )
            if self.pk: # Si estamos editando una existente, la excluimos de la búsqueda
                query_camion = query_camion.exclude(pk=self.pk)
            
            if query_camion.exists():
                raise ValidationError(
                    f"Error: El camión {self.camion.patente} ya tiene un remolque activo asignado."
                )

            # 2. Verificar si el REMOLQUE ya está enganchado a otro camión
            query_remolque = AsignacionTractoRemolque.objects.filter(
                remolque=self.remolque, 
                activo=True
            )
            if self.pk:
                query_remolque = query_remolque.exclude(pk=self.pk)

            if query_remolque.exists():
                raise ValidationError(
                    f"Error: El remolque {self.remolque.patente} ya está activo con otro camión."
                )
    def save(self, *args, **kwargs):
        # Forzamos la ejecución de clean() antes de guardar
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'asignacion_tracto_remolque'
        verbose_name = 'Asignación Tracto-Remolque'
        verbose_name_plural = 'Asignaciones Tracto-Remolque'

    def __str__(self):
        return f"{self.camion.patente} <-> {self.remolque.patente} ({self.fecha_desde.date()})"

#---------ESTADOS-------

class EstadoCamion(models.Model):
    id_estado = models.AutoField(primary_key=True)

    camion = models.OneToOneField(
        Camion,
        on_delete=models.CASCADE,
        db_column='id_camion',
        related_name='estado_actual'
    )

    conductor = models.ForeignKey(
        Conductor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_conductor',
        related_name='camiones_asignados'
    )

    kilometraje = models.IntegerField()
    estado_operativo = models.CharField(max_length=20,choices=ESTADO_OPERATIVO_CHOICES)

    base_actual = models.CharField(
        max_length=20,
        choices=BASE_CHOICES,
        default='PUNTA_ARENAS'
    )

    observacion = models.TextField(blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'estado_camion'

    def __str__(self):
        return f"{self.camion.patente} - {self.estado_operativo} - {self.base_actual}"

class EstadoRemolque(models.Model):
    id_estado = models.AutoField(primary_key=True, db_column='id_estado_remolque')
    remolque = models.OneToOneField( # OneToOne porque cada remolque tiene SOLO UN estado actual
        'Remolque', 
        on_delete=models.CASCADE, 
        db_column='id_remolque',
        related_name='estado_actual'
    )
    estado_operativo = models.CharField(
        max_length=20,
        choices=ESTADO_OPERATIVO_CHOICES, # Agregado
        default='OPERATIVO'
    )
    observacion = models.TextField(blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    @property
    def base_actual(self):
        # Buscamos la asignación donde este remolque esté activo
        asignacion = self.remolque.asignaciontractoremolque_set.filter(activo=True).first()
        
        if asignacion and asignacion.camion.estado_actual:
            # Retorna la base del camión usando el nombre "bonito" de BASE_CHOICES
            return asignacion.camion.estado_actual.get_base_actual_display()
        
        return "SIN ASIGNACIÓN"

    class Meta:
        db_table = 'estado_remolque'    

#---------HISTORIALES-------

class HistorialEstadoRemolque(models.Model):
    id_historial = models.AutoField(primary_key=True, db_column='id_historial')
    remolque = models.ForeignKey(
        'Remolque', 
        on_delete=models.CASCADE, 
        db_column='id_remolque'
    )
    kilometraje = models.DecimalField(max_digits=12, decimal_places=2)
    estado_operativo = models.CharField(
        max_length=20,
        choices=ESTADO_OPERATIVO_CHOICES # Agregado
    )
    descripcion_evente = models.TextField(db_column='descripcion_evente') # Manteniendo tu nombre de SQL
    fecha_evento = models.DateTimeField(auto_now_add=True, db_column='fecha_evento')

    class Meta:
        db_table = 'historial_estado_remolque'

class HistorialEstadoCamion(models.Model):
    id_historial = models.AutoField(primary_key=True)

    camion = models.ForeignKey(
        Camion,
        on_delete=models.CASCADE,
        db_column='id_camion',
        related_name='historial_estados'
    )

    kilometraje = models.IntegerField(blank=True, null=True)
    estado_operativo = models.CharField(
        max_length=20,
        choices=ESTADO_OPERATIVO_CHOICES # Agregado
    )
    id_conductor = models.IntegerField(blank=True, null=True)
    descripcion_evento = models.TextField(blank=True, null=True)
    fecha_evento = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'historial_estado_camion'

    def __str__(self):
        return f"{self.camion.patente} - {self.estado_operativo}"

#---------DOCUMENTOS-------

class DocumentoMantencion(models.Model):
    id_documento = models.AutoField(primary_key=True)

    mantencion = models.ForeignKey(
        Mantencion,
        on_delete=models.CASCADE,
        db_column='id_mantencion',
        related_name='documentos'
    )

    nombre_archivo = models.CharField(max_length=255)
    ruta_archivo = models.TextField()
    tipo_documento = models.CharField(max_length=50, blank=True, null=True)
    fecha_subida = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'documentos_mantencion'

    def __str__(self):
        return self.nombre_archivo
    
class DocumentacionGeneral(models.Model):
    # ID único (Django lo crea como Serial PK automáticamente)
    id_documento = models.AutoField(primary_key=True)
    
    # tipo_entidad: 'CAMION' o 'CONDUCTOR'
    ENTIDAD_CHOICES = [
        ('CAMION', 'Camión'),
        ('CONDUCTOR', 'Conductor'),
    ]
    tipo_entidad = models.CharField(max_length=10, choices=ENTIDAD_CHOICES)
    
    # id_referencia: El ID del camión o del conductor
    id_referencia = models.IntegerField(help_text="ID del camión o conductor según el tipo de entidad")
    
    # categoria
    CATEGORIA_CHOICES = [
        ('LICENCIA', 'Licencia de Conducir'),
        ('EXTINTOR', 'Extintor'),
        ('REVISION_TECNICA', 'Revisión Técnica'),
        ('SEGURO', 'Seguro / SOAP'),
        ('PERMISO_CIRCULACION', 'Permiso de Circulación'),
    ]
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES)
    
    # fecha_vencimiento
    fecha_vencimiento = models.DateField()
    
    # url_drive
    url_drive = models.URLField(max_length=500)

    class Meta:
        db_table = 'documentos_general'
        verbose_name = "Documento General"
        ordering = ['fecha_vencimiento']

    def __str__(self):
        return f"{self.tipo_entidad} ({self.id_referencia}) - {self.get_categoria_display()}"

    # Estado Calculado (Vigente, Próximo a vencer, Vencido)
    @property
    def estado(self):
        hoy = date.today()
        diferencia = (self.fecha_vencimiento - hoy).days
        if diferencia < 0:
            return "Vencido"
        elif diferencia <= 15:
            return "Próximo a vencer"
        return "Vigente"