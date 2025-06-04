from langchain_ollama import ChatOllama
from src.agentes.agente_base import BaseAgent, analizador_jugadores


class AgenteQwen(BaseAgent):
    """
    Implementación del agente con modelo Qwen.
    """

    def __init__(self):
        """
        Inicializa el agente Qwen con sus parámetros específicos.
        """
        model_name = "qwen3:8b"
        temperature = 0.7
        top_p = 0.95
        tools = [analizador_jugadores]

        super().__init__(
            model_name=model_name,
            temperature=temperature,
            tools=tools,
            top_p=top_p
        )

    def configurar_llm(self):
        """
        Configura y devuelve el modelo Qwen en modo chat.
        """
        return ChatOllama(
            model=self.model_name,
            temperature=self.temperature,
            top_p=self.kwargs.get('top_p', 0.95),
            num_ctx=38000
        )


def configurar_agente():
    agente = AgenteQwen()
    return agente.configurar_agente()
