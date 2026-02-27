from django import forms
from .models import Inspeccion, ResultadoItem, RegistroDiario
from django.core.exceptions import ObjectDoesNotExist

class InspeccionForm(forms.ModelForm):
    """Formulario para crear inspecciones con filtrado dinámico de categorías"""
    
    class Meta:
        model = Inspeccion
        fields = ['tipo_inspeccion', 'vehiculo', 'remolque', 'km_registro', 'responsable', 'es_apto_operar', 'observaciones']        
        widgets = {
            'tipo_inspeccion': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'id': 'id_tipo_inspeccion'
            }),
            'vehiculo': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'id': 'id_vehiculo'
            }),
            'remolque': forms.Select(attrs={
                'class': 'form-select form-select-lg',
                'id': 'id_remolque'
            }),
            'km_registro': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg', 
                'placeholder': 'Ej: 423193',
                'id': 'id_km_registro'
            }),
            'responsable': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Nombre del Responsable',
                'id': 'id_responsable'
            }),
            'es_apto_operar': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_es_apto_operar'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Observaciones generales',
                'id': 'id_observaciones'
            }),
        }
        labels = {
            'tipo_inspeccion': 'Tipo de Inspección',
            'vehiculo': 'Patente Camión',
            'remolque': 'Patente Remolque (Auto-llenado)',
            'km_registro': 'Kilometraje Actual',
            'responsable': 'Responsable de Inspección',
            'es_apto_operar': '¿Apto para Operar?',
            'observaciones': 'Observaciones'
        }

    def clean_km_registro(self):
        km_ingresado = self.cleaned_data.get('km_registro')
        vehiculo = self.cleaned_data.get('vehiculo')

        if vehiculo and km_ingresado is not None:
            try:
                # Accedemos al kilometraje actual a través de la relación que definiste
                km_actual = vehiculo.estado_actual.kilometraje
            except (ObjectDoesNotExist, AttributeError):
                # Si el camión no tiene un 'estado_actual' creado todavía
                km_actual = 0

            # Validación: No puede ser menor al actual
            if km_ingresado < km_actual:
                raise forms.ValidationError(
                    f"No puedes ingresar un kilometraje menor al actual ({km_actual} km)."
                )

            # Validación: Salto sospechoso (más de 3000 km)
            diferencia = km_ingresado - km_actual
            if diferencia > 3000:
                raise forms.ValidationError(
                    f"El salto de kilometraje ({diferencia} km) es muy alto. Verifica si el dato es correcto."
                )
        
        return km_ingresado
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remolque no es requerido y se auto-llena
        self.fields['remolque'].required = False
        self.fields['remolque'].disabled = True  # No editable, auto-llenado