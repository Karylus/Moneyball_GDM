import sys
import os
import json
sys.path.append(os.path.abspath("src"))

from agentes.analista_datos import configurar_agente
from utils.logger import logger
from langchain_core.prompts import ChatPromptTemplate

def solicitar_lista(prompt_msg: str):
    # Se asume que el usuario ingresa elementos separados por comas
    entrada = input(prompt_msg).strip()
    # Se remueven espacios y se genera una lista
    return [elem.strip() for elem in entrada.split(",") if elem.strip()]

if __name__ == "__main__":
    logger.info("Iniciando agente experto...")
    agente = configurar_agente()
    logger.info("Agente listo.")

    jugadores = solicitar_lista("Ingrese los nombres de los jugadores (separados por comas): ")

    criterios = solicitar_lista("Ingrese los criterios de evaluación (por ejemplo, velocidad, técnica, física) separados por comas: ")

    prompt_template = ChatPromptTemplate.from_messages([
        (
            "system",
            "Eres un analista de fútbol experto en evaluar jugadores. "
            "Tu deber es solamente asignar una calificación del 0 al 1 a cada jugador para cada criterio proporcionado, usa 3 decimales siempre. "
            "No compares los jugadores entre sí; evalúalos individualmente. "
            
            "DEBES devolver la respuesta en formato CSV EXACTO, con los siguientes requerimientos:\n\n"
            "- La salida debe comenzar con la línea EXACTA: ```csv\n\n"
            "- La primera línea debe ser el encabezado con las columnas: Jugador,Velocidad,Técnica,Resistencia\n"
            "- Cada línea posterior debe contener el nombre del jugador y las calificaciones (números enteros del 1 al 5) para cada criterio, separadas por comas, sin espacios extra.\n"
            "- La salida debe finalizar con una línea que contenga solo ```\n\n"
            "Ejemplo de salida EXACTA:\n"
            "```csv\n"
            "Jugador,Velocidad,Técnica,Resistencia\n"
            "Vinicius Jr,5,4,3\n"
            "Mbappé,5,5,4\n"
            "Haaland,4,5,5\n"
            "```\n\n"
            
            "Si no puedes generar la salida en ese formato EXACTO, responde con: 'ERROR: Formato CSV no válido'."
            "Si no tienes suficiente información para evaluar a un jugador, responde con 'Datos no disponibles'. "
            "Si recibes una calificación fuera del rango 0-1, ignora la evaluación y responde con 'Datos no disponibles'."
        ),
        (
            "user",
            "Dado el listado de jugadores: {jugadores} y los criterios: {criterios}, "
            "asigna una calificación (del 0 al 1) para cada jugador en cada criterio, 3 decimales. "
            "Devuelve el resultado en el formato CSV EXACTO descrito."
            "No me des las estadísticas ni un análisis, solo la tabla CSV. "
        )
    ])

    prompt = prompt_template.format(jugadores=jugadores, criterios=criterios)
    respuesta_agente = agente.invoke({"input": prompt})

    output_agente = respuesta_agente.get("output", "No hay respuesta")
    print("\n=== Calificaciones del Agente ===")
    print(output_agente)


    print("\nAhora, ingresa tus calificaciones (del 0 al 1) para cada jugador en cada criterio:")
    matriz_usuario = []
    for jugador in jugadores:
        califs_jugador = []
        for criterio in criterios:
            while True:
                try:
                    calif = float(input(f"Calificación para {jugador} en {criterio}: ").strip())
                    if 0 <= calif <= 1:
                        califs_jugador.append(calif)
                        break
                    else:
                        print("La calificación debe estar entre 0 y 1.")
                except ValueError:
                    print("Por favor, ingrese un número válido.")
        matriz_usuario.append(califs_jugador)

    resultado_usuario = {
        "jugadores": jugadores,
        "criterios": criterios,
        "calificaciones_usuario": matriz_usuario
    }
    print("\n=== Calificaciones del Usuario ===")
    print(json.dumps(resultado_usuario, indent=2, ensure_ascii=False))

