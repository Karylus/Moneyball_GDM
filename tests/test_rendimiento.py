import pytest
import os
import sys
import time
import numpy as np
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.main import evaluar_con_agente, calcular_matrices_flpr
from src.core.logica_consenso import calcular_matriz_similitud, calcular_cr
from src.core.logica_ranking import calcular_ranking_jugadores

class TestRendimiento:
    @pytest.fixture
    def agentes_simulados(self):
        agentes = []
        for i in range(3):
            agente = MagicMock()
            agente.invoke.return_value = {
                "output": f"""```CSV
                            Jugador,Técnica,Físico,Táctico,Mental
                            Jugador1,Muy Alto,Alto,Muy Alto,Alto
                            Jugador2,Medio,Muy Alto,Alto,Medio
                            Jugador3,Alto,Medio,Medio,Muy Alto
                            ```"""
            }
            agentes.append(agente)
        return agentes

    @pytest.fixture
    def datos_prueba(self):
        return {
            "jugadores": ["Jugador1", "Jugador2", "Jugador3"],
            "criterios": ["Técnica", "Físico", "Táctico", "Mental"],
            "valores_linguisticos": ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"],
            "consenso_minimo": 0.7
        }

    def test_rendimiento_evaluacion(self, agentes_simulados, datos_prueba):
        jugadores = datos_prueba["jugadores"]
        criterios = datos_prueba["criterios"]
        valores_linguisticos = datos_prueba["valores_linguisticos"]
        consenso_minimo = datos_prueba["consenso_minimo"]

        tiempos = []

        for i in range(5):
            inicio = time.time()
            matrices = {}
            for j, agente in enumerate(agentes_simulados):
                prompt = f"""Evalúa a los jugadores {', '.join(jugadores)} según los criterios: {', '.join(criterios)}.
                Usa solo estos valores lingüísticos: {', '.join(valores_linguisticos)}.
                Responde en formato CSV con encabezados."""
                matriz, _ = evaluar_con_agente(
                    agente,
                    prompt,
                    jugadores,
                    criterios,
                    valores_linguisticos,
                    f"Agente{j+1}"
                )
                matrices[f"Agente{j+1}"] = matriz

            flpr_matrices = calcular_matrices_flpr(matrices, criterios)
            matrices_similitud = []
            nombres = list(flpr_matrices.keys())

            for j in range(len(nombres)):
                for k in range(j+1, len(nombres)):
                    matriz_similitud = calcular_matriz_similitud(
                        flpr_matrices[nombres[j]],
                        flpr_matrices[nombres[k]]
                    )
                    matrices_similitud.append(matriz_similitud)

            cr, consenso_alcanzado = calcular_cr(matrices_similitud, consenso_minimo)
            flpr_colectiva = np.mean([flpr for flpr in flpr_matrices.values()], axis=0)
            ranking = calcular_ranking_jugadores(flpr_colectiva, jugadores)

            fin = time.time()
            total = fin - inicio
            tiempos.append(total)
            print(f"Ejecución {i+1}: {total:.2f} segundos")

        tiempo_medio = np.mean(tiempos)
        tiempo_min = np.min(tiempos)
        tiempo_max = np.max(tiempos)
        desviacion = np.std(tiempos)

        print(f"\nEstadísticas de rendimiento:")
        print(f"Tiempo medio: {tiempo_medio:.2f} segundos")
        print(f"Tiempo mínimo: {tiempo_min:.2f} segundos")
        print(f"Tiempo máximo: {tiempo_max:.2f} segundos")
        print(f"Desviación estándar: {desviacion:.2f} segundos")

        tiempo_por_jugador = tiempo_medio / len(jugadores)
        assert tiempo_por_jugador < 10, f"El tiempo medio por jugador ({tiempo_por_jugador:.2f} s) excede el límite aceptable (10 s)"

        for i, tiempo in enumerate(tiempos):
            assert abs(tiempo - tiempo_medio) <= 3 * desviacion, f"La ejecución {i+1} tiene un tiempo anómalo ({tiempo:.2f} s)"