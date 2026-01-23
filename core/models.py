from django.db import models
from datetime import date
# Create your models here.


class Empresa(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=20, unique=True)
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class Camion(models.Model):
    id_camion = models.AutoField(primary_key=True)
    patente = models.CharField(max_length=10, unique=True)
    patente_remolque = models.CharField(max_length=10, blank=True, null=True)
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

    def prioridad_mantencion(self):
        return self.estado_mantencion()["prioridad"]

    def __str__(self):
        return self.patente

class Mantencion(models.Model):
    id_mantencion = models.AutoField(primary_key=True)

    camion = models.ForeignKey(
        Camion,
        on_delete=models.CASCADE,
        db_column='id_camion',
        related_name='mantenciones'
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
    estado_operativo = models.CharField(max_length=20)
    observacion = models.TextField(blank=True, null=True)
    fecha_actualizacion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'estado_camion'

    def __str__(self):
        return f"{self.camion.patente} - {self.estado_operativo}"

class HistorialEstadoCamion(models.Model):
    id_historial = models.AutoField(primary_key=True)

    camion = models.ForeignKey(
        Camion,
        on_delete=models.CASCADE,
        db_column='id_camion',
        related_name='historial_estados'
    )

    kilometraje = models.IntegerField(blank=True, null=True)
    estado_operativo = models.CharField(max_length=20)
    id_conductor = models.IntegerField(blank=True, null=True)
    descripcion_evento = models.TextField(blank=True, null=True)
    fecha_evento = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'historial_estado_camion'

    def __str__(self):
        return f"{self.camion.patente} - {self.estado_operativo}"

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