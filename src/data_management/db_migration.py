import os
import pandas as pd
import json
import logging
import sys

_CURRENT_FILE_PATH = os.path.abspath(__file__)
_DATA_MANAGEMENT_DIR = os.path.dirname(_CURRENT_FILE_PATH)
_SRC_DIR = os.path.dirname(_DATA_MANAGEMENT_DIR)
PROJECT_ROOT = os.path.dirname(_SRC_DIR)

DATA_FOLDER = os.path.join(PROJECT_ROOT, "data")
EXPLICACIONES_ESTADISTICAS = os.path.join(DATA_FOLDER, "fbref_stats_explained.json")

# --- Configuración del Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Importaciones de Módulos del Proyecto ---
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.database.connection import get_mongodb_connection, PLAYERS_COLLECTION, \
        STATS_EXPLAINED_COLLECTION
    from src.data_management.data_loader import normalizar_nombre
except ImportError as e:
    logger.critical(
        f"Error importando módulos necesarios: {e}. Asegúrate que la estructura del proyecto y PYTHONPATH son correctos.")
    if 'get_mongodb_connection' not in globals():
        raise


def format_season(season_str):
    """Convierte el formato de temporada de 'YYYY-YYYY' a 'YY/YY'."""
    if isinstance(season_str, str) and '-' in season_str:
        parts = season_str.split('-')
        if len(parts) == 2 and len(parts[0]) == 4 and len(parts[1]) == 4:
            return f"{parts[0][2:]}/{parts[1][2:]}"
    return season_str


def migrate_multiple_seasons(csv_file_paths):
    """
    Migra estadísticas de jugadores de varios CSV a MongoDB,
    extrayendo la temporada de una columna 'Season'.
    csv_file_paths: lista de rutas a los archivos CSV.
    """
    try:
        mongodb = get_mongodb_connection()

        if mongodb.get_collection(PLAYERS_COLLECTION).count_documents({}) > 0:
            logger.warning(
                f"Collection {PLAYERS_COLLECTION} already contains data. Dropping collection...")
            mongodb.drop_collection(PLAYERS_COLLECTION)

        total_docs = 0
        for ruta_csv in csv_file_paths:
            logger.info(f"Leyendo estadísticas de {ruta_csv}")
            if not os.path.exists(ruta_csv):
                logger.error(f"Archivo CSV no encontrado: {ruta_csv}. Saltando este archivo.")
                continue

            df = pd.read_csv(ruta_csv)

            if 'Season' not in df.columns:
                logger.error(
                    f"La columna 'Season' no se encuentra en {ruta_csv}. Saltando archivo.")
                continue

            season_raw = df['Season'].iloc[0]
            temporada_formateada = format_season(season_raw)

            df['temporada'] = temporada_formateada
            df['normalized_name'] = df['Player'].apply(normalizar_nombre)

            players_data = df.to_dict('records')
            mongodb.insert_many(PLAYERS_COLLECTION, players_data)
            total_docs += len(players_data)
            logger.info(
                f"Insertados {len(players_data)} registros de {ruta_csv} para la temporada {temporada_formateada}")

        if total_docs > 0:
            mongodb.get_collection(PLAYERS_COLLECTION).create_index('normalized_name')
            mongodb.get_collection(PLAYERS_COLLECTION).create_index('temporada')
        logger.info(f"Se migraron {total_docs} registros de jugadores a MongoDB")
        return True
    except FileNotFoundError as e:
        logger.error(f"Error de archivo no encontrado durante la migración de jugadores: {e}")
        return False
    except Exception as e:
        logger.error(f"Error migrando estadísticas de jugadores: {str(e)}")
        return False


def migrate_stats_explanations():
    """
    Migra las explicaciones de las estadísticas de JSON a MongoDB.
    """
    try:
        if not os.path.exists(EXPLICACIONES_ESTADISTICAS):
            logger.error(
                f"Archivo de explicaciones JSON no encontrado: {EXPLICACIONES_ESTADISTICAS}")
            return False

        mongodb = get_mongodb_connection()

        if mongodb.get_collection(STATS_EXPLAINED_COLLECTION).count_documents({}) > 0:
            logger.warning(
                f"Collection {STATS_EXPLAINED_COLLECTION} already contains data. Dropping collection...")
            mongodb.drop_collection(STATS_EXPLAINED_COLLECTION)

        logger.info(f"Leyendo explicaciones de estadísticas desde {EXPLICACIONES_ESTADISTICAS}")
        with open(EXPLICACIONES_ESTADISTICAS, 'r', encoding='utf-8') as f:
            stats_explanations = json.load(f)

        stats_docs = []
        for stat, description in stats_explanations.items():
            if not stat.startswith("_"):
                stats_docs.append({
                    'stat': stat,
                    'description': description,
                    'stat_lower': stat.lower()
                })

        if not stats_docs:
            logger.info("No hay explicaciones de estadísticas para migrar.")
            return True

        logger.info(f"Insertando {len(stats_docs)} explicaciones de estadísticas en MongoDB")
        mongodb.insert_many(STATS_EXPLAINED_COLLECTION, stats_docs)
        mongodb.get_collection(STATS_EXPLAINED_COLLECTION).create_index('stat_lower')
        logger.info(
            f"Explicaciones de estadísticas migradas exitosamente a la colección: {STATS_EXPLAINED_COLLECTION}")
        return True
    except FileNotFoundError:
        logger.error(f"Archivo de explicaciones JSON no encontrado: {EXPLICACIONES_ESTADISTICAS}")
        return False
    except Exception as e:
        logger.error(f"Error migrando explicaciones de estadísticas: {str(e)}")
        return False


def run_migration():
    """
    Ejecuta el proceso completo de migración.
    """
    logger.info("Iniciando la migración de datos a MongoDB")

    # Asegúrate que los nombres de archivo coincidan con los que tienes en data
    csv_files_to_migrate = [
        os.path.join(DATA_FOLDER, "fbref_full_stats.csv"),
        os.path.join(DATA_FOLDER, "fbref_full_stats_2324.csv"),
        os.path.join(DATA_FOLDER, "fbref_full_stats_2223.csv"),
    ]

    all_csv_exist = True
    for csv_path in csv_files_to_migrate:
        if not os.path.exists(csv_path):
            logger.error(f"Archivo CSV requerido no encontrado: {csv_path}")
            all_csv_exist = False

    if not all_csv_exist:
        logger.error("Faltan uno o más archivos CSV. Abortando migración de jugadores.")
        players_success = False
    else:
        players_success = migrate_multiple_seasons(csv_files_to_migrate)

    explanations_success = migrate_stats_explanations()

    if players_success and explanations_success:
        logger.info("Migración completada exitosamente")
        return True
    else:
        logger.error("La migración falló. Revisa los logs para más detalles.")
        return False


if __name__ == "__main__":
    # Este bloque se ejecuta solo cuando el script es llamado directamente
    print(
        "Iniciando migración de datos desde CSV a MongoDB (ejecución directa de db_migration.py)...")

    # La lógica de importación al inicio del script ya debería haber
    # configurado sys.path para que 'from src.database...' funcione.
    # No es necesario modificar sys.path aquí de nuevo si la estructura de importación
    # al inicio del archivo es robusta.

    success = run_migration()

    if success:
        print("Migración completada exitosamente!")
    else:
        print("Migración fallida. Revisa los logs para más detalles.")