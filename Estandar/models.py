from django.db import models

# Create your models here.


class Unidades(models.Model):
    nombre = models.CharField(max_length=20)

    
    def __str__(self):
        return self.nombre
    
    
class Medidas(models.Model):
    nombre = models.CharField(max_length=20)
    #unidades = models.ManyToManyField(Unidades)


    def __str__(self):
        return self.nombre
    
class MedidasUnidades(models.Model):
    id = models.AutoField(primary_key=True)
    medida = models.ForeignKey(Medidas, on_delete=models.CASCADE)
    unidad = models.ForeignKey(Unidades, on_delete=models.CASCADE)
    maximo = models.FloatField()
    minimo = models.FloatField()
    step = models.FloatField()
    
    def __str__(self):
        return f"{self.medida.nombre} - {self.unidad.nombre}"

class Regla(models.Model):
    nombre = models.CharField(max_length=20)
    nombre_medida = models.CharField(max_length=20)
    nombre_unidad = models.CharField(max_length=20)
    descripcion = models.TextField()
    minimo = models.FloatField()
    maximo = models.FloatField()
    
    def __str__(self):
        return self.nombre


    
    