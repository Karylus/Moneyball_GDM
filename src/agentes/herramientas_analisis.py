from src.utils.data_loader import *
from rapidfuzz import process, fuzz
import json

UMBRAL_SIMILITUD = 85

def obtener_info_jugador(jugador: str) -> str:
    df = cargar_estadisticas_jugadores()

    jugador_normalizado = normalizar_nombre(jugador.strip())

    if 'normalized_name' not in df.columns:
        df['normalized_name'] = df['Player'].apply(normalizar_nombre)

    mejor_match, score, index = process.extractOne(jugador_normalizado, df['normalized_name'].tolist(), scorer=fuzz.ratio)

    if score < UMBRAL_SIMILITUD:
        return f"{jugador}: Datos no disponibles"

    jugador_data = df.iloc[index]

    return json.dumps(jugador_data.to_dict(), indent=2)


def obtener_info_jugadores(jugadores: list) -> str:
    """
    Obtiene las estadísticas de múltiples jugadores con una sola carga de datos.

    :param jugadores: Lista de nombres de jugadores a buscar.
    :return: Un JSON con la información de todos los jugadores solicitados.
    """
    df = cargar_estadisticas_jugadores()

    if 'normalized_name' not in df.columns:
        df['normalized_name'] = df['Player'].apply(normalizar_nombre)

    resultados = {}

    for jugador in jugadores:
        jugador_normalizado = normalizar_nombre(jugador.strip())
        mejor_match, score, index = process.extractOne(jugador_normalizado, df['normalized_name'].tolist(), scorer=fuzz.ratio)

        if score < UMBRAL_SIMILITUD:
            resultados[jugador] = "Datos no disponibles"
        else:
            jugador_data = df.iloc[index]
            resultados[jugador] = jugador_data.to_dict()

    return json.dumps(resultados, indent=2)


def comparar_jugadores(jugador1: str, jugador2: str) -> str:
    info_jugador1 = obtener_info_jugador(jugador1)
    info_jugador2 = obtener_info_jugador(jugador2)

    return f"{info_jugador1}\n\n{info_jugador2}"


def listar_jugadores_por_posicion_y_precio(posicion: str, precio_max: int) -> str:
    df = cargar_estadisticas_jugadores()

    if isinstance(df, str):
        return "Error al cargar los datos."

    df_filtrado = df[df['position_group'].str.lower() == posicion.lower()]

    if df_filtrado.empty:
        return f"No se encontraron jugadores para la posición {posicion}."

    tope_precio = precio_max * 1000000
    df_filtrado = df_filtrado[df_filtrado['market_value_in_eur'] <= precio_max]

    if df_filtrado.empty:
        return f"No hay jugadores disponibles en {posicion} por menos de {precio_max} millones."

    df_filtrado = df_filtrado.sort_values(by='market_value_in_eur', ascending=False)

    mejor_jugador = df_filtrado.iloc[0].to_dict()

    return json.dumps(mejor_jugador, indent=2)
