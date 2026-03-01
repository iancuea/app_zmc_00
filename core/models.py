from django.db import models
from datetime import date
from django.core.exceptions import ValidationError
import os
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

def path_documentos_general(instance, filename):
    # Determinamos el ID real de la entidad vinculada
    # Usamos getattr por seguridad, pero como ya son FK, podemos acceder directo
    entidad_id = "sin_id"
    
    if instance.camion_id:
        entidad_id = instance.camion_id
    elif instance.remolque_id:
        entidad_id = instance.remolque_id
    elif instance.conductor_id:
        entidad_id = instance.conductor_id
    
    # Retorna la ruta: documentos/CAMION/10/archivo.pdf
    return f'documentos/{instance.tipo_entidad}/{entidad_id}/{filename}'

class Empresa(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=20, unique=True)
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

#---------ENTIDADES-------

class Contrato(models.Model):
    nombre = models.CharField(max_length=100)
    logo_cliente = models.ImageField(upload_to='logos/contratos/', null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'core_contrato' # Obligamos a usar el nombre exacto de la tabla

    def __str__(self):
        return self.nombre
    
class Camion(models.Model):
    id_camion = models.AutoField(primary_key=True)
    patente = models.CharField(max_length=10, unique=True)
    vin = models.CharField(max_length=17, unique=True, blank=True, null=True)
    marca = models.CharField(max_length=50, blank=True, null=True)
    modelo = models.CharField(max_length=50, blank=True, null=True)
    anio = models.IntegerField(blank=True, null=True)
    contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True)
    intervalo_mantencion = models.IntegerField(default=25000, help_text="KM entre mantenciones")

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
            """
            Nueva lógica: Busca la última inspección de la app 'mantenciones' 
            donde se renovó el aceite de motor.
            """
            # Accedemos a la relación 'inspecciones' definida en el ForeignKey de la nueva app
            ultima = self.inspecciones.filter(
                lubricantes__tipo_lubricante__icontains="MOTOR", 
                lubricantes__renovado=True
            ).order_by('-fecha_ingreso').first()

            estado = getattr(self, 'estado_actual', None)

            if not ultima or not estado:
                return None

            # Obtenemos el registro de lubricante específico de esa inspección
            lubricante = ultima.lubricantes.filter(tipo_lubricante__icontains="MOTOR").first()
            
            if not lubricante or not lubricante.proximo_cambio_km or not estado.kilometraje:
                return None

            # Retorna la resta entre la meta calculada y el GPS actual
            return lubricante.proximo_cambio_km - estado.kilometraje
    
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
        return self.asignaciontractoremolque_set.filter(activo=True).first()

    @property
    def tiene_remolque(self):
        return self.asignacion_actual is not None

    def prioridad_mantencion(self):
        return self.estado_mantencion()["prioridad"]

    def __str__(self):
        return self.patente if self.patente else "Camión sin patente"
    
class Conductor(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=20, unique=True)
    # Dejamos solo correo y celular como campos de contacto principales
    correo = models.EmailField(max_length=254, null=True, blank=True)
    celular = models.CharField(max_length=50, null=True, blank=True)
    
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    # Datos específicos del CSV
    contratista = models.CharField(max_length=100, null=True, blank=True)
    antiguedad = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    inicio_contrato = models.DateField(null=True, blank=True)
    
    # Ampliamos a 100 para evitar el error de "valor demasiado largo"
    clase_licencia = models.CharField(max_length=100, null=True, blank=True)
    
    # Para guardar la URL de la foto de AppSheet o local
    foto_url = models.TextField(null=True, blank=True)

    @property
    def nombre_corto(self):
        """Retorna 'Primer Nombre + Primer Apellido'"""
        partes = self.nombre.split()
        if len(partes) >= 3:
            # Si tiene 4 nombres (común en Chile), el índice 2 suele ser el primer apellido
            # Ejemplo: [0]Alejandro [1]Javier [2]Raín [3]Kogler -> Alejandro Raín
            return f"{partes[0]} {partes[2]}"
        elif len(partes) == 2:
            # Ejemplo: [0]Juan [1]Perez -> Juan Perez
            return f"{partes[0]} {partes[1]}"
        return self.nombre # Si es solo un nombre, lo devuelve tal cual

    class Meta:
        verbose_name = "Conductor"
        verbose_name_plural = "Conductores"
        # Asegúrate de que el db_table coincida con el nombre en tu SQL
        db_table = 'core_conductor'

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

