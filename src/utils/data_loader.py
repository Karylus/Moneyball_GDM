import os
import pandas as pd
import unidecode

DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data")
JUGADORES_FBREF = os.path.join(DATA_FOLDER, "fbref_players_with_market_value.csv")
JUGADORES_TRANSFERMARKT = os.path.join(DATA_FOLDER, "players_transfermarkt.csv")

def normalizar_nombre(nombre):
    """Normaliza el nombre de un jugador para que se pueda buscar desde la entrada."""
    return unidecode.unidecode(nombre).lower()

def cargar_estadisticas_jugadores():
    """Carga el CSV de estadísticas de jugadores y lo devuelve como DataFrame."""
    try:
        df = pd.read_csv(JUGADORES_FBREF)
        df['normalized_name'] = df['Player'].apply(normalizar_nombre)
        return df

    except Exception as e:
        return f"Error al leer los datos: {str(e)}"