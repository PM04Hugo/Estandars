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

class Proyecto(models.Model):
    nombre = models.CharField(max_length=20)
    estandard = models.CharField(max_length=20)
    file= models.FileField(upload_to='proyectos/')
    columnas_excluidas = models.JSONField(default=list)
    filas_confirmadas = models.JSONField(default=list)

    def __str__(self):
        return self.nombre



class Estandar(models.Model):
    nombre = models.CharField(max_length=20)
    reglas = models.ManyToManyField(Regla)
    orden  = models.JSONField(default=list)
    UMBRAL_CUIDADO  = models.IntegerField(default=1)
    UMBRAL_URGENTE  = models.IntegerField(default=3)
    UMBRAL_PELIGRO  = models.IntegerField(default=5)
    
    def __str__(self):
        return self.nombre   
    