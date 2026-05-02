import pdfplumber
import re
from django.core.management.base import BaseCommand
from mantenciones.models import Componente
from core.models import ModeloVehiculo

class Command(BaseCommand):
    help = 'Lector flexible: Busca litros en cualquier columna de la fila'

    def add_arguments(self, parser):
        parser.add_argument('pdf_path', type=str, help='Ruta al archivo PDF')

    def handle(self, *args, **options):
        path = options['pdf_path']
        self.stdout.write(self.style.SUCCESS(f'Iniciando Lector Flexible: {path}'))

        PROHIBIDAS = ['IMPORTANTE', 'UTILIZAR ESTA HOJA', 'CLIENTE:', 'N° CHASIS', 'ORDEN DE TRABAJO', 'KILOMETRAJE', 'HOJA REFERENCIAL']

        with pdfplumber.open(path) as pdf:
            # Identificar modelo
            first_page = pdf.pages[0].extract_text()
            modelo_nombre = "Axor" if "AXOR" in first_page.upper() else "Modelo Generico"
            modelo, _ = ModeloVehiculo.objects.get_or_create(nombre=modelo_nombre, marca="Mercedes-Benz")

            componentes_creados = 0
            nombre_acumulado = ""

            for page_index in [1, 2]: # Páginas de lubricantes
                page = pdf.pages[page_index]
                # Probamos con "lines" tanto vertical como horizontal para Kaufmann
                table = page.extract_table({
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                })
                
                if not table: continue

                for row in table:
                    # Quitamos celdas None y limpiamos texto
                    row = [str(c).strip() if c else "" for c in row]
                    
                    # Unir toda la fila en un solo texto para buscar los litros[cite: 2]
                    fila_completa = " ".join(row)
                    
                    # Saltamos basura
                    if any(p in fila_completa.upper() for p in PROHIBIDAS) or len(fila_completa) < 5:
                        continue

                    # BUSCAR LITROS: Buscamos un número decimal (ej: 39,0 o 11.5)[cite: 2]
                    # Buscamos específicamente en lo que NO es el nombre del componente
                    litros_match = re.search(r'(\d+[,\.]\d+)', " ".join(row[1:]))
                    
                    if not litros_match:
                        # Si no hay números, es que el nombre sigue abajo
                        nombre_acumulado += " " + row[0]
                        continue
                    else:
                        # Si hay un número, procesamos la fila
                        nombre_final = (nombre_acumulado + " " + row[0]).strip()
                        nombre_acumulado = ""
                        
                        litros = float(litros_match.group(1).replace(',', '.'))
                        # La norma suele estar después de los litros (en las últimas columnas)[cite: 2]
                        norma = row[-2] if len(row) > 3 else ""

                        comp_obj, created = Componente.objects.update_or_create(
                            nombre=nombre_final[:250],
                            modelo=modelo,
                            defaults={
                                'categoria': self.asignar_categoria(nombre_final),
                                'capacidad_fluido': litros,
                                'especificacion_fluido': norma[:250]
                            }
                        )
                        if created:
                            componentes_creados += 1
                            self.stdout.write(f"  [+] {nombre_final[:30]}... | {litros}L")

        self.stdout.write(self.style.SUCCESS(f'Carga finalizada: {componentes_creados} componentes.'))

    def asignar_categoria(self, nombre):
        n = nombre.upper()
        if "MOTOR" in n: return "MOTOR"
        if "CAJA" in n or "POWERSHIFT" in n: return "TRANSMISION"
        if "EJE" in n or "HD" in n or "HL" in n: return "DIFERENCIAL"
        return "CHASIS"