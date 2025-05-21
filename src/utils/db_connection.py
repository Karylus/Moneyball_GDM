from pymongo import MongoClient
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('MONGO_DB_NAME', 'Moneyball')

PLAYERS_COLLECTION = 'stats_jugadores'
STATS_EXPLAINED_COLLECTION = 'stats_explained'

class MongoDBConnection:
    """
    Clase utilitaria para manejar la conexión a MongoDB.
    Gestiona las conexiones a MongoDB y proporciona CRUD.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
            try:
                cls._instance.client = MongoClient(MONGO_URI)
                cls._instance.db = cls._instance.client[DB_NAME]
                logger.info(f"Conectado la BD de MongoDB: {DB_NAME}")
            except Exception as e:
                logger.error(f"Error conectando a MongoDB: {str(e)}")
                raise
        return cls._instance
    
    def get_database(self):
        """Obtiene la instancia de la BD"""
        return self.db
    
    def get_collection(self, collection_name):
        """Obtiene una colección por su nombre"""
        return self.db[collection_name]
    
    def close_connection(self):
        """Cierra la conexión a MongoDB"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("Conexión a MongoDB cerrada")
    
    def insert_one(self, collection_name, document):
        """Inserta un solo documento en una colección"""
        try:
            collection = self.get_collection(collection_name)
            result = collection.insert_one(document)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error insertando el documento: {str(e)}")
            raise
    
    def insert_many(self, collection_name, documents):
        """Inserta múltiples documentos en una colección"""
        try:
            collection = self.get_collection(collection_name)
            result = collection.insert_many(documents)
            return result.inserted_ids
        except Exception as e:
            logger.error(f"Error insertando documentos: {str(e)}")
            raise
    
    def find_one(self, collection_name, query=None):
        """Encuentra un solo documento en una colección"""
        try:
            collection = self.get_collection(collection_name)
            return collection.find_one(query or {})
        except Exception as e:
            logger.error(f"Error finding document: {str(e)}")
            raise
    
    def find(self, collection_name, query=None, projection=None):
        """Encuentra múltiples documentos en una colección"""
        try:
            collection = self.get_collection(collection_name)
            return collection.find(query or {}, projection or {})
        except Exception as e:
            logger.error(f"Error finding documents: {str(e)}")
            raise
    
    def update_one(self, collection_name, query, update):
        """Actualiza un solo documento en una colección"""
        try:
            collection = self.get_collection(collection_name)
            return collection.update_one(query, update)
        except Exception as e:
            logger.error(f"Error updating document: {str(e)}")
            raise
    
    def delete_one(self, collection_name, query):
        """Borra un solo documento de una colección"""
        try:
            collection = self.get_collection(collection_name)
            return collection.delete_one(query)
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            raise
    
    def delete_many(self, collection_name, query):
        """Borra múltiples documentos de una colección"""
        try:
            collection = self.get_collection(collection_name)
            return collection.delete_many(query)
        except Exception as e:
            logger.error(f"Error deleting documents: {str(e)}")
            raise
    
    def drop_collection(self, collection_name):
        """Borra una colección de la BD"""
        try:
            self.db.drop_collection(collection_name)
            logger.info(f"Collection {collection_name} dropped")
        except Exception as e:
            logger.error(f"Error dropping collection: {str(e)}")
            raise

mongodb = MongoDBConnection()

def get_mongodb_connection():
    return mongodb