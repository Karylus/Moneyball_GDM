import sys
import os
sys.path.append(os.path.abspath("src"))

from agentes.analista_datos import configurar_agente
from utils.logger import logger

if __name__ == "__main__":
    logger.info("Iniciando agente experto...")
    agente = configurar_agente()
    logger.info("Agente listo.")

    casos_prueba = [
        #"¿Quién es mejor en regates, Vinícius junior  o kylian Mbappé?",
        #"Dame informacion de Trent Alexander Arnold",
        "Cuantos Tackles - Att 3rd tiene Vinicius Junior"
    ]

    for caso in casos_prueba:
        input("\nPresiona Enter para ejecutar la siguiente prueba...")
        logger.info(f"\n{'=' * 50}\n[Consulta]: {caso}")
        try:
            mensaje = [
                (
                    "system",
                    "Eres un analista de datos experto de la UEFA con acceso a estadísticas detalladas. "
                    "Responde ÚNICAMENTE con los formatos de acción específicos requeridos por LangChain. "
                    "Mantén las respuestas precisas y basadas en datos. "
                    "Si no tienes información, indica claramente 'Datos no disponibles'.\n"
                    "Instrucciones clave:\n"
                    "1. Valida siempre la entrada antes de procesar\n"
                    "2. Usa exclusivamente las herramientas proporcionadas\n"
                    "3. Formatea números con precisión decimal cuando sea relevante\n"
                    "4. Responde con los datos de la tool usada, no resumas ni dejes ningún dato fuera."
                ),
                ("human", caso)
            ]

            respuesta = agente.invoke(mensaje)

            logger.info(f"[Respuesta]:\n{respuesta.get("output", "No hay respuesta")}")
        except Exception as e:
            logger.error(f"Error en consulta: {str(e)}")