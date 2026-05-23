import json
import os
import re
from django.core.management.base import BaseCommand
from mantenciones.models import ItemChecklist, Repuesto, CategoriaChecklist 
from core.models import ModeloVehiculo

class Command(BaseCommand):
    help = 'Carga el programa maestro de tareas y repuestos desde el JSON de Claude'

    def add_arguments(self, parser):
        parser.add_argument('json_path', type=str, help='Ruta al archivo JSON intermedio')

    def handle(self, *args, **options):
        path = options['json_path']
        
        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"❌ Error: No existe el archivo en: {path}"))
            return

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Limpieza por Regex para aislar el objeto JSON
        match = re.search(r'(\{.*\})', content, re.DOTALL)
        if not match:
            self.stdout.write(self.style.ERROR("❌ Error: Estructura JSON no encontrada."))
            return

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"❌ Error al procesar la sintaxis del JSON: {str(e)}"))
            return

        # 1. Obtener o crear el camión base
        modelo_obj, _ = ModeloVehiculo.objects.get_or_create(
            nombre=data['modelo'].strip(),
            marca=data['marca'].strip()
        )
        self.stdout.write(self.style.SUCCESS(f"\n🚚 Sincronizando pauta de taller para: {modelo_obj.marca} {modelo_obj.nombre}"))

        # 2. Cargar Ítems del Checklist
        tareas_contadas = 0
        for item in data.get('items_checklist', []):
            if not item or 'nombre' not in item:
                continue

            # Resolvemos dinámicamente la categoría padre
            categoria_raw = item.get('categoria_nombre', 'GENERAL')
            cat_obj, _ = CategoriaChecklist.objects.get_or_create(
                nombre=str(categoria_raw).upper().strip()
            )

            # ESCUDO ANTI-NONE: Si el plan o nombre vienen como null, usamos un string seguro
            nombre_limpio = str(item.get('nombre') or '').strip()[:100]
            plan_limpio = str(item.get('nivel_servicio') or 'SM1').upper().strip()

            ItemChecklist.objects.update_or_create(
                nombre=nombre_limpio,
                modelo=modelo_obj,
                nivel_servicio=plan_limpio,
                defaults={
                    'categoria': cat_obj,
                    'es_critico': item.get('es_critico', False),
                    'tipo_respuesta': item.get('tipo_respuesta', 'ESCALA'),
                    'es_opcional': item.get('es_opcional', False),
                    'referencia_tecnica': str(item.get('referencia_tecnica') or '')[:50],
                    'codigo_sap': str(item.get('codigo_sap') or '')[:50]  # Arreglado aquí con un casteo seguro a String
                }
            )
            tareas_contadas += 1
        self.stdout.write(self.style.SUCCESS(f"   📊 Checklist: {tareas_contadas} tareas de inspección cargadas/actualizadas."))

        # 3. Cargar Repuestos de Bodega (Códigos SAP)
        repuestos_contados = 0
        for rep in data.get('repuestos', []):
            codigo_raw = rep.get('codigo_zmc')
            if not codigo_raw:
                continue
                
            Repuesto.objects.update_or_create(
                codigo_zmc=str(codigo_raw).strip()[:50],
                defaults={
                    'nombre': str(rep.get('nombre') or '').strip()[:150],
                    'tipo': rep.get('tipo', 'OTRO'),
                    'unidad_medida': 'UNIDAD',
                    'stock_minimo': 5
                }
            )
            repuestos_contados += 1
        self.stdout.write(self.style.SUCCESS(f"   📦 Bodega: {repuestos_contados} repuestos codificados de manera limpia."))
        
        self.stdout.write(self.style.SUCCESS("\n🎉 ¡Carga completada con éxito sin errores de datos!"))