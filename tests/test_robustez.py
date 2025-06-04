import pytest
import os
import sys
import pandas as pd
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_management.data_loader import cargar_estadisticas_jugadores
from src.agentes.analista_qwen import configurar_agente as configurar_agente_qwen
from src.main import evaluar_con_agente

class TestRobustez:
    """
    Prueba de robustez ante datos faltantes

    Objetivo:
    Comprobar cómo reacciona el sistema si faltan estadísticas clave de un jugador.
    """

    @pytest.fixture
    def datos_jugador_completo(self):
        datos = pd.DataFrame({
            'Player': ['Jude Bellingham'],
            'Position': ['MF'],
            'Squad': ['Real Madrid'],
            'Age': [20],
            'MP': [30],
            'Starts': [28],
            'Min': [2520],
            'Gls': [15],
            'Ast': [7],
            'PK': [2],
            'PKatt': [2],
            'CrdY': [5],
            'CrdR': [0],
            'xG': [12.5],
            'npxG': [10.8],
            'xAG': [6.3],
            'SCA': [95],
            'GCA': [18],
            'Cmp': [1450],
            'Att': [1680],
            'Cmp%': [86.3],
            'Prog': [180],
            'normalized_name': ['jude bellingham']
        })
        return datos

    @pytest.fixture
    def datos_jugador_incompleto(self):
        datos = pd.DataFrame({
            'Player': ['Jude Bellingham'],
            'Position': ['MF'],
            'Squad': ['Real Madrid'],
            'Age': [20],
            'MP': [30],
            'Starts': [28],
            'Min': [2520],
            'Gls': [15],
            'Ast': [7],
            # Faltan xG y xAG
            'PK': [2],
            'PKatt': [2],
            'CrdY': [5],
            'CrdR': [0],
            'SCA': [95],
            'GCA': [18],
            'Cmp': [1450],
            'Att': [1680],
            'Cmp%': [86.3],
            'Prog': [180],
            'normalized_name': ['jude bellingham']
        })
        return datos

    @pytest.fixture
    def agente_simulado(self):
        agente = MagicMock()
        return agente

    @patch('src.data_management.data_loader.cargar_estadisticas_jugadores')
    def test_manejo_datos_faltantes(self, mock_cargar_estadisticas, agente_simulado, datos_jugador_completo, datos_jugador_incompleto):
        jugador = "Jude Bellingham"
        criterios = ["Técnica", "Físico", "Táctico", "Mental"]
        valores_linguisticos = ["Pobre", "Regular", "Bueno", "Muy Bueno", "Excelente"]

        # Caso 1: Datos completos
        mock_cargar_estadisticas.return_value = datos_jugador_completo
        agente_simulado.invoke.return_value = {
            "output": """```CSV
                        Jugador,Técnica,Físico,Táctico,Mental
                        Jude Bellingham,Excelente,Muy Bueno,Excelente,Excelente
                        ```
                        
                        
                        Jude Bellingham es un centrocampista excepcional con gran técnica y visión de juego. 
                        Sus estadísticas de xG (12.5) y xAG (6.3) demuestran su influencia en ataque.
                        Físicamente es muy potente y tácticamente muy inteligente."""
        }

        prompt_completo = f"""Evalúa al jugador {jugador} según los siguientes criterios: {', '.join(criterios)}.
        Usa solo estos valores lingüísticos: {', '.join(valores_linguisticos)}.
        Responde en formato CSV con encabezados."""

        matriz_completa, output_completo = evaluar_con_agente(
            agente_simulado,
            prompt_completo,
            [jugador],
            criterios,
            valores_linguisticos,
            "TestAgent"
        )

        # Caso 2: Datos incompletos
        mock_cargar_estadisticas.return_value = datos_jugador_incompleto
        agente_simulado.invoke.return_value = {
            "output": """```CSV
                        Jugador,Técnica,Físico,Táctico,Mental
                        Jude Bellingham,Muy Bueno,Muy Bueno,Muy Bueno,Muy Bueno
                        ```
                   
                        
                        Jude Bellingham muestra grandes cualidades como centrocampista.
                        Noto que faltan algunos datos importantes como xG y xAG, lo que dificulta una evaluación completa.
                        Basándome en los datos disponibles, parece ser un jugador muy completo."""
        }

        prompt_incompleto = f"""Evalúa al jugador {jugador} según los siguientes criterios: {', '.join(criterios)}.
        Usa solo estos valores lingüísticos: {', '.join(valores_linguisticos)}.
        Responde en formato CSV con encabezados."""

        matriz_incompleta, output_incompleto = evaluar_con_agente(
            agente_simulado,
            prompt_incompleto,
            [jugador],
            criterios,
            valores_linguisticos,
            "TestAgent"
        )

        assert len(matriz_completa) == 1, "La matriz con datos completos debe tener una fila"
        assert len(matriz_incompleta) == 1, "La matriz con datos incompletos debe tener una fila"
        assert len(matriz_completa[0]) == len(criterios), "La matriz completa debe tener una columna por criterio"
        assert len(matriz_incompleta[0]) == len(criterios), "La matriz incompleta debe tener una columna por criterio"

        for valor in matriz_completa[0] + matriz_incompleta[0]:
            assert valor in valores_linguisticos, f"El valor '{valor}' no está en la lista de valores lingüísticos"

        assert "falt" in output_incompleto.lower() or "missing" in output_incompleto.lower(), \
            "El sistema debería mencionar los datos faltantes en la evaluación"

        assert "error" not in output_incompleto.lower() or "exception" not in output_incompleto.lower(), \
            "El sistema no debería reportar errores graves ante datos faltantes"

        valores_mapeados = {"Pobre": 1, "Regular": 2, "Bueno": 3, "Muy Bueno": 4, "Excelente": 5}

        puntuacion_completa = sum(valores_mapeados[valor] for valor in matriz_completa[0])
        puntuacion_incompleta = sum(valores_mapeados[valor] for valor in matriz_incompleta[0])

        assert puntuacion_incompleta <= puntuacion_completa, \
            "La evaluación con datos incompletos debería ser igual o más conservadora"

        print("\nEvaluación con datos completos:")
        print(f"Matriz: {matriz_completa}")
        print(f"Puntuación total: {puntuacion_completa}")

        print("\nEvaluación con datos incompletos:")
        print(f"Matriz: {matriz_incompleta}")
        print(f"Puntuación total: {puntuacion_incompleta}")

        print("\nDiferencia de puntuación:", puntuacion_completa - puntuacion_incompleta)