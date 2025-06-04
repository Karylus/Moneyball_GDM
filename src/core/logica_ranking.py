import pandas as pd
from src.data_management.data_loader import cargar_estadisticas_jugadores

def calcular_ponderacion_estadisticas(jugador_data):
    """
    Calcula la puntuación bruta de un jugador basada en sus estadísticas y posición.
    No normaliza la puntuación final, para permitir una normalización posterior respecto al grupo.
    """
    posicion = jugador_data.get('position_group', "Unknown")

    rate_to_percentage_scale = {
        "G/Sh": {"max_expected": 0.35, "min_expected": 0.05},      # Goles por disparo
        "G/SoT": {"max_expected": 0.6, "min_expected": 0.1},       # Goles por tiro a puerta
        "npxG/Sh": {"max_expected": 0.35, "min_expected": 0.05},   # xG sin penaltis por disparo
        "SoT%": {"max_expected": 70, "min_expected": 20},          # % de tiros a puerta
        "Succ%": {"max_expected": 80, "min_expected": 20},         # % regates exitosos
        "Won%": {"max_expected": 80, "min_expected": 20},          # % duelos aéreos ganados
        "Tkl%": {"max_expected": 80, "min_expected": 20},          # % entradas exitosas
        "Total - Cmp%": {"max_expected": 95, "min_expected": 60},  # % pases completados
    }

    pesos = {
        "GK": {
            "Save%": 1.5, "PSxG-GA": 1.5, "Stp%": 0.8,
            "Total - Cmp%": 0.6, "Long - Cmp%": 0.7,
            "Saves": 0.8, "CS": 0.9, "Err": -1.0,
        },
        "Defender": {
            "TklW": 1.0, "Tkl%": 0.6, "Tkl+Int": 1.0, "Blocks": 0.9,
            "Clr": 0.7, "Won%": 0.8, "Total - Cmp%": 0.7, "PrgP": 0.7, "Err": -1.0,
        },
        "Defensive-Midfielders": {
            "Tkl+Int": 1.2, "Recov": 1.0, "TklW": 0.8,
            "Total - Cmp%": 1.0, "PrgP": 0.9, "KP": 0.6, "PrgC": 0.6, "Blocks": 0.5, "Err": -0.8,
        },
        "Central Midfielders": {
            "Total - Cmp%": 1.1, "PrgP": 1.0, "KP": 1.0, "Ast": 0.9, "Gls": 0.7,
            "PrgC": 0.8, "SCA": 0.8, "Tkl+Int": 0.6, "Recov": 0.5, "GCA": 0.6,
        },
        "Attacking Midfielders": {
            "KP": 1.2, "Ast": 1.1, "Gls": 1.0, "SCA": 1.0, "GCA": 0.9,
            "PrgC": 0.7, "PrgP": 0.6, "PrgR": 0.7, "Succ%": 0.7, "Total - Cmp%": 0.5,
            "Sh": 0.6, "npxG+xA": 0.8,
        },
        "Wing-Back": {
            "Crs_x": 1.0, "PrgC": 0.8, "PrgP": 0.7, "PrgR": 0.6,
            "Tkl+Int": 0.7, "TklW": 0.6, "KP": 0.7, "Ast": 1.0, "Gls": 0.7,
            "Total - Cmp%": 0.6, "Succ%": 0.5, "SCA": 0.6,
        },
        "Forwards": {
            "Gls": 1.5, "npxG": 1.3, "Sh": 0.8, "SoT%": 0.8,
            "G/Sh": 1.2, "npxG/Sh": 1.0, "Ast": 0.6, "KP": 0.5,
            "PrgR": 0.8, "Succ%": 0.6, "GCA": 0.5,
        },
        "Unknown": {
            "Gls": 0.9, "Ast": 0.9, "npxG": 0.8, "npxG+xA": 0.8,
            "Total - Cmp%": 0.8, "PrgP": 0.7, "PrgC": 0.7, "PrgR": 0.7,
            "KP": 0.7, "SCA": 0.7, "GCA": 0.6, "Tkl+Int": 0.7, "Sh": 0.6,
            "SoT%": 0.5, "G/Sh": 0.7, "Succ%": 0.5,
        }
    }

    pesos_posicion = pesos.get(posicion, pesos["Unknown"])

    minutos_90s = 1.0
    if '90s' in jugador_data and pd.notna(jugador_data['90s']):
        try:
            val_90s = float(jugador_data['90s'])
            minutos_90s = max(val_90s, 0.1)
        except (ValueError, TypeError):
            pass

    puntuacion = 0
    for stat, peso in pesos_posicion.items():
        if stat in jugador_data and pd.notna(jugador_data[stat]):
            try:
                valor_original = float(jugador_data[stat])
                valor_procesado = 0.0

                if stat in rate_to_percentage_scale:
                    config = rate_to_percentage_scale[stat]
                    min_expected = config["min_expected"]
                    max_expected = config["max_expected"]
                    valor_procesado = ((valor_original - min_expected) / (max_expected - min_expected)) * 100
                    valor_procesado = min(max(valor_procesado, 0.0), 100.0)
                elif stat.endswith('%'):
                    valor_procesado = min(max(valor_original, 0.0), 100.0)
                else:
                    valor_procesado = valor_original / minutos_90s if minutos_90s > 0 else 0.0

                puntuacion += valor_procesado * peso
            except (ValueError, TypeError):
                pass

    return puntuacion

