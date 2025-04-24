import numpy as np

def calcular_ranking_jugadores(flpr_colectiva, jugadores):
    """
    Calcula el ranking de los jugadores basado en la matriz FLPR colectiva.

    Parámetros:
    - flpr_colectiva (np.ndarray): Matriz FLPR colectiva.
    - jugadores (list): Lista con los nombres de los jugadores.

    Return:
    - list: Lista de tuplas (jugador, puntuación) ordenada de mejor a peor.
    """
    n = flpr_colectiva.shape[0]
    puntuaciones = []

    for i in range(n):
        # Sumamos los valores de la fila (excluyendo la diagonal)
        puntuacion = sum(flpr_colectiva[i][j] for j in range(n) if i != j)
        puntuaciones.append((jugadores[i], puntuacion))

    # Ordenamos de mayor a menor puntuación
    puntuaciones.sort(key=lambda x: x[1], reverse=True)

    return puntuaciones