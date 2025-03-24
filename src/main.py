import sys
import os
sys.path.append(os.path.abspath("src"))

from agentes.analista_datos import configurar_agente
from utils.logger import logger
from langchain_core.prompts import ChatPromptTemplate

if __name__ == "__main__":
    logger.info("Iniciando agente experto...")
    agente = configurar_agente()  # Asegúrate de que en la configuración se incluya memoria (p.ej., ConversationBufferMemory)
    logger.info("Agente listo.")

    # Obtención de datos iniciales
    posicion = input("Qué posición necesitas para tu equipo: ").strip()
    precio_max = input("Ingrese el precio máximo en millones: ").strip()

    # Prompt inicial
    prompt_template = ChatPromptTemplate([
        (
            "system",
            "Eres un analista de datos experto de la UEFA con acceso a estadísticas detalladas. "
            "Responde ÚNICAMENTE con los formatos de acción específicos requeridos por LangChain. "
            "Mantén las respuestas precisas y basadas en datos. "
            "No traduzcas los nombres de las posiciones al español, mantenlas en inglés. "
            "Al precio máximo no debes añadirle ningún 0. "
            "Si no tienes información, indica claramente 'Datos no disponibles'.\n\n"
            "Instrucciones clave:\n"
            "- Usa los datos de la tool para analizar los jugadores en tu respuesta.\n"
            "- Usa exclusivamente las herramientas proporcionadas (no realices búsquedas externas).\n"
            "- Formatea números con dos decimales cuando sea relevante (ej: 12.34)."
        ),
        (
            "user",
            "Analiza qué jugadores son {posicion} y tienen precio máximo de {precio_max} millones. Dime sus estadísticas."
        )
    ])

    prompt = prompt_template.format(posicion=posicion, precio_max=int(precio_max))
    respuesta = agente.invoke({"input": prompt})
    output = respuesta.get("output", "No hay respuesta")
    logger.info(f"[Respuesta]:\n{output}")
    print("Respuesta del agente:")
    print(output)

    print("\n(escribe 'exit' o 'salir' para terminar).")
    while True:
        user_input = input("Usuario: ").strip()
        if user_input.lower() in ["exit", "salir"]:
            break

        respuesta = agente.invoke({"input": user_input})
        output = respuesta.get("output", "No hay respuesta")
        logger.info(f"[Respuesta]:\n{output}")
        print("Respuesta del agente:")
        print(output)
