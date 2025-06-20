from langchain_google_genai import ChatGoogleGenerativeAI
from src.agentes.agente_base import BaseAgent, analizador_jugadores, explicar_estadisticas
from dotenv import load_dotenv
import os

load_dotenv()


if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")


class AgenteGemini(BaseAgent):
    """
    Implementación del agente con modelo Gemini.
    """

    def __init__(self):
        """
        Inicializa el agente Gemini con sus parámetros específicos.
        """
        model_name = "gemini-2.0-flash"
        temperature = 0.2
        top_p = 0.1
        tools = [analizador_jugadores, explicar_estadisticas]

        super().__init__(
            model_name=model_name,
            temperature=temperature,
            tools=tools,
            top_p=top_p
        )

    def configurar_llm(self):
        """
        Configura y devuelve el modelo Gemini en modo chat.
        """
        return ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            top_p=self.kwargs.get('top_p', 0.1),
            max_tokens=None,
            timeout=None
        )


def configurar_agente():
    agente = AgenteGemini()
    return agente.configurar_agente()
