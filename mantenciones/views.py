import json
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from .forms import InspeccionForm
from .models import CategoriaChecklist, ItemChecklist, ResultadoItem, RegistroLubricantes

def crear_inspeccion(request):
    if request.method == 'POST':
        form = InspeccionForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # Usamos una transacción para que se guarde TODO o NADA
                with transaction.atomic():
                    # 1. Guardamos la cabecera (Inspección)
                    inspeccion = form.save(commit=False)
                    inspeccion.fecha_ingreso = timezone.now()
                    inspeccion.save()

                    # 2. Procesamos el Checklist (JSON enviado desde el JS)
                    checklist_raw = request.POST.get('checklist_json')
                    if checklist_raw:
                        checklist_data = json.loads(checklist_raw)
                        for data in checklist_data:
                            item = ItemChecklist.objects.get(id=data['id'])
                            ResultadoItem.objects.create(
                                inspeccion=inspeccion,
                                item=item,
                                estado=data['estado']
                            )

                    # 3. Procesamos los Lubricantes (Actualización de Semáforo)
                    # El JS envía 'true' o 'false' como string
                    aceite_renovado = request.POST.get('aceite_motor_renovado') == 'true'
                    
                    if aceite_renovado:
                        # Al crear este registro, el save() de RegistroLubricantes 
                        # calculará los +25.000 km automáticamente.
                        RegistroLubricantes.objects.create(
                            inspeccion=inspeccion,
                            tipo_lubricante="ACEITE MOTOR",
                            renovado=True
                        )

                messages.success(request, "¡Inspección guardada y semáforo actualizado!")
                return redirect('camion_list') # O la ruta de tu dashboard

            except Exception as e:
                messages.error(request, f"Error crítico al guardar: {e}")
                print(f"Error en inspección: {e}")
        else:
            messages.error(request, "El formulario tiene errores. Revisa los datos.")
    
    else:
        # GET: Cargamos el formulario limpio
        form = InspeccionForm()

    # Siempre pasamos las categorías para armar el checklist en el HTML
    categorias = CategoriaChecklist.objects.all().order_by('orden')
    
    return render(request, 'mantenciones/crear_inspeccion.html', {
        'form': form,
        'categorias': categorias
    })