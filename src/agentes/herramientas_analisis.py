from src.utils.data_loader import *
from rapidfuzz import process, fuzz
import json

UMBRAL_SIMILITUD = 85


def obtener_estadisticas_equipo(equipo: str) -> str:
    return "foo"


def obtener_info_jugador(jugador: str) -> str:
    df = cargar_datos_jugadores()

    jugador_normalizado = normalizar_nombre(jugador.strip())

    if 'normalized_name' not in df.columns:
        df['normalized_name'] = df['Player'].apply(normalizar_nombre)

    mejor_match, score, index = process.extractOne(jugador_normalizado, df['normalized_name'].tolist(), scorer=fuzz.ratio)

    if score < UMBRAL_SIMILITUD:
        return f"{jugador}: Datos no disponibles"

    jugador_data = df.iloc[index]

    return json.dumps(jugador_data.to_dict(), indent=2, ensure_ascii=False)

def comparar_jugadores(jugador1: str, jugador2: str) -> str:
    info_jugador1 = obtener_info_jugador(jugador1)
    info_jugador2 = obtener_info_jugador(jugador2)

    return f"{info_jugador1}\n\n{info_jugador2}"