def normalizar_puntuacion_individual(puntuaciones, min_teorico=0, max_teorico=100, escala=10):
    """
    Normaliza una puntuación o una lista de puntuaciones a una escala dada.
    """
    if isinstance(puntuaciones, list):
        return [min(max((puntuacion - min_teorico) / (max_teorico - min_teorico) * escala, 0), escala) for puntuacion in puntuaciones]
    else:
        valor = ((puntuaciones - min_teorico) / (max_teorico - min_teorico)) * escala
        return min(max(valor, 0), escala)

def calcular_ranking_jugadores(flpr_colectiva, jugadores):
    """
    Calcula el ranking de los jugadores basado en la matriz FLPR colectiva.
    Normaliza las puntuaciones estadísticas al máximo del grupo.
    """
    n = flpr_colectiva.shape[0]
    puntuaciones_flpr = []

    for i in range(n):
        puntuacion_flpr = sum(flpr_colectiva[i][j] for j in range(n) if i != j)
        puntuaciones_flpr.append((jugadores[i], puntuacion_flpr))

    puntuaciones_flpr.sort(key=lambda x: x[1], reverse=True)

    df_jugadores = cargar_estadisticas_jugadores()
    puntuaciones_stats = []

    for jugador, _ in puntuaciones_flpr:
        puntuacion = 0.0
        if not isinstance(df_jugadores, str):
            if 'normalized_name' not in df_jugadores.columns:
                df_jugadores['normalized_name'] = df_jugadores['Player'].apply(lambda x: x.lower())
            jugador_normalizado = jugador.lower()
            jugador_encontrado = df_jugadores[
                df_jugadores['normalized_name'].str.contains(jugador_normalizado, case=False,
                                                             na=False)]
            if not jugador_encontrado.empty:
                puntuacion_bruta = calcular_ponderacion_estadisticas(jugador_encontrado.iloc[0])
                puntuacion = puntuacion_bruta
        puntuaciones_stats.append((jugador, puntuacion))

    puntuaciones_brutas = [p for _, p in puntuaciones_stats]
    if puntuaciones_brutas:
        puntuaciones_normalizadas = normalizar_puntuacion_individual(puntuaciones_brutas, escala=10)
        puntuaciones_finales = [(jugador, puntuacion) for (jugador, _), puntuacion in
                                zip(puntuaciones_stats, puntuaciones_normalizadas)]
    else:
        puntuaciones_finales = []

    return puntuaciones_finales