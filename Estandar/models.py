from django.db import models

# Create your models here.


class Unidades(models.Model):
    nombre = models.CharField(max_length=20)
    min = models.FloatField()
    max = models.FloatField()
    step = models.FloatField()
    
    def __str__(self):
        return self.nombre
    
    
class Medidas(models.Model):
    nombre = models.CharField(max_length=20)
    unidades = models.ManyToManyField(Unidades)


    def __str__(self):
        return self.nombre
    

class Regla(models.Model):
    nombre = models.CharField(max_length=20)
    nombre_medida = models.CharField(max_length=20)
    nombre_unidad = models.CharField(max_length=20)
    descripcion = models.TextField()
    minimo = models.FloatField()
    maximo = models.FloatField()
    
    