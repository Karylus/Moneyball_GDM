import pytest
import os
import sys
import numpy as np
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.logica_consenso import calcular_matriz_similitud, calcular_consenso_nivel1, calcular_cr
from src.core.fuzzy_matrices import generar_flpr, calcular_flpr_comun
from src.main import evaluar_con_agente, calcular_matrices_flpr

class TestConsenso:
    """
    Prueba de consenso en la selección de jugadores
    """

    @pytest.fixture
    def agentes_simulados(self):
        agente1 = MagicMock()
        agente1.invoke.return_value = {
            "output": """```CSV
            Jugador,Técnica,Físico,Táctico,Mental
            Jugador1,Muy Alto,Muy Alto,Muy Alto,Muy Alto
            Jugador2,Muy Bajo,Muy Bajo,Muy Bajo,Muy Bajo
            Jugador3,Muy Bajo,Muy Bajo,Muy Bajo,Muy Bajo
            ```"""
        }

        agente2 = MagicMock()
        agente2.invoke.return_value = {
            "output": """```CSV
            Jugador,Técnica,Físico,Táctico,Mental
            Jugador1,Muy Bajo,Muy Bajo,Muy Bajo,Muy Bajo
            Jugador2,Muy Alto,Muy Alto,Muy Alto,Muy Alto
            Jugador3,Muy Bajo,Muy Bajo,Muy Bajo,Muy Bajo
            ```"""
        }

        agente3 = MagicMock()
        agente3.invoke.return_value = {
            "output": """```CSV
            Jugador,Técnica,Físico,Táctico,Mental
            Jugador1,Muy Bajo,Muy Bajo,Muy Bajo,Muy Bajo
            Jugador2,Muy Bajo,Muy Bajo,Muy Bajo,Muy Bajo
            Jugador3,Muy Alto,Muy Alto,Muy Alto,Muy Alto
            ```"""
        }

        return [agente1, agente2, agente3]

    @pytest.fixture
    def valores_linguisticos(self):
        return ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]

    def test_detectar_bajo_consenso(self, agentes_simulados, valores_linguisticos):
        jugadores = ["Jugador1", "Jugador2", "Jugador3"]
        criterios = ["Técnica", "Físico", "Táctico", "Mental"]
        consenso_minimo = 0.75

        matrices = {}
        for i, agente in enumerate(agentes_simulados):
            prompt = f"""Evalúa a los jugadores {', '.join(jugadores)} según los criterios: {', '.join(criterios)}.
            Usa solo estos valores lingüísticos: {', '.join(valores_linguisticos)}.
            Responde en formato CSV con encabezados."""

            matriz, _ = evaluar_con_agente(
                agente,
                prompt,
                jugadores,
                criterios,
                valores_linguisticos,
                f"Agente{i+1}"
            )
            matrices[f"Agente{i+1}"] = matriz

        matrices["Usuario"] = [
            ["Alto", "Medio", "Alto", "Muy Alto"],
            ["Medio", "Alto", "Medio", "Alto"],
            ["Muy Alto", "Medio", "Muy Alto", "Alto"]
        ]

        flpr_matrices = calcular_matrices_flpr(matrices, criterios)

        matrices_similitud = []
        nombres = list(flpr_matrices.keys())

        for i in range(len(nombres)):
            for j in range(i+1, len(nombres)):
                matriz_similitud = calcular_matriz_similitud(
                    flpr_matrices[nombres[i]],
                    flpr_matrices[nombres[j]]
                )
                matrices_similitud.append(matriz_similitud)

        cr, consenso_alcanzado = calcular_cr(matrices_similitud, consenso_minimo)

        assert not consenso_alcanzado, "El sistema debe detectar bajo consenso"
        assert cr < consenso_minimo, f"El nivel de consenso ({cr}) debe ser menor que el mínimo ({consenso_minimo})"

        nombres_flpr = list(flpr_matrices.keys())
        if not nombres_flpr:
            pytest.skip("No hay matrices FLPR para procesar la ronda de convergencia.")

        flpr_base_convergencia = flpr_matrices[nombres_flpr[0]].copy()

        num_matrices = len(flpr_matrices)
        if num_matrices > 0:
            flpr_objetivo_convergencia = np.zeros_like(flpr_matrices[nombres_flpr[0]])
            for nombre_flpr_actual in nombres_flpr:
                flpr_objetivo_convergencia += flpr_matrices[nombre_flpr_actual]
            flpr_objetivo_convergencia /= num_matrices
        else:
            flpr_objetivo_convergencia = flpr_base_convergencia

        flpr_matrices_ronda2 = {}
        for nombre in flpr_matrices:
            flpr_matrices_ronda2[nombre] = calcular_flpr_comun(
                flpr_matrices[nombre],
                flpr_objetivo_convergencia
            )

        matrices_similitud_ronda2 = []
        for i in range(len(nombres)):
            for j in range(i+1, len(nombres)):
                matriz_similitud = calcular_matriz_similitud(
                    flpr_matrices_ronda2[nombres[i]],
                    flpr_matrices_ronda2[nombres[j]]
                )
                matrices_similitud_ronda2.append(matriz_similitud)

        cr_ronda2, consenso_alcanzado_ronda2 = calcular_cr(matrices_similitud_ronda2, consenso_minimo)

        assert cr_ronda2 > cr, f"El consenso debe aumentar en la segunda ronda. Ronda1 CR: {cr}, Ronda2 CR: {cr_ronda2}"
        assert consenso_alcanzado_ronda2, f"El consenso debe alcanzarse en la segunda ronda. CR: {cr_ronda2}, Mínimo: {consenso_minimo}"