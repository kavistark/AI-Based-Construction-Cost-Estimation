from django.db import models
from django.contrib.auth.models import User

class ProjectEstimate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    plot_area = models.FloatField(help_text="Area in square feet")
    rooms = models.CharField(max_length=10)
    material_quality = models.CharField(max_length=20)
    paint_type = models.CharField(max_length=20)
    house_type = models.CharField(max_length=10)
    room_type = models.CharField(max_length=20)
    theme = models.CharField(max_length=30)
    budget_range = models.CharField(max_length=50)
    
    # Generated Predictions
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.house_type} - {self.plot_area} sq.ft. (Est: ₹{self.estimated_cost})"
