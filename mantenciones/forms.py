from django import forms
from .models import Inspeccion, ResultadoItem

class InspeccionForm(forms.ModelForm):
    class Meta:
        model = Inspeccion
        fields = ['camion', 'remolque', 'kilometraje_unidad', 'responsable', 'observaciones']
        widgets = {
            # Widgets con clases de Bootstrap para que se vean bien en el celular
            'camion': forms.Select(attrs={'class': 'form-control form-control-lg'}),
            'kilometraje_unidad': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Ej: 423193'}),
            'responsable': forms.TextInput(attrs={'class': 'form-control', 'value': 'Tomás Rocamora'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# Formulario para los ítems B-R-M
class ResultadoItemForm(forms.ModelForm):
    class Meta:
        model = ResultadoItem
        fields = ['estado', 'observacion', 'foto']
        widgets = {
            'estado': forms.RadioSelect(attrs={'class': 'btn-group'}), # Para botones grandes
        }