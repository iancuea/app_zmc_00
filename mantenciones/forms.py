from django import forms
from .models import Inspeccion, ResultadoItem

class InspeccionForm(forms.ModelForm):
    class Meta:
        model = Inspeccion
        # Ajustamos los nombres a los que definiste en el modelo
        fields = ['tipo_inspeccion', 'vehiculo', 'km_registro', 'es_apto_operar', 'renovó_aceite']
        
        widgets = {
            'tipo_inspeccion': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'vehiculo': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'km_registro': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg', 
                'placeholder': 'Ej: 423193'
            }),
            # Agregamos los checkboxes por si los necesitas en el form
            'es_apto_operar': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'renovó_aceite': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
# Formulario para los ítems B-R-M
class ResultadoItemForm(forms.ModelForm):
    class Meta:
        model = ResultadoItem
        fields = ['estado', 'observacion', 'foto']
        widgets = {
            'estado': forms.RadioSelect(attrs={'class': 'btn-group'}), # Para botones grandes
        }