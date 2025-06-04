import os
import pandas as pd
import json
import logging
import sys

RUTA_ACTUAL = os.path.abspath(__file__)
DIR_GESTION_DATOS = os.path.dirname(RUTA_ACTUAL)
DIR_SRC = os.path.dirname(DIR_GESTION_DATOS)
RAIZ_PROYECTO = os.path.dirname(DIR_SRC)

CARPETA_DATOS = os.path.join(RAIZ_PROYECTO, "data")
EXPLICACIONES_ESTADISTICAS = os.path.join(CARPETA_DATOS, "fbref_stats_explained.json")

# Configuración de logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if RAIZ_PROYECTO not in sys.path:
    sys.path.insert(0, RAIZ_PROYECTO)

try:
    from src.database.conexion_mongodb import get_mongodb_connection, PLAYERS_COLLECTION, STATS_EXPLAINED_COLLECTION
    from src.data_management.data_loader import normalizar_nombre
except ImportError as e:
    logger.critical(
        f"Error importando módulos necesarios: {e}. Asegúrate que la estructura del proyecto y PYTHONPATH son correctos.")
    if 'get_mongodb_connection' not in globals():
        raise

def formatear_temporada(temporada_str):
    if isinstance(temporada_str, str) and '-' in temporada_str:
        partes = temporada_str.split('-')
        if len(partes) == 2 and len(partes[0]) == 4 and len(partes[1]) == 4:
            return f"{partes[0][2:]}/{partes[1][2:]}"
    return temporada_str

def migrar_varias_temporadas(rutas_csv):
    """
    Migra estadísticas de jugadores de varios CSV a MongoDB,
    extrayendo la temporada de la columna 'Season'.
    """
    try:
        mongodb = get_mongodb_connection()

        if mongodb.get_collection(PLAYERS_COLLECTION).count_documents({}) > 0:
            logger.warning(
                f"La colección {PLAYERS_COLLECTION} ya contiene datos. Eliminando colección...")
            mongodb.drop_collection(PLAYERS_COLLECTION)

        total_docs = 0
        for ruta_csv in rutas_csv:
            logger.info(f"Leyendo estadísticas de {ruta_csv}")
            if not os.path.exists(ruta_csv):
                logger.error(f"Archivo CSV no encontrado: {ruta_csv}. Se omite este archivo.")
                continue

            df = pd.read_csv(ruta_csv)

            if 'Season' not in df.columns:
                logger.error(
                    f"La columna 'Season' no se encuentra en {ruta_csv}. Se omite el archivo.")
                continue

            temporada_raw = df['Season'].iloc[0]
            temporada_formateada = formatear_temporada(temporada_raw)

            df['temporada'] = temporada_formateada
            df['normalized_name'] = df['Player'].apply(normalizar_nombre)

            datos_jugadores = df.to_dict('records')
            mongodb.insert_many(PLAYERS_COLLECTION, datos_jugadores)
            total_docs += len(datos_jugadores)
            logger.info(
                f"Insertados {len(datos_jugadores)} registros de {ruta_csv} para la temporada {temporada_formateada}")

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

def migrar_explicaciones_estadisticas():
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
                f"La colección {STATS_EXPLAINED_COLLECTION} ya contiene datos. Eliminando colección...")
            mongodb.drop_collection(STATS_EXPLAINED_COLLECTION)

        logger.info(f"Leyendo explicaciones de estadísticas desde {EXPLICACIONES_ESTADISTICAS}")
        with open(EXPLICACIONES_ESTADISTICAS, 'r', encoding='utf-8') as f:
            explicaciones = json.load(f)

        docs_explicaciones = []
        for estadistica, descripcion in explicaciones.items():
            if not estadistica.startswith("_"):
                docs_explicaciones.append({
                    'stat': estadistica,
                    'description': descripcion,
                    'stat_lower': estadistica.lower()
                })

        if not docs_explicaciones:
            logger.info("No hay explicaciones de estadísticas para migrar.")
            return True

        logger.info(f"Insertando {len(docs_explicaciones)} explicaciones de estadísticas en MongoDB")
        mongodb.insert_many(STATS_EXPLAINED_COLLECTION, docs_explicaciones)
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

def ejecutar_migracion():
    """
    Ejecuta el proceso completo de migración.
    """
    logger.info("Iniciando la migración de datos a MongoDB")

    archivos_csv = [
        os.path.join(CARPETA_DATOS, "fbref_full_stats_2425.csv"),
        os.path.join(CARPETA_DATOS, "fbref_full_stats_2324.csv"),
        os.path.join(CARPETA_DATOS, "fbref_full_stats_2223.csv"),
    ]

    existen_todos = True
    for ruta_csv in archivos_csv:
        if not os.path.exists(ruta_csv):
            logger.error(f"Archivo CSV requerido no encontrado: {ruta_csv}")
            existen_todos = False

    if not existen_todos:
        logger.error("Faltan uno o más archivos CSV. Abortando migración de jugadores.")
        exito_jugadores = False
    else:
        exito_jugadores = migrar_varias_temporadas(archivos_csv)

    exito_explicaciones = migrar_explicaciones_estadisticas()

    if exito_jugadores and exito_explicaciones:
        logger.info("Migración completada exitosamente")
        return True
    else:
        logger.error("La migración falló. Revisa los logs para más detalles.")
        return False