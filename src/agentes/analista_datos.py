from langchain.agents import initialize_agent, AgentType
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from src.agentes.herramientas_analisis import *
from langchain.memory import ConversationBufferMemory
from langchain.prompts import MessagesPlaceholder


@tool
def analizador_jugador(jugador: str):
    """
    Obtiene las estadísticas de un solo jugador.

    :param jugador: Nombre del único jugador a buscar.
    :return: Un JSON con la información del jugador.
    """
    return obtener_info_jugador(jugador)


@tool()
def comparador_jugadores(jugador1: str, jugador2: str):
    """Compara a dos jugadores."""
    return comparar_jugadores(jugador1, jugador2)


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


@tool()
def explicar_estadisticas(query: list) -> list:
    """
    Explica el significado de las estadísticas de la query.

    :param query: Lista de estadísticas a consultar.
    :return: Una lista de cadenas con el nombre de la estadística y su explicación.
    """
    df = cargar_explicacion_estadisticas()

    if isinstance(df, str):
        return ["Error al cargar los datos."]

    query_lower = [q.lower() for q in query]
    df['stat_lower'] = df['stat'].str.lower()

    # Filtrar estadísticas encontradas
    df_filtrado = df[df['stat_lower'].isin(query_lower)]

    # Crear lista de explicaciones encontradas
    explicaciones = [
        f"{row['stat']}: {row['description']}"
        for _, row in df_filtrado.iterrows()
    ]

    # Identificar estadísticas no encontradas
    no_encontradas = [q for q in query if q.lower() not in df_filtrado['stat_lower'].values]

    if no_encontradas:
        explicaciones.append(f"No se encontraron las siguientes estadísticas: {', '.join(no_encontradas)}")

    return explicaciones


MODEL_NAME = "mistral-nemo:12b"
TEMPERATURE = 0.2
TOP_P = 0.1
LISTA_TOOLS = [analizador_jugador]


def configurar_llm() -> ChatOllama:
    """Configura y devuelve el modelo en modo chat."""
    return ChatOllama(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        num_ctx=32000
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
