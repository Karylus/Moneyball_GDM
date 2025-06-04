import pytest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.main import evaluar_con_agente, calcular_matrices_flpr
from src.core.logica_consenso import calcular_matriz_similitud, calcular_cr
from src.core.logica_ranking import calcular_ranking_jugadores

class TestExperienciaUsuario:
    """
    Prueba de usuario (experto simulando un entrenador)

    Objetivo:
    Evaluar la utilidad percibida del sistema por un usuario humano.
    """

    @pytest.fixture
    def agentes_simulados(self):
        agente1 = MagicMock()
        agente1.invoke.return_value = {
            "output": """```CSV
            Jugador,Técnica,Físico,Táctico,Mental
            Rodri,Alto,Alto,Muy Alto,Muy Alto
            Tchouaméni,Medio,Muy Alto,Alto,Medio
            Zubimendi,Alto,Medio,Muy Alto,Alto
            ```
            
            Rodri es un mediocentro completo con excelente visión de juego y capacidad táctica. Su posicionamiento es excepcional.
            Tchouaméni destaca por su físico y capacidad de recuperación, aunque técnicamente tiene margen de mejora.
            Zubimendi es muy equilibrado, con gran inteligencia táctica y buena técnica, aunque físicamente no es tan dominante."""
        }

        agente2 = MagicMock()
        agente2.invoke.return_value = {
            "output": """```CSV
            Jugador,Técnica,Físico,Táctico,Mental
            Rodri,Muy Alto,Medio,Muy Alto,Alto
            Tchouaméni,Medio,Muy Alto,Medio,Medio
            Zubimendi,Alto,Alto,Alto,Alto
            ```
            
            Según los datos estadísticos, Rodri lidera en métricas de pases progresivos y acciones defensivas exitosas.
            Tchouaméni destaca en duelos ganados y recuperaciones, pero sus métricas de progresión son inferiores.
            Zubimendi muestra un perfil equilibrado en todas las métricas, sin destacar extraordinariamente en ninguna."""
        }

        agente3 = MagicMock()
        agente3.invoke.return_value = {
            "output": """```CSV
            Jugador,Técnica,Físico,Táctico,Mental
            Rodri,Alto,Alto,Muy Alto,Muy Alto
            Tchouaméni,Alto,Muy Alto,Medio,Alto
            Zubimendi,Muy Alto,Medio,Alto,Alto
            ```
            
            Rodri es el mediocentro más completo, con capacidad para organizar el juego y defender.
            Tchouaméni tiene un potencial físico extraordinario y ha mejorado técnicamente.
            Zubimendi tiene una técnica exquisita y una comprensión del juego que le permite anticiparse a situaciones."""
        }

        return [agente1, agente2, agente3]

    @pytest.fixture
    def datos_prueba(self):
        return {
            "jugadores": ["Rodri", "Tchouaméni", "Zubimendi"],
            "criterios": ["Técnica", "Físico", "Táctico", "Mental"],
            "valores_linguisticos": ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"],
            "consenso_minimo": 0.75
        }

    def test_flujo_entrenador(self, agentes_simulados, datos_prueba):
        jugadores = datos_prueba["jugadores"]
        criterios = datos_prueba["criterios"]
        valores_linguisticos = datos_prueba["valores_linguisticos"]
        consenso_minimo = datos_prueba["consenso_minimo"]

        matrices = {}
        informes_agentes = {}

        for i, agente in enumerate(agentes_simulados):
            nombre_agente = ["Analista Técnico", "Analista de Datos", "Scout"][i]
            prompt = f"""Evalúa a los mediocentros {', '.join(jugadores)} según los criterios: {', '.join(criterios)}.
            Usa solo estos valores lingüísticos: {', '.join(valores_linguisticos)}.
            Responde en formato CSV con encabezados y añade un breve análisis de cada jugador."""

            matriz, output = evaluar_con_agente(
                agente,
                prompt,
                jugadores,
                criterios,
                valores_linguisticos,
                nombre_agente
            )
            matrices[nombre_agente] = matriz
            informes_agentes[nombre_agente] = output

        for nombre, informe in informes_agentes.items():
            for jugador in jugadores:
                assert jugador in informe, f"El informe del {nombre} no menciona a {jugador}"
            assert len(informe.split('\n')) > len(jugadores) + 5, f"El informe del {nombre} parece demasiado corto"
            assert "ERROR" not in informe, f"El informe del {nombre} contiene errores"
            assert "undefined" not in informe, f"El informe del {nombre} contiene valores indefinidos"
            assert "null" not in informe, f"El informe del {nombre} contiene valores nulos"

        matrices["Entrenador"] = [
            ["Alto", "Medio", "Muy Alto", "Alto"],
            ["Medio", "Muy Alto", "Medio", "Medio"],
            ["Muy Alto", "Medio", "Alto", "Muy Alto"]
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

        import numpy as np
        flpr_colectiva = np.mean([flpr for flpr in flpr_matrices.values()], axis=0)
        ranking = calcular_ranking_jugadores(flpr_colectiva, jugadores)

        assert len(ranking) == len(jugadores), "El ranking no incluye a todos los jugadores"
        valores_ranking = [valor for _, valor in ranking]
        assert len(set(valores_ranking)) == len(valores_ranking), "Hay empates en el ranking"
        assert isinstance(cr, float), "El nivel de consenso no es un número"
        assert 0 <= cr <= 1, "El nivel de consenso no está en el rango [0,1]"

        mejor_jugador = ranking[0][0]
        print(f"\nEl sistema recomienda fichar a {mejor_jugador} con una puntuación de {ranking[0][1]:.3f}")
        print(f"Nivel de consenso entre expertos: {cr:.3f} ({'Suficiente' if consenso_alcanzado else 'Insuficiente'})")

        assert True, "El flujo de usuario se completó correctamente"