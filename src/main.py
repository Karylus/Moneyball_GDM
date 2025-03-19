import sys
import os

sys.path.append(os.path.abspath("src"))

from agentes.analista_datos import configurar_agente
from utils.logger import logger
from langchain_core.prompts import ChatPromptTemplate

if __name__ == "__main__":
    logger.info("Iniciando agente experto...")
    agente = configurar_agente()
    logger.info("Agente listo.")

    posicion = input("Qué posición necesitas para tu equipo: ").strip()

    while True:
        try:
            precio_max = input("Ingrese el precio máximo en millones: ").strip()
            break
        except ValueError:
            print("Por favor, ingrese un número válido para el precio.")

    prompt_template = ChatPromptTemplate([
        (
            "system",
            "Eres un analista de datos experto de la UEFA con acceso a estadísticas detalladas. "
            "Responde ÚNICAMENTE con los formatos de acción específicos requeridos por LangChain. "
            "Mantén las respuestas precisas y basadas en datos. "
            "No traduzcas los nombres de las posiciones al español, mantenlo en ingles."
            "El precio máximo no debes añadirle ningún 0."
            "Si no tienes información, indica claramente 'Datos no disponibles'.\n\n"
            "Instrucciones clave:\n"
            "- Valida la entrada: Verifica que la solicitud se refiera a datos relacionados con la UEFA (equipos, jugadores, partidos, torneos). "
            "Si la solicitud no es relevante para la UEFA, responde con 'Solicitud fuera del alcance'.\n"
            "- Usa exclusivamente las herramientas proporcionadas (no realices búsquedas externas).\n"
            "- Formatea números con dos decimales cuando sea relevante (ej: 12.34).\n"
            "- Formato de acción LangChain: Responde en formato JSON con la siguiente estructura:\n\n"
            "```json\n"
            "{{\n"
            "  \"action\": \"nombre_de_la_accion\",\n"
            "  \"action_input\": {{\n"
            "    \"parametro1\": \"valor1\",\n"
            "    \"parametro2\": \"valor2\"\n"
            "  }},\n"
            "  \"data_source\": \"Own\"\n"
            "}}\n"
            "```"
        ),
        (
            "user",
            "Encuentra el mejor jugador para la posición de {posicion} con un precio máximo de {precio_max} millones."
        )
    ])

    prompt = prompt_template.format(posicion=posicion, precio_max=str(precio_max))

    respuesta = agente.invoke({"input": prompt})

    output = respuesta.get("output", "No hay respuesta")
    logger.info(f"[Respuesta]:\n{output}")
    print("Respuesta del agente:")
    print(output)
