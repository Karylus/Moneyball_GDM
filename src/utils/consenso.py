import numpy as np

def calcular_matriz_similitud(flpr1, flpr2):
    """
    Calcula la matriz de similitud entre dos matrices FLPR.

    Parámetros:
    - flpr1 (np.ndarray): Primera matriz FLPR.
    - flpr2 (np.ndarray): Segunda matriz FLPR.

    Return:
    - np.ndarray: Matriz de similitud.
    """
    n = flpr1.shape[0]
    matriz_similitud = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            # Calculamos la similitud como 1 menos la diferencia absoluta
            matriz_similitud[i][j] = 1 - abs(flpr1[i][j] - flpr2[i][j])

    return np.round(matriz_similitud, 3)


def calcular_matriz_consenso(matrices_similitud):
    """
    Calcula la matriz de consenso agregando todas las matrices de similitud
    usando la media aritmética.

    Parámetros:
    - matrices_similitud (list): Lista de matrices de similitud.

    Return:
    - np.ndarray: Matriz de consenso.
    """
    if not matrices_similitud:
        raise ValueError("La lista de matrices de similitud está vacía")

    # Inicializamos la matriz de consenso con ceros
    matriz_consenso = np.zeros_like(matrices_similitud[0])

    # Sumamos todas las matrices
    for matriz in matrices_similitud:
        matriz_consenso += matriz

    # Calculamos la media aritmética
    matriz_consenso = matriz_consenso / len(matrices_similitud)

    return np.round(matriz_consenso, 3)


def calcular_consenso_nivel1(matriz_consenso):
    """
    Calcula el consenso de nivel 1 (consenso por pares de alternativas).

    Parámetros:
    - matriz_consenso (np.ndarray): Matriz de consenso.

    Return:
    - np.ndarray: Matriz de consenso de nivel 1.
    """
    return matriz_consenso


def calcular_consenso_nivel2(matriz_consenso):
    """
    Calcula el consenso de nivel 2 (consenso por alternativas).

    Parámetros:
    - matriz_consenso (np.ndarray): Matriz de consenso.

    Return:
    - np.ndarray: Vector de consenso de nivel 2.
    """
    n = matriz_consenso.shape[0]
    consenso_nivel2 = np.zeros(n)

    for i in range(n):
        # Para cada alternativa, calculamos la media de sus similitudes con todas las demás
        suma = 0
        for j in range(n):
            if i != j:  # Excluimos la diagonal
                suma += matriz_consenso[i][j]

        consenso_nivel2[i] = suma / (n - 1)

    return np.round(consenso_nivel2, 3)


def calcular_consenso_nivel3(matriz_consenso):
    """
    Calcula el consenso de nivel 3 (consenso global).

    Parámetros:
    - matriz_consenso (np.ndarray): Matriz de consenso.

    Return:
    - float: Valor de consenso global.
    """
    consenso_nivel2 = calcular_consenso_nivel2(matriz_consenso)
    return round(np.mean(consenso_nivel2), 3)


def calcular_cr(matrices_similitud, consenso_minimo=0.8):
    """
    Calcula el nivel medio de consenso (CR) y verifica si se alcanza el consenso mínimo.

    Parámetros:
    - matrices_similitud (list): Lista de matrices de similitud.
    - consenso_minimo (float): Valor mínimo de consenso requerido (entre 0 y 1).

    Return:
    - tuple: (CR, consenso_alcanzado)
        - CR (float): Nivel medio de consenso (entre 0 y 1).
        - consenso_alcanzado (bool): True si se alcanza el consenso mínimo, False en caso contrario.
    """
    matriz_consenso = calcular_matriz_consenso(matrices_similitud)
    cr = calcular_consenso_nivel3(matriz_consenso)
    consenso_alcanzado = cr >= consenso_minimo

    return cr, consenso_alcanzado