class AsignacionPermanente(models.Model):
    camion = models.ForeignKey(Camion, on_delete=models.CASCADE, related_name='conductores_asignados')
    conductor = models.ForeignKey(Conductor, on_delete=models.CASCADE)
    TURNO_CHOICES = [
        ('TITULAR', 'Titular'),
        ('RELEVO', 'Relevo/Backup'),
    ]
    tipo_turno = models.CharField(max_length=20, choices=TURNO_CHOICES, blank=True, null=True)
    
    class Meta:
        db_table = 'core_asignacion_permanente'
        verbose_name = "Asignación de Conductor"
        # Esto permite que un conductor no se repita en el mismo camión
        unique_together = ('camion', 'conductor') 

    def __str__(self):
        return f"{self.camion.patente} -> {self.conductor.nombre}"

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
        return self.patente if self.patente else "Remolque sin patente"

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
        # 1. Si hay camión, mostramos su patente
        if self.camion:
            return f"🚜 {self.camion.patente} - {self.fecha_mantencion}"
        
        # 2. Si hay remolque, mostramos su patente
        if self.remolque:
            return f"🚛 {self.remolque.patente} - {self.fecha_mantencion}"
        
        # 3. Caso de emergencia (cuando estás creando el registro)
        return f"Nueva Mantención - {self.fecha_mantencion}"

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
    id_documento = models.AutoField(primary_key=True)
    
    ENTIDAD_CHOICES = [
        ('CAMION', 'Camión'),
        ('CONDUCTOR', 'Conductor'),
        ('REMOLQUE', 'Remolque'), 
    ]
    tipo_entidad = models.CharField(max_length=10, choices=ENTIDAD_CHOICES)
   # --- RELACIONES DIRECTAS (NUEVAS) ---
    camion = models.ForeignKey(
        'Camion', 
        on_delete=models.CASCADE, 
        db_column='id_camion', 
        null=True, 
        blank=True,
        related_name='documentos_general'
    )
    remolque = models.ForeignKey(
        'Remolque', 
        on_delete=models.CASCADE, 
        db_column='id_remolque', 
        null=True, 
        blank=True,
        related_name='documentos_general'
    )
    conductor = models.ForeignKey(
        'Conductor', 
        on_delete=models.CASCADE, 
        db_column='id_conductor', # Este apunta al id en core_conductor
        null=True, 
        blank=True,
        related_name='documentos_general'
    )

    CATEGORIA_CHOICES = [
        # --- DOCUMENTOS VEHICULARES ---
        ('PADRON', 'Padrón / Certificado Inscripción'),
        ('PERMISO_CIRCULACION', 'Permiso de Circulación'),
        ('SOAP', 'Seguro Obligatorio (SOAP)'),
        ('REVISION_TECNICA', 'Revisión Técnica'),
        ('TC8', 'Certificado TC8 (Gases)'),
        ('SEC' , 'Certificado SEC'),
        ('HERMETICIDAD', 'Prueba de Hermeticidad'),
        ('EXTINTOR', 'Certificado Carga de Extintor'),
        
        # --- SEGUROS Y TRANSPORTE ---
        ('SEGURO_CARGA', 'Seguro Transporte Terrestre (Carga)'),
        ('SEGURO_RC', 'Seguro Responsabilidad Civil'),
  
        
        # --- PERSONAL ---
        ('LICENCIA', 'Licencia de Conducir'),
        ('CONTRATO', 'Contrato de Trabajo'),
        ('EXAMEN_PREOCUPACIONAL', 'Examen Preocupacional'),
    ]
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    
    # Mantenemos url_drive por compatibilidad, pero la dejamos opcional
    url_drive = models.URLField(max_length=500, blank=True, null=True)

    # NUEVO CAMPO: Se mapea con archivo_path en la BD
    # upload_to llama a la función de arriba para crear las carpetas
    archivo = models.FileField(
        upload_to=path_documentos_general, 
        db_column='archivo_path', 
        null=True, 
        blank=True
    )

    class Meta:
        managed = False  # Mantén esto si manejas la tabla por fuera de las migraciones
        db_table = 'documentos_general'
        verbose_name = "Documento General"
        ordering = ['fecha_vencimiento']

    def __str__(self):
            # Buscamos qué entidad está vinculada para mostrarla en el nombre
            entidad = "Sin asignar"
            if self.camion:
                entidad = self.camion.patente
            elif self.remolque:
                entidad = self.remolque.patente
            elif self.conductor:
                entidad = self.conductor.nombre

            return f"{self.get_categoria_display()} - {entidad} ({self.tipo_entidad})"
    
    @property
    def estado(self):
        # Si no tiene fecha, asumimos que es un documento permanente
        if not self.fecha_vencimiento:
            return "Permanente"
        
        hoy = date.today()
        diferencia = (self.fecha_vencimiento - hoy).days
        if diferencia < 0:
            return "Vencido"
        elif diferencia <= 15:
            return "Próximo a vencer"
        return "Vigente"