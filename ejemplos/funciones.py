"""Casos de calibración: se leen y parsean, sin importarlos ni ejecutarlos.

Positivos: sumar/total y acumular/contar.
Negativos: sumar/contar e identidad/acumular.
Exploratorio: operaciones/operaciones_reordenadas.
Las expectativas se fijan por la estructura antes de medir los scores.
"""


def sumar(a, b):
    resultado = a + b
    return resultado


def total(x, y):
    valor = x + y
    return valor


def acumular(valores):
    total = 0
    for elemento in valores:
        if elemento > 5:
            total += elemento
    return total


def contar(datos):
    suma = 0
    for numero in datos:
        if numero > 5:
            suma += numero
    return suma


def identidad(valor):
    return valor


def operaciones(a):
    suma = a + 1
    producto = a * 2
    return suma, producto


def operaciones_reordenadas(a):
    producto = a * 2
    suma = a + 1
    return suma, producto
