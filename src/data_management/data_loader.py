import os
import pandas as pd
import unidecode
import logging
from src.database.conexion_mongodb import get_mongodb_connection, PLAYERS_COLLECTION, STATS_EXPLAINED_COLLECTION

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
JUGADORES_FBREF = os.path.join(DATA_FOLDER, "fbref_full_stats_2425.csv")
EXPLICACIONES_ESTADISTICAS = os.path.join(DATA_FOLDER, "fbref_stats_explained.json")

def normalizar_nombre(nombre):
    """Normaliza el nombre de un jugador para que se pueda buscar desde la entrada."""
    return unidecode.unidecode(nombre).lower()

def cargar_estadisticas_jugadores(season=None):
    """
    Carga las estadísticas de jugadores desde MongoDB y las devuelve como DataFrame.
    Si la conexión a MongoDB falla, carga los datos desde el CSV como fallback.

    Args:
        season (str, optional): Temporada a cargar (e.g., "2223", "2324"). 
                               Si es None, carga todos los datos.
    """
    try:
        mongodb = get_mongodb_connection()

        query = {}
        if season:
            query = {"Season": season}

        cursor = mongodb.find(PLAYERS_COLLECTION, query=query, projection={'_id': 0})
        df = pd.DataFrame(list(cursor))

        if df.empty:
            logger.info("No data found in MongoDB. Falling back to CSV file.")
            # Si se especifica una temporada, usar el archivo específico de esa temporada
            if season:
                csv_file = os.path.join(DATA_FOLDER, f"fbref_full_stats_{season}.csv")
                if os.path.exists(csv_file):
                    df = pd.read_csv(csv_file)
                else:
                    logger.info(f"No se encontró el archivo para la temporada {season}. Usando archivo general.")
                    df = pd.read_csv(JUGADORES_FBREF)
                    # Filtrar por temporada si existe la columna Season
                    if 'Season' in df.columns and season:
                        df = df[df['Season'] == season]
            else:
                df = pd.read_csv(JUGADORES_FBREF)

            df['normalized_name'] = df['Player'].apply(normalizar_nombre)

        return df

    except Exception as e:
        logger.error(f"Error al cargar datos desde MongoDB: {str(e)}. Intentando cargar desde CSV.")
        try:
            if season:
                csv_file = os.path.join(DATA_FOLDER, f"fbref_full_stats_{season}.csv")
                if os.path.exists(csv_file):
                    df = pd.read_csv(csv_file)
                else:
                    logger.info(f"No se encontró el archivo para la temporada {season}. Usando archivo general.")
                    df = pd.read_csv(JUGADORES_FBREF)

                    if 'Season' in df.columns and season:
                        df = df[df['Season'] == season]
            else:
                df = pd.read_csv(JUGADORES_FBREF)

            df['normalized_name'] = df['Player'].apply(normalizar_nombre)
            return df
        except Exception as csv_error:
            return f"Error al leer los datos: {str(csv_error)}"

def cargar_explicacion_estadisticas():
    """
    Carga las explicaciones de estadísticas desde MongoDB y las devuelve como DataFrame.
    Si la conexión a MongoDB falla, carga los datos desde el JSON como fallback.
    """
    try:
        mongodb = get_mongodb_connection()
        cursor = mongodb.find(STATS_EXPLAINED_COLLECTION, projection={'_id': 0})

        df = pd.DataFrame(list(cursor))

        if df.empty:
            logger.info("No data found in MongoDB. Falling back to JSON file.")
            df = pd.read_json(EXPLICACIONES_ESTADISTICAS)

        return df

    except Exception as e:
        logger.error(f"Error al cargar explicaciones desde MongoDB: {str(e)}. Intentando cargar desde JSON.")
        try:
            df = pd.read_json(EXPLICACIONES_ESTADISTICAS)
            return df
        except Exception as json_error:
            return f"Error al leer los datos: {str(json_error)}"
