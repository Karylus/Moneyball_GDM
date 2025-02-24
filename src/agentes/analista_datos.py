from langchain.agents import initialize_agent, AgentType
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from src.agentes.herramientas_analisis import *


@tool
def analizador_equipos(equipo: str):
    """Obtiene estadísticas de un equipo."""
    return obtener_estadisticas_equipo(equipo)


@tool
def analizador_jugadores(jugador1: str):
    """Obtiene estadísticas de un jugador."""
    return obtener_info_jugador(jugador1)


@tool()
def comparador_jugadores(jugador1: str, jugador2: str):
    """Compara a dos jugadores."""
    return comparar_jugadores(jugador1, jugador2)


MODEL_NAME = "phi4:latest"
TEMPERATURE = 0.2
TOP_P = 0.1
LISTA_TOOLS = [analizador_equipos, analizador_jugadores, comparador_jugadores]


def configurar_llm() -> ChatOllama:
    """Configura y retorna el modelo de lenguaje en modo chat con herramientas enlazadas."""
    return ChatOllama(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        num_ctx=4096,
    )


def configurar_agente():
    """Configura y retorna el agente sin mezclar la lógica de ejecución."""
    llm = configurar_llm()
    return initialize_agent(
        tools=LISTA_TOOLS,
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        max_iterations=10,
        verbose=True
    )
