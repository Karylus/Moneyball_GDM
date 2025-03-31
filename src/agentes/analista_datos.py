from langchain.agents import initialize_agent, AgentType
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from src.agentes.herramientas_analisis import *
from langchain.memory import ConversationBufferMemory
from langchain.prompts import MessagesPlaceholder


@tool
def analizador_jugadores(jugador1: str):
    """Obtiene estadísticas de un jugador."""
    return obtener_info_jugador(jugador1)


#@tool()
#def comparador_jugadores(jugador1: str, jugador2: str):
#    """Compara a dos jugadores."""
#    return comparar_jugadores(jugador1, jugador2)


@tool()
def encontrar_jugadores_precio(posicion: str, precio_max: int) -> str:
    """
    Encuentra los jugadores para la posición dada en el rango de precio_max.

    Parámetros:
    - posicion (str): La posición a buscar (ej. "Delantero", "Centrocampista").
    - precio_max (int): Precio máximo permitido para el fichaje.

    Return:
    - Un JSON con la información de los jugadores encontrados.
    """
    return listar_jugadores_por_posicion_y_precio(posicion,precio_max)


MODEL_NAME = "mistral-nemo:12b"
TEMPERATURE = 0.2
TOP_P = 0.1
LISTA_TOOLS = [analizador_jugadores, encontrar_jugadores_precio]


def configurar_llm() -> ChatOllama:
    """Configura y devuelve el modelo en modo chat."""
    return ChatOllama(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        num_ctx=4096,
    )


def configurar_agente():
    """Configura y devuelve el agente."""
    llm = configurar_llm()

    chat_history = MessagesPlaceholder(variable_name="chat_history")
    memoria = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    return initialize_agent(
        tools=LISTA_TOOLS,
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        memory=memoria,
        max_iterations=10,
        verbose=True,
        agent_kwargs={
            "memory_prompts": [chat_history],
            "input_variables": ["input", "agent_scratchpad", "chat_history"]
        }
    )
