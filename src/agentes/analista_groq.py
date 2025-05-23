from langchain_groq import ChatGroq
from src.agentes.base_agent import BaseAgent, analizador_jugadores
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

# Configurar API key
if "GROQ_API_KEY" not in os.environ:
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")


class AgenteGroq(BaseAgent):
    """
    Implementación del agente de análisis usando el modelo Groq.
    """

    def __init__(self):
        """
        Inicializa el agente Groq con sus parámetros específicos.
        """
        model_name = "llama-3.3-70b-versatile"
        temperature = 0.2
        tools = [analizador_jugadores]

        super().__init__(
            model_name=model_name,
            temperature=temperature,
            tools=tools
        )

    def configurar_llm(self):
        """
        Configura y devuelve el modelo Groq en modo chat.
        """
        return ChatGroq(
            model=self.model_name,
            temperature=self.temperature
        )


def configurar_agente():
    """
    Función de fábrica para mantener compatibilidad con el código existente.
    """
    agente = AgenteGroq()
    return agente.configurar_agente()
