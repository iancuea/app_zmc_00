import json
import os
from django.core.management.base import BaseCommand
from mantenciones.models import Componente
from core.models import ModeloVehiculo

class Command(BaseCommand):
    help = 'Carga componentes técnicos de vehículos desde un JSON estructurado por Claude'

    def add_arguments(self, parser):
        # Permite pasar la ruta del JSON como argumento en la terminal
        parser.add_argument('json_path', type=str, help='Ruta al archivo JSON generado por la IA')

    def handle(self, *args, **options):
        path = options['json_path']
        
        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"❌ Error: El archivo no existe en la ruta: {path}"))
            return

        with open(path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR("❌ Error: El archivo no contiene un JSON válido. Revisa que no tenga texto extra afuera de los corchetes."))
                return

        # Procesamos el archivo mapeando los datos al modelo relacional de app_zmc
        for item in data:
            # 1. Traemos o creamos el modelo del camión (Ej: Axor)
            modelo_obj, created_modelo = ModeloVehiculo.objects.get_or_create(
                nombre=item['modelo'].strip(),
                marca=item['marca'].strip()
            )
            
            status_mod = "[NUEVO]" if created_modelo else "[EXISTENTE]"
            self.stdout.write(self.style.SUCCESS(f"🚚 {status_mod} Procesando modelo: {modelo_obj.marca} {modelo_obj.nombre}"))
            
            componentes_cargados = 0

            # 2. Iteramos e inyectamos los componentes validados
            for comp in item['componentes']:
                # update_or_create evita duplicados si vuelves a correr el script por correcciones
                comp_obj, created_comp = Componente.objects.update_or_create(
                    nombre=comp['nombre'].strip()[:250],
                    modelo=modelo_obj,
                    defaults={
                        'categoria': comp['categoria'].upper().strip(),
                        'capacidad_fluido': comp['capacidad_fluido'],
                        'especificacion_fluido': comp['especificacion_fluido'].strip()[:250] if comp['especificacion_fluido'] else ""
                    }
                )
                if created_comp:
                    componentes_cargados += 1

            self.stdout.write(self.style.SUCCESS(f"   ✅ Éxito: Se guardaron {componentes_cargados} componentes nuevos de manera limpia en PostgreSQL.\n"))