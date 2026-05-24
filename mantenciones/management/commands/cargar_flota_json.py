import json
import os
import re
from django.core.management.base import BaseCommand
from mantenciones.models import Componente 
from core.models import ModeloVehiculo

class Command(BaseCommand):
    help = 'Carga las capacidades de fluidos con auto-detección dinámica de campos en PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument('json_path', type=str, help='Ruta al archivo JSON de fluidos')

    def handle(self, *args, **options):
        path = options['json_path']
        
        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"❌ Error: El archivo no existe en: {path}"))
            return

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        match = re.search(r'(\{.*\}|\[.*\])', content, re.DOTALL)
        if not match:
            self.stdout.write(self.style.ERROR("❌ Error: Estructura JSON no encontrada."))
            return

        try:
            raw_data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"❌ Error de sintaxis: {str(e)}"))
            return

        # 🔍 ESCANEO INTELIGENTE: Leemos las columnas reales de tu tabla Componente
        campos_reales = [f.name for f in Componente._meta.fields]
        
        # Mapeamos dinámicamente el campo de la capacidad en litros
        campo_capacidad = None
        for c in ['capacidad_litros', 'capacidad', 'litros', 'volumen']:
            if c in campos_reales:
                campo_capacidad = c
                break
                
        # Mapeamos dinámicamente el campo del tipo de aceite
        campo_lubricante = None
        for l in ['tipo_lubricante', 'lubricante', 'tipo_aceite', 'fluido']:
            if l in campos_reales:
                campo_lubricante = l
                break

        # Función interna para inyectar la data adaptándose a tus columnas
        def procesar_y_subir(comp_data, modelo_obj):
            defaults = {}
            if campo_capacidad:
                # Convertimos a flotante por seguridad
                defaults[campo_capacidad] = float(comp_data.get('capacidad_litros') or 0.0)
            if campo_lubricante:
                defaults[campo_lubricante] = str(comp_data.get('tipo_lubricante') or '').strip()[:150]

            Componente.objects.update_or_create(
                nombre=str(comp_data.get('nombre') or '').strip()[:100],
                modelo=modelo_obj,
                defaults=defaults
            )

        componentes_cargados = 0

        # CASO 1: Estructura de bloques (Formato Freightliner de Haiku)
        if isinstance(raw_data, dict) and 'componentes' in raw_data:
            marca_camion = raw_data.get('marca', '').strip()
            modelo_camion = raw_data.get('modelo', '').strip()
            
            modelo_obj, _ = ModeloVehiculo.objects.get_or_create(
                nombre=modelo_camion,
                marca=marca_camion
            )
            self.stdout.write(self.style.SUCCESS(f"\n🚚 [PRODUCCIÓN] Sincronizando componentes de: {modelo_obj.marca} {modelo_obj.nombre}"))

            for comp in raw_data.get('componentes', []):
                if not comp or 'nombre' not in comp:
                    continue
                procesar_y_subir(comp, modelo_obj)
                componentes_cargados += 1

        # CASO 2: Estructura plana (Formato antiguo)
        elif isinstance(raw_data, list):
            for item in raw_data:
                if not item or 'modelo' not in item or 'nombre' not in item:
                    continue
                
                marca_camion = item.get('marca', '').strip()
                modelo_camion = item.get('modelo', '').strip()
                
                modelo_obj, _ = ModeloVehiculo.objects.get_or_create(
                    nombre=modelo_camion,
                    marca=marca_camion
                )
                
                procesar_y_subir(item, modelo_obj)
                componentes_cargados += 1
        else:
            self.stdout.write(self.style.ERROR("❌ Error: Estructura de JSON no soportada."))
            return

        self.stdout.write(self.style.SUCCESS(f"   ✅ Éxito: Se integraron {componentes_cargados} componentes físicos en PostgreSQL de forma dinámica."))
        self.stdout.write(self.style.SUCCESS("🎉 Sincronización del maestro de fluidos completada.\n"))