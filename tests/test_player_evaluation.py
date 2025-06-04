import pytest
import os
import sys
import pandas as pd
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_management.data_loader import cargar_estadisticas_jugadores
from src.agentes.analista_qwen import configurar_agente as configurar_agente_qwen
from src.main import evaluar_con_agente

class TestEvaluacionJugador:
    """
    Prueba de evaluación individual de jugadores

    Objetivo:
    Validar que el sistema extrae correctamente los datos de un jugador y
    genera un informe coherente usando los agentes LLM.
    """

    @pytest.fixture
    def datos_jugador_simulado(self):
        datos_jugador = pd.DataFrame({
            'Player': ['Luka Modric'],
            'Position': ['MF'],
            'Squad': ['Real Madrid'],
            'Age': [37],
            'MP': [30],
            'Starts': [20],
            'Min': [1800],
            'Gls': [5],
            'Ast': [8],
            'PK': [1],
            'PKatt': [1],
            'CrdY': [3],
            'CrdR': [0],
            'xG': [4.2],
            'npxG': [3.5],
            'xAG': [7.8],
            'SCA': [85],
            'GCA': [12],
            'Cmp': [1200],
            'Att': [1350],
            'Cmp%': [88.9],
            'Prog': [150],
            'normalized_name': ['luka modric']
        })
        return datos_jugador

    @pytest.fixture
    def agente_simulado(self):
        agente = MagicMock()
        agente.invoke.return_value = {
            "output": """Aquí está mi análisis del jugador:

            ```CSV
            Jugador,Técnica,Físico,Táctico,Mental
            Luka Modric,Excelente,Bueno,Excelente,Excelente
            ```
            
            
            Luka Modric es un centrocampista experimentado con excelente visión de juego y técnica.
            A pesar de su edad, mantiene un buen nivel físico. Su inteligencia táctica y liderazgo
            son excepcionales, lo que le permite seguir siendo influyente en el mediocampo del Real Madrid."""
        }
        return agente

    @patch('src.data_management.data_loader.cargar_estadisticas_jugadores')
    @patch('src.agentes.analista_qwen.configurar_agente')
    def test_evaluacion_jugador(self, mock_configurar_agente, mock_cargar_estadisticas, datos_jugador_simulado, agente_simulado):
        """
        Prueba que el sistema evalúa correctamente a un jugador individual
        """
        mock_cargar_estadisticas.return_value = datos_jugador_simulado
        mock_configurar_agente.return_value = agente_simulado

        jugador = "Luka Modric"
        criterios = ["Técnica", "Físico", "Táctico", "Mental"]
        valores_linguisticos = ["Pobre", "Regular", "Bueno", "Muy Bueno", "Excelente"]

        prompt = f"""Evalúa al jugador {jugador} según los siguientes criterios: {', '.join(criterios)}.
        Usa solo estos valores lingüísticos: {', '.join(valores_linguisticos)}.
        Responde en formato CSV con encabezados."""

        matriz, output = evaluar_con_agente(
            agente_simulado,
            prompt,
            [jugador],
            criterios,
            valores_linguisticos,
            "TestAgent"
        )

        assert agente_simulado.invoke.called, "No se invocó al agente LLM"
        assert len(matriz) == 1, "La matriz de evaluación debe tener una fila"
        assert len(matriz[0]) == len(criterios), "La matriz debe tener una columna por criterio"

        for valor in matriz[0]:
            assert valor in valores_linguisticos, f"El valor '{valor}' no está en la lista de valores lingüísticos"

        assert jugador in output, f"El nombre del jugador '{jugador}' no aparece en el output"
        for criterio in criterios:
            assert criterio in output, f"El criterio '{criterio}' no aparece en el output"