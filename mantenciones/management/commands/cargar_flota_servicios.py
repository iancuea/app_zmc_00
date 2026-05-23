import json
import os
import re
from django.core.management.base import BaseCommand
from mantenciones.models import ItemChecklist, CategoriaChecklist 
from core.models import ModeloVehiculo

class Command(BaseCommand):
    help = 'Carga las hojas secuenciales de servicios (SM1, SM2, SM3) del Axor directo a PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument('json_path', type=str, help='Ruta al archivo JSON intermedio de servicio')

    def handle(self, *args, **options):
        path = options['json_path']
        
        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"❌ Error: El archivo no existe en la ruta: {path}"))
            return

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extraer estrictamente la estructura del JSON con Regex
        match = re.search(r'(\{.*\})', content, re.DOTALL)
        if not match:
            self.stdout.write(self.style.ERROR("❌ Error: No se encontró un formato JSON válido en el archivo."))
            return

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"❌ Error de sintaxis en el JSON: {str(e)}"))
            return

        # 1. Resolver el Camión Base
        modelo_obj, _ = ModeloVehiculo.objects.get_or_create(
            nombre=data['modelo'].strip(),
            marca=data['marca'].strip()
        )
        
        plan = data.get('nivel_servicio_global', 'SM1').upper().strip()
        self.stdout.write(self.style.SUCCESS(f"\n🚚 [PRODUCCIÓN] Cargando pauta ejecutable del plan: {plan}"))
        self.stdout.write(self.style.SUCCESS(f"📦 Flota Destino: {modelo_obj.marca} {modelo_obj.nombre}"))

        tareas_cargadas = 0
        
        # 2. Iterar e inyectar tareas a PostgreSQL
        for item in data.get('items', []):
            if not item or 'nombre' not in item:
                continue

            # Obtener o crear dinámicamente el grupo del sistema (Categoría Padre)
            cat_raw = item.get('categoria_nombre', 'GENERAL')
            cat_obj, _ = CategoriaChecklist.objects.get_or_create(
                nombre=str(cat_raw).upper().strip()
            )

            # Sanitización rigurosa de longitudes de campos según tu modelo
            nombre_limpio = str(item.get('nombre') or '').strip()[:100]
            ref_wis = str(item.get('referencia_tecnica') or '').strip()[:50]
            cod_sap = str(item.get('codigo_sap') or '').strip()[:50] if item.get('codigo_sap') else None

            # update_or_create previene duplicidad si re-corres el script por correcciones del taller
            ItemChecklist.objects.update_or_create(
                nombre=nombre_limpio,
                modelo=modelo_obj,
                nivel_servicio=plan, # Queda tageado estrictamente con el plan del documento (SM1, SM2...)
                referencia_tecnica=ref_wis, # Aquí vive el código WIS crítico de Mercedes
                defaults={
                    'categoria': cat_obj,
                    'es_critico': item.get('es_critico', False),
                    'tipo_respuesta': item.get('tipo_respuesta', 'ESCALA'),
                    'es_opcional': item.get('es_opcional', False),
                    'codigo_sap': cod_sap
                }
            )
            tareas_cargadas += 1

        self.stdout.write(self.style.SUCCESS(f"   ✅ Éxito: Se integraron {tareas_cargadas} tareas secuenciales a la pauta de inspección."))
        self.stdout.write(self.style.SUCCESS("🎉 Sincronización con la base de datos de producción finalizada.\n"))