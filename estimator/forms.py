from django import forms
from .models import ProjectEstimate

class ProjectEstimateForm(forms.ModelForm):
    class Meta:
        model = ProjectEstimate
        fields = ['plot_area', 'rooms', 'material_quality', 'paint_type', 'house_type', 'room_type', 'theme', 'budget_range']
