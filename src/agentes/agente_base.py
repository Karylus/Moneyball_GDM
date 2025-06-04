from langchain.agents import initialize_agent, AgentType
from langchain_core.tools import tool
from langchain.memory import ConversationBufferMemory
from langchain.prompts import MessagesPlaceholder
from src.core.herramientas_análisis import *
from src.data_management.data_loader import cargar_explicacion_estadisticas
from abc import ABC, abstractmethod
from typing import List, Any, Dict, Type


@tool
def analizador_jugador(jugador: str):
    """
    Obtiene las estadísticas de un solo jugador.

    :param jugador: Nombre del único jugador a buscar.
    :return: Un JSON con la información del jugador.
    """
    return obtener_info_jugador(jugador)


@tool
def analizador_jugadores(jugadores: list):
    """
    Obtiene las estadísticas de múltiples jugadores con una sola llamada.

    :param jugadores: Lista de nombres de jugadores a buscar.
    :return: Un JSON con la información de todos los jugadores solicitados.
    """
    return obtener_info_jugadores(jugadores)


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
    return listar_jugadores_por_posicion_y_precio(posicion, precio_max)


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

    df_filtrado = df[df['stat_lower'].isin(query_lower)]

    explicaciones = [
        f"{row['stat']}: {row['description']}"
        for _, row in df_filtrado.iterrows()
    ]

    no_encontradas = [q for q in query if q.lower() not in df_filtrado['stat_lower'].values]

    if no_encontradas:
        explicaciones.append(f"No se encontraron las siguientes estadísticas: {', '.join(no_encontradas)}")

    return explicaciones


class BaseAgent(ABC):
    """
    Clase base para los agentes de análisis.
    Define la estructura común y los métodos que todos los agentes deben implementar.
    """
    
    def __init__(self, model_name: str, temperature: float, tools: List = None, **kwargs):
        """
        Inicializa un agente con los parámetros básicos.
        
        Args:
            model_name: Nombre del modelo a utilizar
            temperature: Temperatura para la generación de texto
            tools: Lista de herramientas que el agente puede utilizar
            **kwargs: Parámetros adicionales específicos del modelo
        """
        self.model_name = model_name
        self.temperature = temperature
        self.tools = tools or [analizador_jugadores]
        self.kwargs = kwargs
        self.llm = self.configurar_llm()
        
    @abstractmethod
    def configurar_llm(self):
        """
        Configura y devuelve el modelo.
        """
        pass
    
    def configurar_agente(self):
        """
        Configura y devuelve el agente con el LLM y las herramientas especificadas.
        """
        chat_history = MessagesPlaceholder(variable_name="chat_history")
        memoria = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        
        return initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            memory=memoria,
            max_iterations=10,
            verbose=True,
            handle_parsing_errors=True,
            agent_kwargs={
                "memory_prompts": [chat_history],
                "input_variables": ["input", "agent_scratchpad", "chat_history"]
            }
        )