import numpy as np
import skfuzzy as fuzz

rangos = np.arange(0, 1.1, 0.1)

terminos_linguisticos = {
    "Muy Bajo": fuzz.trapmf(rangos, [0, 0, 0.1, 0.2]),
    "Bajo": fuzz.trapmf(rangos, [0.1, 0.2, 0.3, 0.4]),
    "Medio": fuzz.trapmf(rangos, [0.3, 0.4, 0.6, 0.7]),
    "Alto": fuzz.trapmf(rangos, [0.6, 0.7, 0.8, 0.9]),
    "Muy Alto": fuzz.trapmf(rangos, [0.8, 0.9, 1, 1])
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
            valores.append(np.mean(terminos_linguisticos[termino]))
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