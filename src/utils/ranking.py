import numpy as np
import pandas as pd
import os
from src.utils.data_loader import cargar_estadisticas_jugadores

def calcular_ponderacion_estadisticas(jugador_data):
    """
    Calcula la puntuación ponderada de un jugador basada en sus estadísticas y posición.

    Parámetros:
    - jugador_data (pd.Series): Serie con los datos del jugador.

    Return:
    - float: Puntuación ponderada del jugador.
    """
    posicion = jugador_data['position_group'] if 'position_group' in jugador_data else "Unknown"

    pesos = {
        "GK": {  # Portero
            "Total - Cmp%": 0.15,  # Precisión de pases
            "Long - Cmp%": 0.15,   # Precisión de pases largos
            "Saves": 0.25,         # Paradas
            "Save%": 0.25,         # Porcentaje de paradas
            "CS": 0.20,            # Porterías a cero
        },
        "Defender": {  # Defensa
            "Tkl+Int": 0.20,       # Entradas + Intercepciones
            "Clr": 0.15,           # Despejes
            "Total - Cmp%": 0.15,  # Precisión de pases
            "Err": -0.15,          # Errores (negativo)
            "Blocks": 0.15,        # Bloqueos
            "Won%": 0.10,          # Porcentaje de duelos aéreos ganados
            "PrgP": 0.10,          # Pases progresivos
        },
        "Defensive-Midfielders": {  # Mediocentro defensivo
            "Tkl+Int": 0.20,       # Entradas + Intercepciones
            "Total - Cmp%": 0.20,  # Precisión de pases
            "PrgP": 0.15,          # Pases progresivos
            "Recov": 0.15,         # Recuperaciones
            "PrgC": 0.10,          # Conducciones progresivas
            "KP": 0.10,            # Pases clave
            "Err": -0.10,          # Errores (negativo)
        },
        "Central Midfielders": {  # Mediocentro
            "Total - Cmp%": 0.20,  # Precisión de pases
            "PrgP": 0.15,          # Pases progresivos
            "KP": 0.15,            # Pases clave
            "PrgC": 0.15,          # Conducciones progresivas
            "Tkl+Int": 0.10,       # Entradas + Intercepciones
            "Ast": 0.15,           # Asistencias
            "Gls": 0.10,           # Goles
        },
        "Attacking Midfielders": {  # Mediapunta
            "KP": 0.20,            # Pases clave
            "Ast": 0.15,           # Asistencias
            "Gls": 0.15,           # Goles
            "SCA": 0.15,           # Acciones que crean ocasiones de disparo
            "PrgC": 0.15,          # Conducciones progresivas
            "Succ%": 0.10,         # Porcentaje de regates exitosos
            "Total - Cmp%": 0.10,  # Precisión de pases
        },
        "Wing-Back": {  # Carrilero
            "Crs_x": 0.20,         # Centros
            "PrgC": 0.15,          # Conducciones progresivas
            "Tkl+Int": 0.15,       # Entradas + Intercepciones
            "KP": 0.15,            # Pases clave
            "Ast": 0.15,           # Asistencias
            "Total - Cmp%": 0.10,  # Precisión de pases
            "Gls": 0.10,           # Goles
        },
        "Forwards": {  # Delantero
            "Gls": 0.25,           # Goles
            "Sh": 0.15,            # Tiros
            "SoT%": 0.15,          # Porcentaje de tiros a puerta
            "Ast": 0.10,           # Asistencias
            "KP": 0.10,            # Pases clave
            "Succ%": 0.10,         # Porcentaje de regates exitosos
            "PrgR": 0.15,          # Pases progresivos recibidos
        },
        "Unknown": {  # Posición desconocida - pesos genéricos
            "Gls": 0.15,           # Goles
            "Ast": 0.15,           # Asistencias
            "Total - Cmp%": 0.15,  # Precisión de pases
            "Tkl+Int": 0.15,       # Entradas + Intercepciones
            "PrgP": 0.10,          # Pases progresivos
            "PrgC": 0.10,          # Conducciones progresivas
            "KP": 0.10,            # Pases clave
            "SCA": 0.10,           # Acciones que crean ocasiones de disparo
        }
    }

    # Seleccionar los pesos según la posición
    pesos_posicion = pesos.get(posicion, pesos["Unknown"])

    # Calcular la puntuación ponderada
    puntuacion = 0
    for stat, peso in pesos_posicion.items():
        if stat in jugador_data:
            # Convertir a float si es posible, si no, usar 0
            try:
                valor = float(jugador_data[stat]) if not pd.isna(jugador_data[stat]) else 0
                puntuacion += valor * peso
            except (ValueError, TypeError):
                # Si no se puede convertir a float, ignorar esta estadística
                pass

    return puntuacion

def calcular_ranking_jugadores(flpr_colectiva, jugadores):
    """
    Calcula el ranking de los jugadores basado en la matriz FLPR colectiva.
    La puntuación es independiente del ranking y está en un rango de 0 a 10.

    Parámetros:
    - flpr_colectiva (np.ndarray): Matriz FLPR colectiva.
    - jugadores (list): Lista con los nombres de los jugadores.

    Return:
    - list: Lista de tuplas (jugador, puntuación) ordenada según el ranking FLPR.
            La puntuación es independiente y está en un rango de 0 a 10.
    """
    n = flpr_colectiva.shape[0]
    puntuaciones_flpr = []
    puntuaciones_stats = []

    # Calcular puntuaciones FLPR para todos los jugadores
    for i in range(n):
        puntuacion_flpr = sum(flpr_colectiva[i][j] for j in range(n) if i != j)
        puntuaciones_flpr.append((jugadores[i], puntuacion_flpr))

    # Ordenar jugadores según puntuación FLPR (este es el ranking real)
    puntuaciones_flpr.sort(key=lambda x: x[1], reverse=True)

    # Cargar estadísticas de jugadores para calcular puntuaciones independientes
    df_jugadores = cargar_estadisticas_jugadores()
    puntuaciones_finales = []

    # Para cada jugador en el orden del ranking FLPR
    for jugador, _ in puntuaciones_flpr:
        # Puntuación por defecto si no se encuentran estadísticas
        puntuacion_normalizada = 5.0  # Valor medio en escala 0-10

        if not isinstance(df_jugadores, str):  # Si no hay error al cargar los datos
            # Normalizar nombres para búsqueda si no se ha hecho ya
            if 'normalized_name' not in df_jugadores.columns:
                df_jugadores['normalized_name'] = df_jugadores['Player'].apply(lambda x: x.lower())

            # Buscar jugador en el dataset
            jugador_normalizado = jugador.lower()
            jugador_encontrado = df_jugadores[df_jugadores['normalized_name'].str.contains(jugador_normalizado, case=False, na=False)]

            if not jugador_encontrado.empty:
                # Calcular puntuación basada en estadísticas
                puntuacion_stats = calcular_ponderacion_estadisticas(jugador_encontrado.iloc[0])

                puntuacion_normalizada = min(10, max(0, puntuacion_stats / 10))

        puntuaciones_finales.append((jugador, puntuacion_normalizada))

    return puntuaciones_finales