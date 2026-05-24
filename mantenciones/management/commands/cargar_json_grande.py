import json
import os
import re
from django.core.management.base import BaseCommand
from mantenciones.models import ItemChecklist, CategoriaChecklist 
from core.models import ModeloVehiculo

class Command(BaseCommand):
    help = 'Carga pautas de servicios (individuales o en bloque) del Axor directo a PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument('json_path', type=str, help='Ruta al archivo JSON (individual o arreglo masivo)')

    def handle(self, *args, **options):
        path = options['json_path']
        
        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"❌ Error: El archivo no existe en la ruta: {path}"))
            return

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extraer estrictamente la estructura limpia del JSON con Regex
        match = re.search(r'(\{.*\}|\[.*\])', content, re.DOTALL)
        if not match:
            self.stdout.write(self.style.ERROR("❌ Error: No se encontró un formato JSON válido en el archivo."))
            return

        try:
            raw_data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"❌ Error de sintaxis en el JSON: {str(e)}"))
            return

        # FLEXIBILIDAD EN PRODUCCIÓN: Si viene un objeto único, lo metemos en una lista para procesarlo igual
        if isinstance(raw_data, dict):
            bloques_servicios = [raw_data]
        elif isinstance(raw_data, list):
            bloques_servicios = raw_data
        else:
            self.stdout.write(self.style.ERROR("❌ Error: El formato del JSON debe ser un objeto o una lista de objetos."))
            return

        total_tareas_cargadas = 0

        # Procesar cada bloque del documento (SM1, SM2, SM3...)
        for bloque in bloques_servicios:
            if 'modelo' not in bloque or 'items' not in bloque:
                continue

            # 1. Resolver el Camión Base por cada bloque
            modelo_obj, _ = ModeloVehiculo.objects.get_or_create(
                nombre=bloque['modelo'].strip(),
                marca=bloque['marca'].strip()
            )
            
            # Extraer el plan global de este bloque específico
            plan = str(bloque.get('nivel_servicio_global') or 'SM1').upper().strip()
            self.stdout.write(self.style.SUCCESS(f"\n🚚 [PRODUCCIÓN] Procesando bloque del plan: {plan} para {modelo_obj.marca} {modelo_obj.nombre}"))

            tareas_bloque = 0
            
            # 2. Iterar e inyectar las tareas de este plan a PostgreSQL
            for item in bloque.get('items', []):
                if not item or 'nombre' not in item:
                    continue

                # Obtener o crear dinámicamente el grupo del sistema (Categoría Padre)
                cat_raw = item.get('categoria_nombre', 'GENERAL')
                cat_obj, _ = CategoriaChecklist.objects.get_or_create(
                    nombre=str(cat_raw).upper().strip()
                )

                # Sanitización rigurosa de strings con escudo anti-None
                nombre_limpio = str(item.get('nombre') or '').strip()[:100]
                ref_wis = str(item.get('referencia_tecnica') or '').strip()[:50]
                cod_sap = str(item.get('codigo_sap') or '').strip()[:50] if item.get('codigo_sap') else None

                # update_or_create evita duplicar si re-corres el script por correcciones de taller
                ItemChecklist.objects.update_or_create(
                    nombre=nombre_limpio,
                    modelo=modelo_obj,
                    nivel_servicio=plan,  # Se le asigna el plan global que venía en la raíz de este bloque
                    defaults={
                        'categoria': cat_obj,
                        'es_critico': item.get('es_critico', False),
                        'tipo_respuesta': item.get('tipo_respuesta', 'ESCALA'),
                        'es_opcional': item.get('es_opcional', False),
                        'referencia_tecnica': ref_wis,
                        'codigo_sap': cod_sap
                    }
                )
                tareas_bloque += 1
                total_tareas_cargadas += 1

            self.stdout.write(self.style.SUCCESS(f"   ✅ Sincronizadas {tareas_bloque} tareas para {plan}."))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 ¡Golaço! Carga masiva finalizada. Se integraron {total_tareas_cargadas} tareas totales en PostgreSQL.\n"))