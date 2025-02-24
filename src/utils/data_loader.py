import os
import pandas as pd
import unidecode

DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data")
JUGADORES_CSV = os.path.join(DATA_FOLDER, "fbref_full_players_stats.csv")

def normalizar_nombre(nombre):
    """Normaliza el nombre de un jugador para que sea compatible con la base de datos."""
    return unidecode.unidecode(nombre).lower()

def cargar_datos_jugadores():
    """Carga el CSV de jugadores y lo devuelve como DataFrame."""
    try:
        df = pd.read_csv(JUGADORES_CSV)
        df['normalized_name'] = df['Player'].apply(normalizar_nombre)
        return df

    except Exception as e:
        return f"Error al leer los datos: {str(e)}"