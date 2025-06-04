import pytest
import os
import sys
import pandas as pd
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.conexion_mongodb import MongoDBConnection, PLAYERS_COLLECTION

class TestIntegracionMongoDB:
    """
    Pruebas de integración con MongoDB para asegurar almacenamiento, consulta y actualización de estadísticas.
    """

    @pytest.fixture
    def mock_mongodb(self):
        MongoDBConnection._instance = None

        with patch('src.database.conexion_mongodb.MongoClient') as mock_cliente:
            mock_bd = MagicMock()
            mock_coleccion = MagicMock()

            mock_coleccion.find_one.return_value = None
            mock_coleccion.find.return_value = []

            mock_bd.__getitem__.return_value = mock_coleccion
            mock_cliente.return_value.__getitem__.return_value = mock_bd

            mongodb = MongoDBConnection()
            mongodb._mock_coleccion = mock_coleccion

            yield mongodb

            MongoDBConnection._instance = None

    def test_insertar_y_recuperar_jugador(self, mock_mongodb):
        jugador = {
            "Player": "Jugador Ficticio",
            "Position": "MF",
            "Squad": "Equipo Ficticio",
            "Age": 25,
            "MP": 30,
            "Starts": 25,
            "Min": 2250,
            "Gls": 10,
            "Ast": 15,
            "xG": 8.5,
            "xAG": 12.3,
            "Season": "2324",
            "normalized_name": "jugador ficticio"
        }

        mock_mongodb._mock_coleccion.find_one.return_value = None

        mock_mongodb.insert_one(PLAYERS_COLLECTION, jugador)

        mock_mongodb._mock_coleccion.insert_one.assert_called_once()
        args, _ = mock_mongodb._mock_coleccion.insert_one.call_args
        assert args[0] == jugador

        mock_mongodb._mock_coleccion.find_one.return_value = jugador

        jugador_recuperado = mock_mongodb.find_one(
            PLAYERS_COLLECTION,
            {"normalized_name": "jugador ficticio"}
        )

        mock_mongodb._mock_coleccion.find_one.assert_called_with(
            {"normalized_name": "jugador ficticio"}
        )

        assert jugador_recuperado == jugador

    def test_actualizar_jugador(self, mock_mongodb):
        jugador_original = {
            "Player": "Jugador Ficticio",
            "Position": "MF",
            "Squad": "Equipo Ficticio",
            "Age": 25,
            "Season": "2324"
        }

        mock_mongodb._mock_coleccion.find_one.return_value = jugador_original

        jugador_recuperado = mock_mongodb.find_one(
            PLAYERS_COLLECTION,
            {"Player": "Jugador Ficticio"}
        )

        assert jugador_recuperado == jugador_original

        mock_mongodb.update_one(
            PLAYERS_COLLECTION,
            {"Player": "Jugador Ficticio"},
            {"$set": {"Age": 26, "Squad": "Nuevo Equipo"}}
        )

        mock_mongodb._mock_coleccion.update_one.assert_called_with(
            {"Player": "Jugador Ficticio"},
            {"$set": {"Age": 26, "Squad": "Nuevo Equipo"}}
        )

        jugador_actualizado = {
            "Player": "Jugador Ficticio",
            "Position": "MF",
            "Squad": "Nuevo Equipo",
            "Age": 26,
            "Season": "2324"
        }
        mock_mongodb._mock_coleccion.find_one.return_value = jugador_actualizado

        jugador_recuperado = mock_mongodb.find_one(
            PLAYERS_COLLECTION,
            {"Player": "Jugador Ficticio"}
        )

        assert jugador_recuperado["Age"] == 26
        assert jugador_recuperado["Squad"] == "Nuevo Equipo"

    def test_buscar_varios_jugadores(self, mock_mongodb):
        jugadores = [
            {
                "Player": "Jugador 1",
                "Position": "MF",
                "Squad": "Equipo A",
                "Age": 25,
                "Season": "2324"
            },
            {
                "Player": "Jugador 2",
                "Position": "FW",
                "Squad": "Equipo B",
                "Age": 28,
                "Season": "2324"
            },
            {
                "Player": "Jugador 3",
                "Position": "DF",
                "Squad": "Equipo A",
                "Age": 22,
                "Season": "2324"
            }
        ]

        mock_mongodb._mock_coleccion.find.return_value = jugadores

        cursor = mock_mongodb.find(
            PLAYERS_COLLECTION,
            {"Squad": "Equipo A"}
        )

        mock_mongodb._mock_coleccion.find.assert_called_with(
            {"Squad": "Equipo A"},
            {}
        )

        jugadores_recuperados = list(cursor)

        assert len(jugadores_recuperados) == 3
        assert jugadores_recuperados == jugadores