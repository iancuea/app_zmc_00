from django.db import models
from django.conf import settings
from core.models import Camion, Remolque

class Inspeccion(models.Model):
    """
    Representa el informe completo (cabecera). 
    Equivale al 'Informe Mantención' que hoy manejas en PDF.
    """
    id_inspeccion = models.AutoField(primary_key=True)
    
    # Datos de la Unidad (Fierros)
    camion = models.ForeignKey(Camion, on_delete=models.CASCADE, related_name='inspecciones', db_column='id_camion')
    remolque = models.ForeignKey(Remolque, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspecciones', db_column='id_remolque')
    
    # Datos Operativos del Informe [cite: 6, 11]
    kilometraje_unidad = models.IntegerField() # Los 423.193 km del informe [cite: 11]
    fecha_ingreso = models.DateTimeField() # [cite: 6]
    fecha_salida = models.DateTimeField(null=True, blank=True) # [cite: 6]
    
    # Responsable (Tomás Rocamora) [cite: 8]
    responsable = models.CharField(max_length=100)
    
    # Resultados Finales [cite: 32]
    observaciones = models.TextField(blank=True, null=True)
    apto_operacion = models.BooleanField(default=True) # "La unidad se encuentra en condiciones de incorporarse" [cite: 32]
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mantencion_inspeccion'
        verbose_name_plural = "Inspecciones"

    def __str__(self):
        return f"Inspección {self.id_inspeccion} - {self.camion.patente}"

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
    Sección especial para los aceites renovados[cite: 24].
    """
    inspeccion = models.ForeignKey(Inspeccion, on_delete=models.CASCADE, related_name='lubricantes')
    tipo_lubricante = models.CharField(max_length=100) # ej: "ACEITE MOTOR" [cite: 24]
    renovado = models.BooleanField(default=False) # [cite: 24]
    proximo_cambio_km = models.IntegerField(null=True, blank=True) #
