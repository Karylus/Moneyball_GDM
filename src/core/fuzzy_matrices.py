import numpy as np
import skfuzzy as fuzz

rangos = np.arange(0, 1.1, 0.1)

terminos_linguisticos = {
    "Muy Bajo": fuzz.trapmf(rangos, [0, 0, 0.05, 0.15]),
    "Bajo": fuzz.trapmf(rangos, [0.1, 0.2, 0.3, 0.4]),
    "Medio": fuzz.trapmf(rangos, [0.35, 0.45, 0.55, 0.65]),
    "Alto": fuzz.trapmf(rangos, [0.6, 0.7, 0.8, 0.9]),
    "Muy Alto": fuzz.trapmf(rangos, [0.85, 0.95, 1, 1]),

    "Very Low": fuzz.trapmf(rangos, [0, 0, 0.05, 0.15]),
    "Low": fuzz.trapmf(rangos, [0.1, 0.2, 0.3, 0.4]),
    "Medium": fuzz.trapmf(rangos, [0.35, 0.45, 0.55, 0.65]),
    "High": fuzz.trapmf(rangos, [0.6, 0.7, 0.8, 0.9]),
    "Very High": fuzz.trapmf(rangos, [0.85, 0.95, 1, 1])
}


def generar_flpr(terminos):
    """
    Genera una matriz FLPR a partir de los términos lingüísticos dados.

    Parámetros:
    - terminos (list): Lista de términos lingüísticos de los jugadores para un criterio.

    Return:
    - np.ndarray: Matriz FLPR.
    """
    valores = []
    for termino in terminos:
        if termino in terminos_linguisticos:
            valores.append(fuzz.defuzz(rangos, terminos_linguisticos[termino], 'centroid'))
        else:
            raise ValueError(f"Término lingüístico desconocido: {termino}")

    n = len(valores)
    flpr = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            if i == j:
                flpr[i][j] = 0.5
            else:
                flpr[i][j] = round(valores[i] / (valores[i] + valores[j]), 3)

    return flpr


def calcular_flpr_comun(flpr_agente, flpr_usuario):
    """
    Calcula la FLPR común usando la media de las matrices FLPR del agente y del usuario.

    Parámetros:
    - flpr_agente (np.ndarray): Matriz FLPR del agente.
    - flpr_usuario (np.ndarray): Matriz FLPR del usuario.

    Return:
    - np.ndarray: FLPR común.
    """
    return np.round((flpr_agente + flpr_usuario) / 2, 3)

def calcular_matrices_flpr(matrices, criterios):
    """
    Calcula las matrices FLPR para cada matriz de calificaciones.

    Args:
        matrices (dict): Diccionario con las matrices de calificaciones
        criterios (list): Lista de criterios

    Returns:
        dict: Diccionario con las matrices FLPR calculadas
    """
    flpr_matrices = {}

    for nombre, matriz in matrices.items():
        flpr_matriz = None
        for idx, criterio in enumerate(criterios):
            calificaciones = [fila[idx] for fila in matriz]
            flpr_criterio = generar_flpr(calificaciones)

            if flpr_matriz is None:
                flpr_matriz = flpr_criterio
            else:
                flpr_matriz = calcular_flpr_comun(flpr_matriz, flpr_criterio)

        flpr_matrices[nombre] = flpr_matriz

    return flpr_matrices