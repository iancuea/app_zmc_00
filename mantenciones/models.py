from django.db import models
from django.conf import settings
from core.models import Camion, Remolque
from django.contrib.auth.models import User

class Inspeccion(models.Model):
    # Tipos de inspección para el filtro lógico
    TIPO_CHOICES = [
        ('DIARIO', 'Checklist Diario'),
        ('MANTENCION', 'Mantención Técnica'),
    ]
    tipo_inspeccion = models.CharField(max_length=20, choices=TIPO_CHOICES, default='DIARIO')

    # Identificador único
    id_inspeccion = models.AutoField(primary_key=True)
    
    # Datos de la Unidad (Fierros)
    # Usamos 'vehiculo' como nombre principal para evitar líos
    vehiculo = models.ForeignKey(Camion, on_delete=models.CASCADE, related_name='inspecciones', db_column='id_camion')
    remolque = models.ForeignKey(Remolque, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspecciones', db_column='id_remolque')
    
    # Datos Operativos
    km_registro = models.PositiveIntegerField() # Equivale a kilometraje_unidad
    fecha_ingreso = models.DateTimeField(auto_now_add=True) # Se auto-rellena al crear
    fecha_salida = models.DateTimeField(null=True, blank=True) #
    
    # Responsable y Observaciones
    responsable = models.CharField(max_length=100, default="Tomás Rocamora")
    observaciones = models.TextField(blank=True, null=True)
    
    # Estados de Control
    es_apto_operar = models.BooleanField(default=True, verbose_name="¿Apto para operar?")
    renovó_aceite = models.BooleanField(default=False, verbose_name="¿Renovó Aceite Motor?")

    ajuste_db = models.BooleanField(default=True)

    class Meta:
        db_table = 'mantencion_inspeccion'
        verbose_name_plural = "Inspecciones"

    def __str__(self):
        return f"{self.tipo_inspeccion} - {self.vehiculo.patente} ({self.fecha_ingreso.strftime('%d/%m/%Y')})"

class CategoriaChecklist(models.Model):
    """
    Categorías del informe: 'CABINA', 'SISTEMA HIDRÁULICO', 'SEGURIDAD', etc.
    """
    nombre = models.CharField(max_length=100) # ej: "KIT DE SEGURIDAD" [cite: 19]
    orden = models.IntegerField(default=0) # Para que aparezcan en orden en el celular

    def __str__(self):
        return self.nombre

class ItemChecklist(models.Model):
    """
    Los ítems específicos: 'Extintores', 'Bombas', 'Plumillas'.
    """
    categoria = models.ForeignKey(CategoriaChecklist, on_delete=models.CASCADE, related_name='items')
    nombre = models.CharField(max_length=100) # ej: "EXTINTORES" [cite: 21]
    es_critico = models.BooleanField(default=False) # Si está Malo, el camión no sale

    def __str__(self):
        return f"{self.categoria.nombre} - {self.nombre}"

class ResultadoItem(models.Model):
    """
    Aquí guardamos el B-R-M de cada ítem en una inspección específica.
    """
    ESTADO_CHOICES = [
        ('B', 'Bueno'),
        ('R', 'Regular'),
        ('M', 'Malo'),
    ]
    
    inspeccion = models.ForeignKey(Inspeccion, on_delete=models.CASCADE, related_name='resultados')
    item = models.ForeignKey(ItemChecklist, on_delete=models.CASCADE)
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default='B') # [cite: 13, 14, 15]
    observacion = models.CharField(max_length=255, blank=True, null=True)
    foto = models.ImageField(upload_to='inspecciones/evidencia/', null=True, blank=True)

    class Meta:
        unique_together = ('inspeccion', 'item')

class RegistroLubricantes(models.Model):
    """
    Sección especial para los aceites renovados.
    """
    inspeccion = models.ForeignKey(Inspeccion, on_delete=models.CASCADE, related_name='lubricantes')
    tipo_lubricante = models.CharField(max_length=100) # ej: "ACEITE MOTOR"
    renovado = models.BooleanField(default=False)
    proximo_cambio_km = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Si se renovó el aceite y no se puso el próximo km a mano
        if self.renovado and not self.proximo_cambio_km:
            # CORRECCIÓN: Usamos 'km_registro' que es el nombre real en tu modelo Inspeccion
            km_entrada = self.inspeccion.km_registro
            
            # CORRECCIÓN: Usamos 'vehiculo' que es el nombre real en tu modelo Inspeccion
            # Asegúrate de que el modelo Camion tenga el campo 'intervalo_mantencion'
            intervalo = self.inspeccion.vehiculo.intervalo_mantencion
            
            self.proximo_cambio_km = km_entrada + intervalo
            
        super().save(*args, **kwargs)

class RegistroDiario(models.Model):
    # Relaciones básicas
    vehiculo = models.ForeignKey(Camion, on_delete=models.CASCADE, related_name='checklists_diarios')
    revisado_por = models.CharField(max_length=100, help_text="Nombre de quien realiza la inspección")    
    fecha = models.DateTimeField(auto_now_add=True)

    # Datos de control
    km_actual = models.PositiveIntegerField(verbose_name="Kilometraje actual")
    horometro = models.PositiveIntegerField(null=True, blank=True, verbose_name="Horómetro (opcional)")

    # Filtros Lógicos de Estado
    es_apto = models.BooleanField(default=True, verbose_name="¿Apto para operar?")
    nivel_combustible = models.CharField(max_length=20, choices=[
        ('bajo', 'Bajo'), ('medio', 'Medio'), ('full', 'Full')
    ], default='full')

    # Almacenamiento flexible del Checklist
    # Guardamos las respuestas como un JSON para no crear 50 columnas de Sí/No
    # Ej: {"luces": true, "frenos": false, "limpieza": true}
    check_datos = models.JSONField(default=dict, help_text="Resultados del checklist diario")

    # Observaciones críticas
    novedades = models.TextField(blank=True, null=True, verbose_name="Novedades o fallas detectadas")
    
    class Meta:
        ordering = ['-fecha']
        verbose_name = "Registro Diario"
        verbose_name_plural = "Registros Diarios"

    def __str__(self):
        estado = "APTO" if self.es_apto else "NO APTO"
        return f"{self.vehiculo.patente} - {self.fecha.strftime('%d/%m/%Y')} - {estado}"