import csv
import sys
import os
import json
from io import StringIO

sys.path.append(os.path.abspath("src"))

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

from agentes.analista_datos import configurar_agente
from utils.logger import logger
from utils.matrices import generar_flpr, calcular_flpr_comun
from langchain_core.prompts import ChatPromptTemplate

with open('src/data/fbref_stats_explained.json', 'r', encoding='utf-8') as f:
    explicaciones_stats = json.load(f)

explicaciones_formateadas = "\n".join([f"{clave}: {valor}" for clave, valor in explicaciones_stats.items() if not clave.startswith("_")])

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
            "Tu deber es asignar una calificación lingüística (Muy Bajo, Bajo, Medio, Alto, Muy Alto) a cada jugador dado para cada criterio proporcionado. "
            "No compares los jugadores entre sí; evalúalos individualmente. "
            "Responde en formato CSV\n "

            "Output format:\n\n"
            "1. La Primera linea es: ```csv\n"
            "2. El encabezado con los campos: Jugador, y la lista de todos los criterios separados por comas\n"
            "3. Una linea por cada jugador y las calificaciones lingüísticas para cada criterio, separadas por comas, sin espacios extra.\n"
            "4. Ultima linea: ```\n\n"

            "Si no puedes generar la salida en ese formato EXACTO, responde con: 'ERROR: Formato CSV no válido'."
        ),
        (
            "user",
            "Dado el listado de jugadores: {jugadores} y los criterios: {criterios}, "
            "asigna una calificación lingüística (Muy Bajo, Bajo, Medio, Alto, Muy Alto) para cada jugador en cada criterio. "
            "Devuelve el resultado en formato el CSV descrito."
        )
    ])

    prompt = prompt_template.format(jugadores=jugadores, criterios=criterios)
    respuesta_agente = agente.invoke({"input": prompt})

    output_agente = respuesta_agente.get("output", "No hay respuesta")
    print("\n=== Calificaciones del Agente ===")
    print(output_agente)

    matriz_agente = []
    try:
        csv_data = StringIO(output_agente.replace("```csv", "").replace("```", "").strip())
        reader = csv.DictReader(csv_data)

        for row in reader:
            row_normalizado = {k.lower().strip(): v for k, v in row.items()}

            calificaciones = []
            for criterio in criterios:
                if criterio in row_normalizado:
                    calificaciones.append(str(row_normalizado[criterio]))
                else:
                    print(
                        f"Advertencia: El criterio '{criterio}' no está presente en los datos del CSV.")
                    calificaciones.append(0.0)  # Valor predeterminado en caso de ausencia
            matriz_agente.append(calificaciones)

    except KeyError as e:
        print(f"ERROR: No se pudo procesar la salida del agente. {e}")
        sys.exit(1)
    except Exception as e:
        print("ERROR: No se pudo procesar la salida del agente.")
        print(str(e))
        sys.exit(1)

    print(
        "\n\nCalifica el desempeño de cada jugador en cada criterio del 1 al 5:")
    print("1: Muy Bajo, 2: Bajo, 3: Medio, 4: Alto, 5: Muy Alto")

    terminos_opciones = {1: "Muy Bajo", 2: "Bajo", 3: "Medio", 4: "Alto", 5: "Muy Alto"}

    matriz_usuario = []
    for jugador in jugadores:
        califs_jugador = []
        for criterio in criterios:
            while True:
                try:
                    calif = int(input(
                        f"¿Qué te parece el desempeño de {jugador} en {criterio}? (1-5): ").strip())
                    if calif in terminos_opciones:
                        califs_jugador.append(terminos_opciones[calif])
                        break
                    else:
                        print("Por favor, ingrese un número válido entre 1 y 5.")
                except ValueError:
                    print("Por favor, ingrese un número válido entre 1 y 5.")
        matriz_usuario.append(califs_jugador)

    print("\n=== Calificaciones del Usuario ===")
    output_usuario = StringIO()
    writer = csv.writer(output_usuario)
    writer.writerow(["Jugador"] + criterios)
    for jugador, calificaciones in zip(jugadores, matriz_usuario):
        writer.writerow([jugador] + calificaciones)
    print(output_usuario.getvalue())

    flpr_matrices_usuario = {}
    for idx, criterio in enumerate(criterios):
        calificaciones_criterio = [fila[idx] for fila in matriz_usuario]
        flpr_matrices_usuario[criterio] = generar_flpr(calificaciones_criterio)

    print("\n=== Matrices FLPR del Usuario ===")
    for criterio, flpr in flpr_matrices_usuario.items():
        print(f"\nFLPR para el criterio '{criterio}':")
        print(flpr)

    flpr_matrices_agente = {}
    for idx, criterio in enumerate(criterios):
        calificaciones_criterio = [fila[idx] for fila in matriz_agente]
        flpr_matrices_agente[criterio] = generar_flpr(calificaciones_criterio)

    print("\n=== Matrices FLPR del Agente ===")
    for criterio, flpr in flpr_matrices_agente.items():
        print(f"\nFLPR para el criterio '{criterio}':")
        print(flpr)

    flpr_matrices_comunes = {}
    for criterio in criterios:
        flpr_agente = flpr_matrices_agente[criterio]
        flpr_usuario = flpr_matrices_usuario[criterio]
        flpr_comun = calcular_flpr_comun(flpr_agente, flpr_usuario)
        flpr_matrices_comunes[criterio] = flpr_comun

    print("\n=== Matrices Comunes de Preferencia por Característica===")
    for criterio, flpr_comun in flpr_matrices_comunes.items():
        print(f"\nMatriz común para el criterio '{criterio}':")
        print(flpr_comun)

    # Calcular la matriz FLPR global
    matriz_flpr_global = None
    for criterio, flpr_comun in flpr_matrices_comunes.items():
        if matriz_flpr_global is None:
            matriz_flpr_global = flpr_comun.copy()
        else:
            matriz_flpr_global += flpr_comun

    # Promediar las matrices comunes
    matriz_flpr_global /= len(flpr_matrices_comunes)

    print("\n=== Matriz FLPR Global ===")
    print(matriz_flpr_global)