import csv
import sys
import os
import json
import random
import unicodedata
import re
from io import StringIO

sys.path.append(os.path.abspath("src"))

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

def normalizar_texto(texto):
    """
    Normaliza un texto eliminando tildes y otros caracteres diacríticos,
    convirtiendo a minúsculas y eliminando comillas simples y dobles.

    Args:
        texto (str): Texto a normalizar

    Returns:
        str: Texto normalizado sin tildes, sin comillas y en minúsculas
    """
    # Si el texto es None, devolver una cadena vacía
    if texto is None:
        return ""

    # Convertir a string si no lo es
    if not isinstance(texto, str):
        texto = str(texto)

    # Convertir a minúsculas
    texto = texto.lower()

    # Eliminar comillas simples y dobles
    texto = texto.replace("'", "").replace('"', "")

    # Normalizar NFD y eliminar diacríticos
    return ''.join(c for c in unicodedata.normalize('NFD', texto)
                  if not unicodedata.combining(c))

def extraer_csv(texto):
    """
    Extrae el contenido CSV de un texto que puede contener explicaciones antes o después.
    Busca el contenido entre marcadores ```csv o ```CSV y ```, o intenta extraer directamente
    si no encuentra los marcadores.

    Args:
        texto (str): Texto que puede contener contenido CSV

    Returns:
        str: Contenido CSV extraído
    """
    # Buscar contenido entre ```csv y ```
    csv_match = re.search(r'```(?:csv|CSV)\s*([\s\S]*?)```', texto)

    if csv_match:
        # Si encontramos los marcadores, extraemos el contenido entre ellos
        return csv_match.group(1).strip()
    else:
        # Si no hay marcadores, intentamos procesar todo el texto como CSV
        # Primero eliminamos cualquier texto antes de la primera línea que parezca un encabezado CSV
        # (línea que contiene varias comas)
        lines = texto.split('\n')
        csv_start = 0

        for i, line in enumerate(lines):
            if line.count(',') >= 2:  # Asumimos que una línea con al menos 3 campos es parte del CSV
                csv_start = i
                break

        return '\n'.join(lines[csv_start:]).strip()

from src.agentes.analista_qwen import configurar_agente as configurar_agente_qwen
from src.agentes.analista_gemini import configurar_agente as configurar_agente_gemini
from src.agentes.analista_groq import configurar_agente as configurar_agente_groq
from src.utils.logger import logger
from src.core.fuzzy_matrices import generar_flpr, calcular_flpr_comun
from src.core.consensus_logic import calcular_matriz_similitud, calcular_cr
from src.core.ranking_logic import calcular_ranking_jugadores
from langchain_core.prompts import ChatPromptTemplate

with open('data/fbref_stats_explained.json', 'r', encoding='utf-8') as f:
    explicaciones_stats = json.load(f)

explicaciones_formateadas = "\n".join([f"{clave}: {valor}" for clave, valor in explicaciones_stats.items() if not clave.startswith("_")])

def solicitar_lista(prompt_msg: str):
    # Se asume que el usuario ingresa elementos separados por comas
    entrada = input(prompt_msg).strip()
    # Se remueven espacios y se genera una lista
    return [elem.strip() for elem in entrada.split(",") if elem.strip()]

if __name__ == "__main__":
    logger.info("Iniciando agentes expertos...")
    agente_qwen = configurar_agente_qwen()
    logger.info("Agente qwen listo.")
    agente_gemini = configurar_agente_gemini()
    logger.info("Agente Gemini listo.")
    agente_groq = configurar_agente_groq()
    logger.info("Agente Groq listo.")

    print("\n=== Iniciando evaluación de jugadores ===\n")

    jugadores = solicitar_lista("Ingrese los nombres de los jugadores (separados por comas): ")
    criterios = solicitar_lista("Ingrese los criterios de evaluación (por ejemplo, velocidad, técnica, física) separados por comas: ")

    # Solicitar el nivel mínimo de consenso
    consenso_minimo = 0.8  # Valor por defecto
    while True:
        try:
            consenso_input = input(f"Ingrese el nivel mínimo de consenso requerido (0-1, por defecto {consenso_minimo}): ").strip()
            if not consenso_input:  # Si el usuario no ingresa nada, usar el valor por defecto
                break
            consenso_minimo = float(consenso_input)
            if 0 <= consenso_minimo <= 1:
                break
            else:
                print("El nivel de consenso debe estar entre 0 y 1.")
        except ValueError:
            print("Por favor, ingrese un número válido.")

    # Solicitar el número máximo de rondas de discusión
    max_rondas_discusion = 3  # Valor por defecto
    while True:
        try:
            rondas_input = input(f"Ingrese el número máximo de rondas de discusión (por defecto {max_rondas_discusion}): ").strip()
            if not rondas_input:  # Si el usuario no ingresa nada, usar el valor por defecto
                break
            max_rondas_discusion = int(rondas_input)
            if max_rondas_discusion > 0:
                break
            else:
                print("El número de rondas debe ser mayor que 0.")
        except ValueError:
            print("Por favor, ingrese un número entero válido.")

    prompt_template = ChatPromptTemplate.from_messages([
        (
            "system",
            "Eres un analista de fútbol experto en evaluar jugadores. "
            "Tu deber es asignar una calificación lingüística (Muy Bajo, Bajo, Medio, Alto, Muy Alto) a cada jugador dado para cada criterio proporcionado. "
            "No compares los jugadores entre sí; evalúalos individualmente. Usa la herramienta 'analizador_jugadores'."
            "Responde siempre SOLO en el formato CSV siguiente, no devuelvas ningún texto adicional\n "

            "Output format:\n\n"
            "1. La Primera linea es: ```CSV\n"
            "2. El encabezado será con los campos: la palabra Jugador, y cada criterio separado por comas\n"
            "3. Una linea extra por cada nombre de jugador junto a SOLO sus calificaciones lingüísticas, separadas por comas.\n"
            "4. Ultima linea: ```\n\n"

            "Si no puedes generar la salida en ese formato EXACTO, responde con: 'ERROR: Formato CSV no válido'."
        ),
        (
            "user",
            "Dado el listado de jugadores: {jugadores} y los criterios: {criterios}, "
            "asigna una calificación lingüística (Muy Bajo, Bajo, Medio, Alto, Muy Alto) para cada jugador en cada criterio. "
            "Responde usando el formato CSV descrito. No incluyas texto adicional, solo el CSV.\n"
            "No uses comillas en ninguna parte de la salida, ni incluyas espacios extra entre los campos.\n\n"
        )
    ])

    prompt = prompt_template.format(jugadores=jugadores, criterios=criterios)

    max_intentos = 3
    valores_linguisticos = ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]

    # Evaluación con el agente qwen
    matriz_agente_qwen = []

    print("\n=== Evaluación con el Agente qwen ===")

    # Un solo intento para el agente qwen, sin reintentos
    respuesta_agente_qwen = agente_qwen.invoke({"input": prompt})
    output_agente_qwen = respuesta_agente_qwen.get("output", "No hay respuesta")

    print("\n=== Calificaciones del Agente qwen ===")
    print(output_agente_qwen)

    try:
        matriz_agente_qwen = []
        csv_content = extraer_csv(output_agente_qwen)
        csv_data = StringIO(csv_content)
        reader = csv.DictReader(csv_data)

        for row in reader:
            # Normalizar las claves (criterios) pero no los valores (términos lingüísticos)
            # Sin embargo, eliminamos comillas simples y dobles de los valores
            row_normalizado = {normalizar_texto(k.strip()) if k is not None else "": v.replace("'", "").replace('"', "") if v is not None else "" for k, v in row.items()}
            calificaciones = []
            for criterio in criterios:
                criterio_lower = normalizar_texto(criterio)
                if criterio_lower in row_normalizado:
                    calificaciones.append(str(row_normalizado[criterio_lower]))
                else:
                    print(f"Advertencia: El criterio '{criterio}' no está presente en los datos del CSV.")
                    raise ValueError(f"Criterio '{criterio}' no encontrado en los datos del CSV.")
            matriz_agente_qwen.append(calificaciones)

        # Si llegamos aquí sin excepciones, la respuesta es válida
        print("✅ CSV procesado correctamente para el agente qwen.")

    except Exception as e:
        print(f"ERROR: No se pudo procesar la salida del agente qwen.")
        print(str(e))

        # Generamos valores lingüísticos aleatorios inmediatamente si hay un error
        print("Generando valores lingüísticos aleatorios...")

        # Generar matriz con valores aleatorios
        matriz_agente_qwen = []
        for _ in jugadores:
            calificaciones = []
            for _ in criterios:
                calificaciones.append(random.choice(valores_linguisticos))
            matriz_agente_qwen.append(calificaciones)

        print("Se han generado valores lingüísticos aleatorios para el agente qwen para continuar con el programa.")

    # Evaluación con el agente Gemini
    intento_actual = 0
    matriz_agente_gemini = []

    print("\n=== Evaluación con el Agente Gemini ===")
    while intento_actual < max_intentos:
        intento_actual += 1

        # Si no es el primer intento, informamos al agente de su error y pedimos que lo corrija
        if intento_actual > 1:
            print(f"\nReintentando (intento {intento_actual}/{max_intentos})...")
            mensaje_error = """
            Tu respuesta anterior no tenía el formato CSV correcto. Por favor, intenta de nuevo.
            Recuerda que debes responder con el siguiente formato exacto:
            "1. La Primera linea es: ```CSV\n"
            "2. El encabezado tendrá los campos: Jugador, y la lista de todos los criterios separados por comas\n"
            "3. Una linea extra por cada nombre de jugador y SOLO las calificaciones lingüísticas para cada criterio, separadas por comas, sin espacios extra.\n"
            "4. Ultima linea: ```\n\n"
            """
            agente_gemini.invoke({"input": mensaje_error})

        respuesta_agente_gemini = agente_gemini.invoke({"input": prompt})
        output_agente_gemini = respuesta_agente_gemini.get("output", "No hay respuesta")

        print("\n=== Calificaciones del Agente Gemini ===")
        print(output_agente_gemini)

        # Verificar si la respuesta contiene un error explícito
        if "ERROR:" in output_agente_gemini:
            print(f"El agente Gemini reportó un error. Reintentando...")
            continue

        try:
            matriz_agente_gemini = []
            # Extraer el contenido CSV de la salida del agente
            csv_content = extraer_csv(output_agente_gemini)
            csv_data = StringIO(csv_content)
            reader = csv.DictReader(csv_data)

            for row in reader:
                # Normalizar las claves (criterios) pero no los valores (términos lingüísticos)
                # Sin embargo, eliminamos comillas simples y dobles de los valores
                row_normalizado = {normalizar_texto(k.strip()) if k is not None else "": v.replace("'", "").replace('"', "") if v is not None else "" for k, v in row.items()}
                calificaciones = []
                for criterio in criterios:
                    criterio_lower = normalizar_texto(criterio)
                    if criterio_lower in row_normalizado:
                        calificaciones.append(str(row_normalizado[criterio_lower]))
                    else:
                        print(f"Advertencia: El criterio '{criterio}' no está presente en los datos del CSV.")
                        # Tratar la falta de criterios como un error que debe reintentar
                        raise ValueError(f"Criterio '{criterio}' no encontrado en los datos del CSV.")
                matriz_agente_gemini.append(calificaciones)

            # Si llegamos aquí sin excepciones, la respuesta es válida
            print("✅ CSV procesado correctamente para el agente Gemini.")
            break

        except Exception as e:
            print(f"ERROR: No se pudo procesar la salida del agente Gemini (intento {intento_actual}/{max_intentos}).")
            print(str(e))

            # Si es el último intento, generamos valores lingüísticos aleatorios en lugar de salir con error
            if intento_actual >= max_intentos:
                print(f"Se alcanzó el número máximo de intentos ({max_intentos}). Generando valores lingüísticos aleatorios...")

                # Generar matriz con valores aleatorios
                matriz_agente_gemini = []
                for _ in jugadores:
                    calificaciones = []
                    for _ in criterios:
                        calificaciones.append(random.choice(valores_linguisticos))
                    matriz_agente_gemini.append(calificaciones)

                print("Se han generado valores lingüísticos aleatorios para el agente Gemini para continuar con el programa.")
                break

    # Evaluación con el agente Groq
    intento_actual = 0
    matriz_agente_groq = []

    print("\n=== Evaluación con el Agente Groq ===")
    while intento_actual < max_intentos:
        intento_actual += 1

        # Si no es el primer intento, informamos al agente de su error y pedimos que lo corrija
        if intento_actual > 1:
            print(f"\nReintentando (intento {intento_actual}/{max_intentos})...")
            mensaje_error = """
            Tu respuesta anterior no tenía el formato CSV correcto. Por favor, intenta de nuevo.
            Recuerda que debes responder con el siguiente formato exacto:
            "1. La Primera linea es: ```CSV\n"
            "2. El encabezado tendrá los campos: Jugador, y la lista de todos los criterios separados por comas\n"
            "3. Una linea extra por cada nombre de jugador y SOLO las calificaciones lingüísticas para cada criterio, separadas por comas, sin espacios extra.\n"
            "4. Ultima linea: ```\n\n"
            """
            agente_groq.invoke({"input": mensaje_error})

        respuesta_agente_groq = agente_groq.invoke({"input": prompt})
        output_agente_groq = respuesta_agente_groq.get("output", "No hay respuesta")

        print("\n=== Calificaciones del Agente Groq ===")
        print(output_agente_groq)

        # Verificar si la respuesta contiene un error explícito
        if "ERROR:" in output_agente_groq:
            print(f"El agente Groq reportó un error. Reintentando...")
            continue

        try:
            matriz_agente_groq = []
            # Extraer el contenido CSV de la salida del agente
            csv_content = extraer_csv(output_agente_groq)
            csv_data = StringIO(csv_content)
            reader = csv.DictReader(csv_data)

            for row in reader:
                # Normalizar las claves (criterios) pero no los valores (términos lingüísticos)
                # Sin embargo, eliminamos comillas simples y dobles de los valores
                row_normalizado = {normalizar_texto(k.strip()) if k is not None else "": v.replace("'", "").replace('"', "") if v is not None else "" for k, v in row.items()}
                calificaciones = []
                for criterio in criterios:
                    criterio_lower = normalizar_texto(criterio)
                    if criterio_lower in row_normalizado:
                        calificaciones.append(str(row_normalizado[criterio_lower]))
                    else:
                        print(f"Advertencia: El criterio '{criterio}' no está presente en los datos del CSV.")
                        # Tratar la falta de criterios como un error que debe reintentar
                        raise ValueError(f"Criterio '{criterio}' no encontrado en los datos del CSV.")
                matriz_agente_groq.append(calificaciones)

            # Si llegamos aquí sin excepciones, la respuesta es válida
            print("✅ CSV procesado correctamente para el agente Groq.")
            break

        except Exception as e:
            print(f"ERROR: No se pudo procesar la salida del agente Groq (intento {intento_actual}/{max_intentos}).")
            print(str(e))

            # Si es el último intento, generamos valores lingüísticos aleatorios en lugar de salir con error
            if intento_actual >= max_intentos:
                print(f"Se alcanzó el número máximo de intentos ({max_intentos}). Generando valores lingüísticos aleatorios...")

                # Generar matriz con valores aleatorios
                matriz_agente_groq = []
                for _ in jugadores:
                    calificaciones = []
                    for _ in criterios:
                        calificaciones.append(random.choice(valores_linguisticos))
                    matriz_agente_groq.append(calificaciones)

                print("Se han generado valores lingüísticos aleatorios para el agente Groq para continuar con el programa.")
                break

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
                    calif = int(input(f"¿Qué te parece el desempeño de {jugador} en {criterio}? (1-5): ").strip())
                    if calif in terminos_opciones:
                        califs_jugador.append(terminos_opciones[calif])
                        break
                    else:
                        print("Por favor, ingrese un número válido entre 1 y 5.")
                except ValueError:
                    print("Por favor, ingrese un número válido entre 1 y 5.")
        matriz_usuario.append(califs_jugador)

    flpr_usuario = None
    flpr_agente_qwen = None
    flpr_agente_gemini = None
    flpr_agente_groq = None

    for idx, criterio in enumerate(criterios):
        calificaciones_usuario = [fila[idx] for fila in matriz_usuario]
        calificaciones_agente_qwen = [fila[idx] for fila in matriz_agente_qwen]
        calificaciones_agente_gemini = [fila[idx] for fila in matriz_agente_gemini]
        calificaciones_agente_groq = [fila[idx] for fila in matriz_agente_groq]

        flpr_usuario_criterio = generar_flpr(calificaciones_usuario)
        flpr_agente_qwen_criterio = generar_flpr(calificaciones_agente_qwen)
        flpr_agente_gemini_criterio = generar_flpr(calificaciones_agente_gemini)
        flpr_agente_groq_criterio = generar_flpr(calificaciones_agente_groq)

        if flpr_usuario is None:
            flpr_usuario = flpr_usuario_criterio
            flpr_agente_qwen = flpr_agente_qwen_criterio
            flpr_agente_gemini = flpr_agente_gemini_criterio
            flpr_agente_groq = flpr_agente_groq_criterio
        else:
            flpr_usuario = calcular_flpr_comun(flpr_usuario, flpr_usuario_criterio)
            flpr_agente_qwen = calcular_flpr_comun(flpr_agente_qwen, flpr_agente_qwen_criterio)
            flpr_agente_gemini = calcular_flpr_comun(flpr_agente_gemini, flpr_agente_gemini_criterio)
            flpr_agente_groq = calcular_flpr_comun(flpr_agente_groq, flpr_agente_groq_criterio)

    print("\n=== Matriz FLPR Final del Usuario ===")
    print(flpr_usuario)

    print("\n=== Matriz FLPR Final del Agente qwen ===")
    print(flpr_agente_qwen)

    print("\n=== Matriz FLPR Final del Agente Gemini ===")
    print(flpr_agente_gemini)

    print("\n=== Matriz FLPR Final del Agente Groq ===")
    print(flpr_agente_groq)

    # Calcular matriz FLPR colectiva entre los agentes
    flpr_agentes_qwen_gemini = calcular_flpr_comun(flpr_agente_qwen, flpr_agente_gemini)
    flpr_agentes = calcular_flpr_comun(flpr_agentes_qwen_gemini, flpr_agente_groq)
    print("\n=== Matriz FLPR Colectiva (Agentes qwen, Gemini y Groq) ===")
    print(flpr_agentes)

    # Calcular matriz FLPR colectiva entre usuario y agentes
    flpr_colectiva = calcular_flpr_comun(flpr_agentes, flpr_usuario)
    print("\n=== Matriz FLPR Colectiva (Usuario y Agentes) ===")
    print(flpr_colectiva)

    # Calcular matrices de similitud
    matriz_similitud_qwen_usuario = calcular_matriz_similitud(flpr_usuario, flpr_agente_qwen)
    matriz_similitud_gemini_usuario = calcular_matriz_similitud(flpr_usuario, flpr_agente_gemini)
    matriz_similitud_groq_usuario = calcular_matriz_similitud(flpr_usuario, flpr_agente_groq)
    matriz_similitud_qwen_gemini = calcular_matriz_similitud(flpr_agente_qwen, flpr_agente_gemini)
    matriz_similitud_qwen_groq = calcular_matriz_similitud(flpr_agente_qwen, flpr_agente_groq)
    matriz_similitud_gemini_groq = calcular_matriz_similitud(flpr_agente_gemini, flpr_agente_groq)

    print("\n=== Matriz de Similitud (Usuario y Agente qwen) ===")
    print(matriz_similitud_qwen_usuario)

    print("\n=== Matriz de Similitud (Usuario y Agente Gemini) ===")
    print(matriz_similitud_gemini_usuario)

    print("\n=== Matriz de Similitud (Usuario y Agente Groq) ===")
    print(matriz_similitud_groq_usuario)

    print("\n=== Matriz de Similitud (Agente qwen y Agente Gemini) ===")
    print(matriz_similitud_qwen_gemini)

    print("\n=== Matriz de Similitud (Agente qwen y Agente Groq) ===")
    print(matriz_similitud_qwen_groq)

    print("\n=== Matriz de Similitud (Agente Gemini y Agente Groq) ===")
    print(matriz_similitud_gemini_groq)

    # Mostrar matrices de términos lingüísticos y permitir al usuario corregir sesgos
    print("\n=== Matrices de Términos Lingüísticos ===")
    print("Ahora puedes revisar las matrices de términos lingüísticos para identificar posibles sesgos.")

    # Función para mostrar matriz de términos lingüísticos
    def mostrar_matriz_terminos(matriz, nombre_matriz):
        print(f"\n--- Matriz de Términos Lingüísticos: {nombre_matriz} ---")
        print(f"{'Jugador':<15}", end="")
        for criterio in criterios:
            print(f"{criterio:<15}", end="")
        print()
        for i, jugador in enumerate(jugadores):
            print(f"{jugador:<15}", end="")
            for j, criterio in enumerate(criterios):
                print(f"{matriz[i][j]:<15}", end="")
            print()

    # Mostrar todas las matrices
    mostrar_matriz_terminos(matriz_usuario, "Usuario")
    mostrar_matriz_terminos(matriz_agente_qwen, "Agente qwen")
    mostrar_matriz_terminos(matriz_agente_gemini, "Agente Gemini")
    mostrar_matriz_terminos(matriz_agente_groq, "Agente Groq")

    # Preguntar si el usuario quiere modificar alguna matriz
    modificar_matrices = input("\n¿Deseas modificar alguna matriz para corregir sesgos? (s/n): ").strip().lower()

    if modificar_matrices == 's':
        while True:
            print("\nSelecciona la matriz que deseas modificar:")
            print("1. Matriz del Usuario")
            print("2. Matriz del Agente qwen")
            print("3. Matriz del Agente Gemini")
            print("4. Matriz del Agente Groq")
            print("5. Terminar modificaciones")

            opcion = input("Ingresa el número de la opción: ").strip()

            if opcion == '5':
                break

            if opcion not in ['1', '2', '3', '4']:
                print("Opción no válida. Intenta de nuevo.")
                continue

            # Seleccionar la matriz a modificar
            if opcion == '1':
                matriz_a_modificar = matriz_usuario
                nombre_matriz = "Usuario"
            elif opcion == '2':
                matriz_a_modificar = matriz_agente_qwen
                nombre_matriz = "Agente qwen"
            elif opcion == '3':
                matriz_a_modificar = matriz_agente_gemini
                nombre_matriz = "Agente Gemini"
            elif opcion == '4':
                matriz_a_modificar = matriz_agente_groq
                nombre_matriz = "Agente Groq"

            # Mostrar la matriz seleccionada
            mostrar_matriz_terminos(matriz_a_modificar, nombre_matriz)

            # Solicitar índices del valor a modificar
            while True:
                try:
                    jugador_idx = int(input(f"\nIngresa el número del jugador a modificar (1-{len(jugadores)}): ")) - 1
                    if jugador_idx < 0 or jugador_idx >= len(jugadores):
                        print(f"Índice de jugador fuera de rango. Debe estar entre 1 y {len(jugadores)}.")
                        continue

                    criterio_idx = int(input(f"Ingresa el número del criterio a modificar (1-{len(criterios)}): ")) - 1
                    if criterio_idx < 0 or criterio_idx >= len(criterios):
                        print(f"Índice de criterio fuera de rango. Debe estar entre 1 y {len(criterios)}.")
                        continue

                    print(f"\nValor actual: {matriz_a_modificar[jugador_idx][criterio_idx]}")
                    print("Valores posibles: Muy Bajo, Bajo, Medio, Alto, Muy Alto")

                    nuevo_valor = input("Ingresa el nuevo valor: ").strip()
                    if nuevo_valor not in valores_linguisticos:
                        print(f"Valor no válido. Debe ser uno de: {', '.join(valores_linguisticos)}")
                        continue

                    # Modificar el valor en la matriz
                    matriz_a_modificar[jugador_idx][criterio_idx] = nuevo_valor
                    print(f"Valor modificado correctamente.")

                    # Preguntar si desea modificar otro valor en la misma matriz
                    continuar = input("¿Deseas modificar otro valor en esta matriz? (s/n): ").strip().lower()
                    if continuar != 's':
                        break

                except ValueError:
                    print("Por favor, ingresa un número válido.")

            # Recalcular la matriz FLPR correspondiente
            if opcion == '1':
                flpr_usuario = None
                for idx, criterio in enumerate(criterios):
                    calificaciones_usuario = [fila[idx] for fila in matriz_usuario]
                    flpr_usuario_criterio = generar_flpr(calificaciones_usuario)
                    if flpr_usuario is None:
                        flpr_usuario = flpr_usuario_criterio
                    else:
                        flpr_usuario = calcular_flpr_comun(flpr_usuario, flpr_usuario_criterio)
                print("\n=== Matriz FLPR del Usuario (Actualizada) ===")
                print(flpr_usuario)
            elif opcion == '2':
                flpr_agente_qwen = None
                for idx, criterio in enumerate(criterios):
                    calificaciones_agente_qwen = [fila[idx] for fila in matriz_agente_qwen]
                    flpr_agente_qwen_criterio = generar_flpr(calificaciones_agente_qwen)
                    if flpr_agente_qwen is None:
                        flpr_agente_qwen = flpr_agente_qwen_criterio
                    else:
                        flpr_agente_qwen = calcular_flpr_comun(flpr_agente_qwen, flpr_agente_qwen_criterio)
                print("\n=== Matriz FLPR del Agente qwen (Actualizada) ===")
                print(flpr_agente_qwen)
            elif opcion == '3':
                flpr_agente_gemini = None
                for idx, criterio in enumerate(criterios):
                    calificaciones_agente_gemini = [fila[idx] for fila in matriz_agente_gemini]
                    flpr_agente_gemini_criterio = generar_flpr(calificaciones_agente_gemini)
                    if flpr_agente_gemini is None:
                        flpr_agente_gemini = flpr_agente_gemini_criterio
                    else:
                        flpr_agente_gemini = calcular_flpr_comun(flpr_agente_gemini, flpr_agente_gemini_criterio)
                print("\n=== Matriz FLPR del Agente Gemini (Actualizada) ===")
                print(flpr_agente_gemini)
            elif opcion == '4':
                flpr_agente_groq = None
                for idx, criterio in enumerate(criterios):
                    calificaciones_agente_groq = [fila[idx] for fila in matriz_agente_groq]
                    flpr_agente_groq_criterio = generar_flpr(calificaciones_agente_groq)
                    if flpr_agente_groq is None:
                        flpr_agente_groq = flpr_agente_groq_criterio
                    else:
                        flpr_agente_groq = calcular_flpr_comun(flpr_agente_groq, flpr_agente_groq_criterio)
                print("\n=== Matriz FLPR del Agente Groq (Actualizada) ===")
                print(flpr_agente_groq)

        # Recalcular matrices FLPR colectivas
        flpr_agentes_qwen_gemini = calcular_flpr_comun(flpr_agente_qwen, flpr_agente_gemini)
        flpr_agentes = calcular_flpr_comun(flpr_agentes_qwen_gemini, flpr_agente_groq)
        print("\n=== Matriz FLPR Colectiva (Agentes qwen, Gemini y Groq) (Actualizada) ===")
        print(flpr_agentes)

        flpr_colectiva = calcular_flpr_comun(flpr_agentes, flpr_usuario)
        print("\n=== Matriz FLPR Colectiva (Usuario y Agentes) (Actualizada) ===")
        print(flpr_colectiva)

        # Recalcular matrices de similitud
        matriz_similitud_qwen_usuario = calcular_matriz_similitud(flpr_usuario, flpr_agente_qwen)
        matriz_similitud_gemini_usuario = calcular_matriz_similitud(flpr_usuario, flpr_agente_gemini)
        matriz_similitud_groq_usuario = calcular_matriz_similitud(flpr_usuario, flpr_agente_groq)
        matriz_similitud_qwen_gemini = calcular_matriz_similitud(flpr_agente_qwen, flpr_agente_gemini)
        matriz_similitud_qwen_groq = calcular_matriz_similitud(flpr_agente_qwen, flpr_agente_groq)
        matriz_similitud_gemini_groq = calcular_matriz_similitud(flpr_agente_gemini, flpr_agente_groq)

    # Calcular nivel de consenso con todas las matrices de similitud
    matrices_similitud = [matriz_similitud_qwen_usuario, matriz_similitud_gemini_usuario, matriz_similitud_groq_usuario, 
                          matriz_similitud_qwen_gemini, matriz_similitud_qwen_groq, matriz_similitud_gemini_groq]
    cr, consenso_alcanzado = calcular_cr(matrices_similitud, consenso_minimo)
    print(f"\n=== Nivel de Consenso ===")
    print(f"Nivel de consenso (CR): {cr}")
    print(f"Consenso mínimo requerido: {consenso_minimo}")
    if consenso_alcanzado:
        print("✅ Se ha alcanzado el nivel mínimo de consenso.")
    else:
        print("❌ No se ha alcanzado el nivel mínimo de consenso.")

    # Guardar las calificaciones en la memoria de los agentes
    calificaciones_qwen_str = "Mis calificaciones como agente qwen para los jugadores son:\n"
    for i, jugador in enumerate(jugadores):
        calificaciones_qwen_str += f"{jugador}: "
        for j, criterio in enumerate(criterios):
            calificaciones_qwen_str += f"{criterio}: {matriz_agente_qwen[i][j]}, "
        calificaciones_qwen_str = calificaciones_qwen_str.rstrip(", ") + "\n"

    calificaciones_gemini_str = "Mis calificaciones como agente Gemini para los jugadores son:\n"
    for i, jugador in enumerate(jugadores):
        calificaciones_gemini_str += f"{jugador}: "
        for j, criterio in enumerate(criterios):
            calificaciones_gemini_str += f"{criterio}: {matriz_agente_gemini[i][j]}, "
        calificaciones_gemini_str = calificaciones_gemini_str.rstrip(", ") + "\n"

    calificaciones_groq_str = "Mis calificaciones como agente Groq para los jugadores son:\n"
    for i, jugador in enumerate(jugadores):
        calificaciones_groq_str += f"{jugador}: "
        for j, criterio in enumerate(criterios):
            calificaciones_groq_str += f"{criterio}: {matriz_agente_groq[i][j]}, "
        calificaciones_groq_str = calificaciones_groq_str.rstrip(", ") + "\n"

    calificaciones_usuario_str = "Las calificaciones del usuario para los jugadores son:\n"
    for i, jugador in enumerate(jugadores):
        calificaciones_usuario_str += f"{jugador}: "
        for j, criterio in enumerate(criterios):
            calificaciones_usuario_str += f"{criterio}: {matriz_usuario[i][j]}, "
        calificaciones_usuario_str = calificaciones_usuario_str.rstrip(", ") + "\n"

    # Solo realizar la discusión y reevaluación si no se alcanza el consenso mínimo
    if not consenso_alcanzado:
        # Inicializar variables para el bucle de rondas de discusión
        ronda_actual = 1
        consenso_alcanzado_nuevo = False
        cr_nuevo = cr
        flpr_usuario_actual = flpr_usuario
        flpr_agente_qwen_actual = flpr_agente_qwen
        flpr_agente_gemini_actual = flpr_agente_gemini
        flpr_colectiva_actual = flpr_colectiva
        matriz_usuario_actual = matriz_usuario
        matriz_agente_qwen_actual = matriz_agente_qwen
        matriz_agente_gemini_actual = matriz_agente_gemini

        # Bucle de rondas de discusión
        while ronda_actual <= max_rondas_discusion and not consenso_alcanzado_nuevo:
            print(f"\n\n=== RONDA DE DISCUSIÓN {ronda_actual}/{max_rondas_discusion} ===")

            # Preparar las cadenas de calificaciones para esta ronda
            calificaciones_qwen_str = f"Mis calificaciones como agente qwen para los jugadores (Ronda {ronda_actual}) son:\n"
            for i, jugador in enumerate(jugadores):
                calificaciones_qwen_str += f"{jugador}: "
                for j, criterio in enumerate(criterios):
                    calificaciones_qwen_str += f"{criterio}: {matriz_agente_qwen_actual[i][j]}, "
                calificaciones_qwen_str = calificaciones_qwen_str.rstrip(", ") + "\n"

            calificaciones_gemini_str = f"Mis calificaciones como agente Gemini para los jugadores (Ronda {ronda_actual}) son:\n"
            for i, jugador in enumerate(jugadores):
                calificaciones_gemini_str += f"{jugador}: "
                for j, criterio in enumerate(criterios):
                    calificaciones_gemini_str += f"{criterio}: {matriz_agente_gemini_actual[i][j]}, "
                calificaciones_gemini_str = calificaciones_gemini_str.rstrip(", ") + "\n"

            calificaciones_usuario_str = f"Las calificaciones del usuario para los jugadores (Ronda {ronda_actual}) son:\n"
            for i, jugador in enumerate(jugadores):
                calificaciones_usuario_str += f"{jugador}: "
                for j, criterio in enumerate(criterios):
                    calificaciones_usuario_str += f"{criterio}: {matriz_usuario_actual[i][j]}, "
                calificaciones_usuario_str = calificaciones_usuario_str.rstrip(", ") + "\n"

            # Informar a los agentes sobre las calificaciones
            agente_qwen.invoke({"input": f"Recuerda estas calificaciones que ha dado el usuario: {calificaciones_usuario_str}\n"
                "No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del usuario recordadas'."})

            agente_gemini.invoke({"input": f"Recuerda estas calificaciones que ha dado el usuario: {calificaciones_usuario_str}\n"
                "No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del usuario recordadas'."})

            agente_groq.invoke({"input": f"Recuerda estas calificaciones que ha dado el usuario: {calificaciones_usuario_str}\n"
                "No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del usuario recordadas'."})

            agente_qwen.invoke({"input": f"Recuerda estas calificaciones que has dado como agente qwen: {calificaciones_qwen_str}\n "
                                    f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente qwen recordadas'."})

            agente_gemini.invoke({"input": f"Recuerda estas calificaciones que has dado como agente Gemini: {calificaciones_gemini_str}\n "
                                    f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Gemini recordadas'."})

            agente_groq.invoke({"input": f"Recuerda estas calificaciones que has dado como agente Groq: {calificaciones_groq_str}\n "
                                    f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Groq recordadas'."})

            # Informar a cada agente sobre las calificaciones de los otros agentes
            agente_qwen.invoke({"input": f"El agente Gemini ha dado estas calificaciones: {calificaciones_gemini_str}\n "
                                    f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Gemini recordadas'."})

            agente_qwen.invoke({"input": f"El agente Groq ha dado estas calificaciones: {calificaciones_groq_str}\n "
                                    f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Groq recordadas'."})

            agente_gemini.invoke({"input": f"El agente qwen ha dado estas calificaciones: {calificaciones_qwen_str}\n "
                                    f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente qwen recordadas'."})

            agente_gemini.invoke({"input": f"El agente Groq ha dado estas calificaciones: {calificaciones_groq_str}\n "
                                    f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Groq recordadas'."})

            agente_groq.invoke({"input": f"El agente qwen ha dado estas calificaciones: {calificaciones_qwen_str}\n "
                                    f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente qwen recordadas'."})

            agente_groq.invoke({"input": f"El agente Gemini ha dado estas calificaciones: {calificaciones_gemini_str}\n "
                                    f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Gemini recordadas'."})

            print(f"\n=== Discusión sobre las valoraciones (Ronda {ronda_actual}/{max_rondas_discusion}) ===")
            print("Ahora puedes discutir con los agentes sobre las valoraciones realizadas.")
            print("(Escribe 'finalizar' para terminar la discusión y continuar con la re-evaluación)")
            print("(Escribe 'agente:qwen', 'agente:gemini' o 'agente:groq' para dirigir tu pregunta a un agente específico)")

            discusion_activa = True
            agente_actual = "qwen"  # Por defecto empezamos con qwen

            while discusion_activa:
                pregunta_usuario = input(f"\nTu pregunta sobre las valoraciones (agente actual: {agente_actual}): ")

                if pregunta_usuario.lower() == 'finalizar':
                    print("\nFinalizando discusión sobre valoraciones.")
                    discusion_activa = False
                    continue

                # Permitir al usuario cambiar de agente
                if pregunta_usuario.lower().startswith('agente:'):
                    agente_seleccionado = pregunta_usuario.lower().split(':')[1].strip()
                    if agente_seleccionado in ['qwen', 'gemini', 'groq']:
                        agente_actual = agente_seleccionado
                        print(f"\nCambiado a agente {agente_actual.capitalize()}")
                    else:
                        print(f"\nAgente no reconocido. Usando {agente_actual.capitalize()}")
                    continue

                prompt_discusion = f"""
                    Basándote en las calificaciones y la discusión anterior, por favor, responde a la siguiente pregunta: {pregunta_usuario}
                    No uses ninguna tool ni evalúes a los jugadores, solo responde esta pregunta.
                    Tu objetivo es evaluar críticamente las afirmaciones del usuario.
                    Si el usuario dice algo incorrecto o sin sentido, discútelo y explica por qué no estás de acuerdo.
                    Proporciona argumentos claros y basados en datos o lógica. No aceptes afirmaciones sin fundamento.
                    Si recibes una orden, explica tu punta de vista pero debes respetar la orden.
                """

                # Seleccionar el agente adecuado para responder
                if agente_actual == "qwen":
                    respuesta = agente_qwen.invoke({"input": prompt_discusion})
                    print("\nRespuesta del agente qwen:")
                elif agente_actual == "gemini":
                    respuesta = agente_gemini.invoke({"input": prompt_discusion})
                    print("\nRespuesta del agente Gemini:")
                else:
                    respuesta = agente_groq.invoke({"input": prompt_discusion})
                    print("\nRespuesta del agente Groq:")

                output = respuesta.get("output", "No hay respuesta")
                print(output)

            print(f"\n=== Re-evaluación de jugadores (Ronda {ronda_actual}/{max_rondas_discusion}) ===")
            print("Los agentes volverán a evaluar a los jugadores basándose en la discusión anterior.")

            # Re-evaluación con el agente qwen
            prompt_reevaluacion_qwen = f"""
            Basándote en nuestra discusión anterior sobre las valoraciones de los jugadores, 
            por favor, vuelve a evaluar a los siguientes jugadores: {', '.join(jugadores)} 
            según los criterios: {', '.join(criterios)}.

            Proporciona tu nueva evaluación en el mismo formato CSV que usaste anteriormente.
            """

            # Re-evaluación con el agente Gemini
            prompt_reevaluacion_gemini = f"""
            Basándote en nuestra discusión anterior sobre las valoraciones de los jugadores, 
            por favor, vuelve a evaluar a los siguientes jugadores: {', '.join(jugadores)} 
            según los criterios: {', '.join(criterios)}.

            Recuerda que anteriormente tú diste estas calificaciones como agente Gemini:
            {calificaciones_gemini_str}

            El agente qwen dio estas calificaciones:
            {calificaciones_qwen_str}

            El agente Groq dio estas calificaciones:
            {calificaciones_groq_str}

            Y el usuario dio estas calificaciones:
            {calificaciones_usuario_str}

            Proporciona tu nueva evaluación en el mismo formato CSV que usaste anteriormente.
            """

            # Re-evaluación con el agente Groq
            prompt_reevaluacion_groq = f"""
            Basándote en nuestra discusión anterior sobre las valoraciones de los jugadores, 
            por favor, vuelve a evaluar a los siguientes jugadores: {', '.join(jugadores)} 
            según los criterios: {', '.join(criterios)}.

            Recuerda que anteriormente tú diste estas calificaciones como agente Groq:
            {calificaciones_groq_str}

            El agente qwen dio estas calificaciones:
            {calificaciones_qwen_str}

            El agente Gemini dio estas calificaciones:
            {calificaciones_gemini_str}

            Y el usuario dio estas calificaciones:
            {calificaciones_usuario_str}

            Proporciona tu nueva evaluación en el mismo formato CSV que usaste anteriormente.
            """

            max_intentos_reevaluacion = 3
            valores_linguisticos = ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]

            # Re-evaluación con el agente qwen
            print(f"\n=== Re-evaluación con el Agente qwen (Ronda {ronda_actual}/{max_rondas_discusion}) ===")
            intento_actual_reevaluacion = 0
            output_reevaluacion_qwen = "No hay respuesta"
            matriz_agente_qwen_nueva = []

            while intento_actual_reevaluacion < max_intentos_reevaluacion:
                intento_actual_reevaluacion += 1

                # Si no es el primer intento, informamos al agente de su error y pedimos que lo corrija
                if intento_actual_reevaluacion > 1:
                    print(f"\nReintentando re-evaluación qwen (intento {intento_actual_reevaluacion}/{max_intentos_reevaluacion})...")
                    mensaje_error = """
                    Tu respuesta anterior no tenía el formato CSV correcto. Por favor, intenta de nuevo.
                    Recuerda que debes responder con el siguiente formato exacto:
                    1. La Primera linea es: ```csv
                    2. El encabezado será con los campos: Jugador, y la lista de todos los criterios separados por comas
                    3. Una linea extra por cada nombre de jugador y las calificaciones lingüísticas para cada criterio, separadas por comas, sin espacios extra.
                    4. Ultima linea: ```
                    """
                    agente_qwen.invoke({"input": mensaje_error})

                respuesta_reevaluacion_qwen = agente_qwen.invoke({"input": prompt_reevaluacion_qwen})
                output_reevaluacion_qwen = respuesta_reevaluacion_qwen.get("output", "No hay respuesta")

                # Verificar si la respuesta contiene un error explícito
                if "ERROR:" in output_reevaluacion_qwen:
                    print(f"El agente qwen reportó un error en la re-evaluación. Reintentando...")
                    continue

                # Intentar procesar el CSV para verificar que es válido
                try:
                    # Extraer el contenido CSV de la salida del agente
                    csv_content = extraer_csv(output_reevaluacion_qwen)
                    csv_data = StringIO(csv_content)
                    reader = csv.DictReader(csv_data)
                    # Solo verificamos que se pueda leer al menos una fila
                    next(reader, None)
                    # Si llegamos aquí sin excepciones, la respuesta es válida
                    print("✅ CSV de re-evaluación qwen procesado correctamente.")
                    csv_procesado_correctamente = True
                    break
                except Exception as e:
                    print(f"ERROR: CSV inválido en la re-evaluación qwen (intento {intento_actual_reevaluacion}/{max_intentos_reevaluacion}).")
                    print(str(e))
                    if intento_actual_reevaluacion >= max_intentos_reevaluacion:
                        print(f"Se alcanzó el número máximo de intentos ({max_intentos_reevaluacion}). Generando valores lingüísticos aleatorios...")
                    # Si no es el último intento, continuamos con el siguiente intento
                    continue

            print("\n=== Nueva evaluación del agente qwen ===")
            print(output_reevaluacion_qwen)

            # Procesar la nueva evaluación del agente qwen
            matriz_agente_qwen_nueva = []
            csv_procesado_correctamente = False
            try:
                # Extraer el contenido CSV de la salida del agente
                csv_content = extraer_csv(output_reevaluacion_qwen)
                csv_data = StringIO(csv_content)
                reader = csv.DictReader(csv_data)

                for row in reader:
                    # Normalizar las claves (criterios) pero no los valores (términos lingüísticos)
                    # Sin embargo, eliminamos comillas simples y dobles de los valores
                    row_normalizado = {normalizar_texto(k.strip()) if k is not None else "": v.replace("'", "").replace('"', "") if v is not None else "" for k, v in row.items()}
                    calificaciones = []
                    for criterio in criterios:
                        criterio_lower = normalizar_texto(criterio)
                        if criterio_lower in row_normalizado:
                            calificaciones.append(str(row_normalizado[criterio_lower]))
                        else:
                            print(f"Advertencia: El criterio '{criterio}' no está presente en los datos del CSV.")
                            # Tratar la falta de criterios como un error que debe reintentar
                            raise ValueError(f"Criterio '{criterio}' no encontrado en los datos del CSV.")
                    matriz_agente_qwen_nueva.append(calificaciones)

                # Si llegamos aquí sin excepciones, el CSV se procesó correctamente
                csv_procesado_correctamente = True
                print("✅ CSV de re-evaluación qwen procesado y validado correctamente.")
            except Exception as e:
                print(f"ERROR: No se pudo procesar la nueva evaluación del agente qwen.")
                print(str(e))

                # Si no se pudo procesar la salida, generamos valores lingüísticos aleatorios
                if not csv_procesado_correctamente:
                    if intento_actual_reevaluacion >= max_intentos_reevaluacion:
                        print("Generando valores lingüísticos aleatorios para la re-evaluación qwen...")

                        # Generar matriz con valores aleatorios
                        matriz_agente_qwen_nueva = []
                        for _ in jugadores:
                            calificaciones = []
                            for _ in criterios:
                                calificaciones.append(random.choice(valores_linguisticos))
                            matriz_agente_qwen_nueva.append(calificaciones)

                        print("Se han generado valores lingüísticos aleatorios para el agente qwen para continuar con el programa.")
                    else:
                        # Si no es el último intento, usamos la matriz anterior
                        matriz_agente_qwen_nueva = matriz_agente_qwen_actual

            # Re-evaluación con el agente Gemini
            print(f"\n=== Re-evaluación con el Agente Gemini (Ronda {ronda_actual}/{max_rondas_discusion}) ===")
            intento_actual_reevaluacion = 0
            output_reevaluacion_gemini = "No hay respuesta"
            matriz_agente_gemini_nueva = []

            while intento_actual_reevaluacion < max_intentos_reevaluacion:
                intento_actual_reevaluacion += 1

                # Si no es el primer intento, informamos al agente de su error y pedimos que lo corrija
                if intento_actual_reevaluacion > 1:
                    print(f"\nReintentando re-evaluación Gemini (intento {intento_actual_reevaluacion}/{max_intentos_reevaluacion})...")
                    mensaje_error = """
                    Tu respuesta anterior no tenía el formato CSV correcto. Por favor, intenta de nuevo.
                    Recuerda que debes responder con el siguiente formato exacto:
                    1. La Primera linea es: ```csv
                    2. El encabezado será con los campos: Jugador, y la lista de todos los criterios separados por comas
                    3. Una linea extra por cada nombre de jugador y las calificaciones lingüísticas para cada criterio, separadas por comas, sin espacios extra.
                    4. Ultima linea: ```
                    """
                    agente_gemini.invoke({"input": mensaje_error})

                respuesta_reevaluacion_gemini = agente_gemini.invoke({"input": prompt_reevaluacion_gemini})
                output_reevaluacion_gemini = respuesta_reevaluacion_gemini.get("output", "No hay respuesta")

                # Verificar si la respuesta contiene un error explícito
                if "ERROR:" in output_reevaluacion_gemini:
                    print(f"El agente Gemini reportó un error en la re-evaluación. Reintentando...")
                    continue

                # Intentar procesar el CSV para verificar que es válido
                try:
                    # Extraer el contenido CSV de la salida del agente
                    csv_content = extraer_csv(output_reevaluacion_gemini)
                    csv_data = StringIO(csv_content)
                    reader = csv.DictReader(csv_data)
                    # Solo verificamos que se pueda leer al menos una fila
                    next(reader, None)
                    # Si llegamos aquí sin excepciones, la respuesta es válida
                    print("✅ CSV de re-evaluación Gemini procesado correctamente.")
                    csv_procesado_correctamente = True
                    break
                except Exception as e:
                    print(f"ERROR: CSV inválido en la re-evaluación Gemini (intento {intento_actual_reevaluacion}/{max_intentos_reevaluacion}).")
                    print(str(e))
                    if intento_actual_reevaluacion >= max_intentos_reevaluacion:
                        print(f"Se alcanzó el número máximo de intentos ({max_intentos_reevaluacion}). Generando valores lingüísticos aleatorios...")
                    # Si no es el último intento, continuamos con el siguiente intento
                    continue

            print("\n=== Nueva evaluación del agente Gemini ===")
            print(output_reevaluacion_gemini)

            # Procesar la nueva evaluación del agente Gemini
            matriz_agente_gemini_nueva = []
            csv_procesado_correctamente = False
            try:
                # Extraer el contenido CSV de la salida del agente
                csv_content = extraer_csv(output_reevaluacion_gemini)
                csv_data = StringIO(csv_content)
                reader = csv.DictReader(csv_data)

                for row in reader:
                    # Normalizar las claves (criterios) pero no los valores (términos lingüísticos)
                    # Sin embargo, eliminamos comillas simples y dobles de los valores
                    row_normalizado = {normalizar_texto(k.strip()) if k is not None else "": v.replace("'", "").replace('"', "") if v is not None else "" for k, v in row.items()}
                    calificaciones = []
                    for criterio in criterios:
                        criterio_lower = normalizar_texto(criterio)
                        if criterio_lower in row_normalizado:
                            calificaciones.append(str(row_normalizado[criterio_lower]))
                        else:
                            print(f"Advertencia: El criterio '{criterio}' no está presente en los datos del CSV.")
                            # Tratar la falta de criterios como un error que debe reintentar
                            raise ValueError(f"Criterio '{criterio}' no encontrado en los datos del CSV.")
                    matriz_agente_gemini_nueva.append(calificaciones)

                # Si llegamos aquí sin excepciones, el CSV se procesó correctamente
                csv_procesado_correctamente = True
                print("✅ CSV de re-evaluación Gemini procesado y validado correctamente.")
            except Exception as e:
                print(f"ERROR: No se pudo procesar la nueva evaluación del agente Gemini.")
                print(str(e))

                # Si no se pudo procesar la salida, generamos valores lingüísticos aleatorios
                if not csv_procesado_correctamente:
                    if intento_actual_reevaluacion >= max_intentos_reevaluacion:
                        print("Generando valores lingüísticos aleatorios para la re-evaluación Gemini...")

                        # Generar matriz con valores aleatorios
                        matriz_agente_gemini_nueva = []
                        for _ in jugadores:
                            calificaciones = []
                            for _ in criterios:
                                calificaciones.append(random.choice(valores_linguisticos))
                            matriz_agente_gemini_nueva.append(calificaciones)

                        print("Se han generado valores lingüísticos aleatorios para el agente Gemini para continuar con el programa.")
                    else:
                        # Si no es el último intento, usamos la matriz anterior
                        matriz_agente_gemini_nueva = matriz_agente_gemini_actual

            # Re-evaluación del usuario
            print(f"\n=== Re-evaluación del usuario (Ronda {ronda_actual}/{max_rondas_discusion}) ===")
            print("Ahora es tu turno de volver a evaluar a los jugadores después de la discusión.")
            print("Califica el desempeño de cada jugador en cada criterio del 1 al 5:")
            print("1: Muy Bajo, 2: Bajo, 3: Medio, 4: Alto, 5: Muy Alto")

            matriz_usuario_nueva = []
            for jugador in jugadores:
                califs_jugador = []
                for criterio in criterios:
                    while True:
                        try:
                            calif = int(input(f"¿Qué te parece ahora el desempeño de {jugador} en {criterio}? (1-5): ").strip())
                            if calif in terminos_opciones:
                                califs_jugador.append(terminos_opciones[calif])
                                break
                            else:
                                print("Por favor, ingrese un número válido entre 1 y 5.")
                        except ValueError:
                            print("Por favor, ingrese un número válido entre 1 y 5.")
                matriz_usuario_nueva.append(califs_jugador)

            # Calcular nuevas matrices FLPR
            flpr_usuario_nueva = None
            flpr_agente_qwen_nueva = None
            flpr_agente_gemini_nueva = None

            for idx, criterio in enumerate(criterios):
                calificaciones_usuario_nuevas = [fila[idx] for fila in matriz_usuario_nueva]
                calificaciones_agente_qwen_nuevas = [fila[idx] for fila in matriz_agente_qwen_nueva]
                calificaciones_agente_gemini_nuevas = [fila[idx] for fila in matriz_agente_gemini_nueva]

                flpr_usuario_criterio_nueva = generar_flpr(calificaciones_usuario_nuevas)
                flpr_agente_qwen_criterio_nueva = generar_flpr(calificaciones_agente_qwen_nuevas)
                flpr_agente_gemini_criterio_nueva = generar_flpr(calificaciones_agente_gemini_nuevas)

                if flpr_usuario_nueva is None:
                    flpr_usuario_nueva = flpr_usuario_criterio_nueva
                    flpr_agente_qwen_nueva = flpr_agente_qwen_criterio_nueva
                    flpr_agente_gemini_nueva = flpr_agente_gemini_criterio_nueva
                else:
                    flpr_usuario_nueva = calcular_flpr_comun(flpr_usuario_nueva, flpr_usuario_criterio_nueva)
                    flpr_agente_qwen_nueva = calcular_flpr_comun(flpr_agente_qwen_nueva, flpr_agente_qwen_criterio_nueva)
                    flpr_agente_gemini_nueva = calcular_flpr_comun(flpr_agente_gemini_nueva, flpr_agente_gemini_criterio_nueva)

            print(f"\n=== Matriz FLPR Final del Usuario (Después de la ronda {ronda_actual} de discusión) ===")
            print(flpr_usuario_nueva)

            print(f"\n=== Matriz FLPR Final del Agente qwen (Después de la ronda {ronda_actual} de discusión) ===")
            print(flpr_agente_qwen_nueva)

            print(f"\n=== Matriz FLPR Final del Agente Gemini (Después de la ronda {ronda_actual} de discusión) ===")
            print(flpr_agente_gemini_nueva)

            # Calcular matriz FLPR colectiva entre los agentes después de la reevaluación
            flpr_agentes_nueva = calcular_flpr_comun(flpr_agente_qwen_nueva, flpr_agente_gemini_nueva)
            print(f"\n=== Matriz FLPR Colectiva (Agentes qwen y Gemini) (Después de la ronda {ronda_actual} de discusión) ===")
            print(flpr_agentes_nueva)

            # Calcular matriz FLPR colectiva después de la reevaluación
            flpr_colectiva_nueva = calcular_flpr_comun(flpr_agentes_nueva, flpr_usuario_nueva)
            print(f"\n=== Matriz FLPR Colectiva (Usuario y Agentes) (Después de la ronda {ronda_actual} de discusión) ===")
            print(flpr_colectiva_nueva)

            # Calcular matrices de similitud después de la discusión
            matriz_similitud_qwen_usuario_nueva = calcular_matriz_similitud(flpr_usuario_nueva, flpr_agente_qwen_nueva)
            matriz_similitud_gemini_usuario_nueva = calcular_matriz_similitud(flpr_usuario_nueva, flpr_agente_gemini_nueva)
            matriz_similitud_agentes_nueva = calcular_matriz_similitud(flpr_agente_qwen_nueva, flpr_agente_gemini_nueva)

            print(f"\n=== Matriz de Similitud (Usuario y Agente qwen) (Después de la ronda {ronda_actual} de discusión) ===")
            print(matriz_similitud_qwen_usuario_nueva)

            print(f"\n=== Matriz de Similitud (Usuario y Agente Gemini) (Después de la ronda {ronda_actual} de discusión) ===")
            print(matriz_similitud_gemini_usuario_nueva)

            print(f"\n=== Matriz de Similitud (Agente qwen y Agente Gemini) (Después de la ronda {ronda_actual} de discusión) ===")
            print(matriz_similitud_agentes_nueva)

            # Calcular nivel de consenso después de la discusión
            matrices_similitud_nuevas = [matriz_similitud_qwen_usuario_nueva, matriz_similitud_gemini_usuario_nueva, matriz_similitud_agentes_nueva]
            cr_nuevo, consenso_alcanzado_nuevo = calcular_cr(matrices_similitud_nuevas, consenso_minimo)
            print(f"\n=== Nivel de Consenso (Después de la ronda {ronda_actual} de discusión) ===")
            print(f"Nivel de consenso (CR): {cr_nuevo}")
            print(f"Consenso mínimo requerido: {consenso_minimo}")
            if consenso_alcanzado_nuevo:
                print("✅ Se ha alcanzado el nivel mínimo de consenso.")
            else:
                print("❌ No se ha alcanzado el nivel mínimo de consenso.")

            # Comparar el nivel de consenso antes y después de la discusión
            if cr_nuevo > cr:
                print(f"\nEl nivel de consenso ha mejorado después de la discusión: {cr} → {cr_nuevo}")
            elif cr_nuevo < cr:
                print(f"\nEl nivel de consenso ha disminuido después de la discusión: {cr} → {cr_nuevo}")
            else:
                print(f"\nEl nivel de consenso se ha mantenido igual después de la discusión: {cr}")

            # Actualizar las variables para la siguiente ronda
            flpr_usuario_actual = flpr_usuario_nueva
            flpr_agente_qwen_actual = flpr_agente_qwen_nueva
            flpr_agente_gemini_actual = flpr_agente_gemini_nueva
            flpr_colectiva_actual = flpr_colectiva_nueva
            matriz_usuario_actual = matriz_usuario_nueva
            matriz_agente_qwen_actual = matriz_agente_qwen_nueva
            matriz_agente_gemini_actual = matriz_agente_gemini_nueva

            # Incrementar el contador de rondas
            ronda_actual += 1

            # Si se alcanzó el consenso o se llegó al máximo de rondas, mostrar el ranking de jugadores
            if consenso_alcanzado_nuevo or ronda_actual > max_rondas_discusion:
                print("\n=== Ranking de Jugadores (Después de la discusión) ===")
                ranking = calcular_ranking_jugadores(flpr_colectiva_nueva, jugadores)

                print("TOP JUGADORES (de mejor a peor):")
                for posicion, (jugador, puntuacion) in enumerate(ranking, 1):
                    print(f"{posicion}. {jugador} - Puntuación: {puntuacion:.3f}")

                # Si se alcanzó el máximo de rondas sin consenso, dar una última oportunidad para modificar matrices
                if not consenso_alcanzado_nuevo and ronda_actual > max_rondas_discusion:
                    print(f"\n⚠️ Se ha alcanzado el número máximo de rondas de discusión ({max_rondas_discusion}) sin llegar al consenso mínimo requerido.")
                    print(f"Nivel de consenso actual: {cr_nuevo}")

                    # Ofrecer una última oportunidad para modificar matrices
                    print("\n=== Última oportunidad para corregir sesgos ===")
                    print("Puedes revisar y modificar las matrices de términos lingüísticos una última vez antes de calcular el ranking final.")

                    # Mostrar todas las matrices
                    mostrar_matriz_terminos(matriz_usuario_actual, "Usuario (Actual)")
                    mostrar_matriz_terminos(matriz_agente_qwen_actual, "Agente qwen (Actual)")
                    mostrar_matriz_terminos(matriz_agente_gemini_actual, "Agente Gemini (Actual)")

                    # Preguntar si el usuario quiere modificar alguna matriz
                    modificar_matrices_final = input("\n¿Deseas modificar alguna matriz para corregir sesgos? (s/n): ").strip().lower()

                    if modificar_matrices_final == 's':
                        while True:
                            print("\nSelecciona la matriz que deseas modificar:")
                            print("1. Matriz del Usuario")
                            print("2. Matriz del Agente qwen")
                            print("3. Matriz del Agente Gemini")
                            print("4. Terminar modificaciones")

                            opcion = input("Ingresa el número de la opción: ").strip()

                            if opcion == '4':
                                break

                            if opcion not in ['1', '2', '3']:
                                print("Opción no válida. Intenta de nuevo.")
                                continue

                            # Seleccionar la matriz a modificar
                            if opcion == '1':
                                matriz_a_modificar = matriz_usuario_actual
                                nombre_matriz = "Usuario"
                            elif opcion == '2':
                                matriz_a_modificar = matriz_agente_qwen_actual
                                nombre_matriz = "Agente qwen"
                            elif opcion == '3':
                                matriz_a_modificar = matriz_agente_gemini_actual
                                nombre_matriz = "Agente Gemini"

                            # Mostrar la matriz seleccionada
                            mostrar_matriz_terminos(matriz_a_modificar, nombre_matriz)

                            # Solicitar índices del valor a modificar
                            while True:
                                try:
                                    jugador_idx = int(input(f"\nIngresa el número del jugador a modificar (1-{len(jugadores)}): ")) - 1
                                    if jugador_idx < 0 or jugador_idx >= len(jugadores):
                                        print(f"Índice de jugador fuera de rango. Debe estar entre 1 y {len(jugadores)}.")
                                        continue

                                    criterio_idx = int(input(f"Ingresa el número del criterio a modificar (1-{len(criterios)}): ")) - 1
                                    if criterio_idx < 0 or criterio_idx >= len(criterios):
                                        print(f"Índice de criterio fuera de rango. Debe estar entre 1 y {len(criterios)}.")
                                        continue

                                    print(f"\nValor actual: {matriz_a_modificar[jugador_idx][criterio_idx]}")
                                    print("Valores posibles: Muy Bajo, Bajo, Medio, Alto, Muy Alto")

                                    nuevo_valor = input("Ingresa el nuevo valor: ").strip()
                                    if nuevo_valor not in valores_linguisticos:
                                        print(f"Valor no válido. Debe ser uno de: {', '.join(valores_linguisticos)}")
                                        continue

                                    # Modificar el valor en la matriz
                                    matriz_a_modificar[jugador_idx][criterio_idx] = nuevo_valor
                                    print(f"Valor modificado correctamente.")

                                    # Preguntar si desea modificar otro valor en la misma matriz
                                    continuar = input("¿Deseas modificar otro valor en esta matriz? (s/n): ").strip().lower()
                                    if continuar != 's':
                                        break

                                except ValueError:
                                    print("Por favor, ingresa un número válido.")

                            # Recalcular la matriz FLPR correspondiente
                            if opcion == '1':
                                flpr_usuario_nueva = None
                                for idx, criterio in enumerate(criterios):
                                    calificaciones_usuario_nuevas = [fila[idx] for fila in matriz_usuario_actual]
                                    flpr_usuario_criterio_nueva = generar_flpr(calificaciones_usuario_nuevas)
                                    if flpr_usuario_nueva is None:
                                        flpr_usuario_nueva = flpr_usuario_criterio_nueva
                                    else:
                                        flpr_usuario_nueva = calcular_flpr_comun(flpr_usuario_nueva, flpr_usuario_criterio_nueva)
                                print("\n=== Matriz FLPR del Usuario (Actualizada) ===")
                                print(flpr_usuario_nueva)
                                flpr_usuario_actual = flpr_usuario_nueva
                            elif opcion == '2':
                                flpr_agente_qwen_nueva = None
                                for idx, criterio in enumerate(criterios):
                                    calificaciones_agente_qwen_nuevas = [fila[idx] for fila in matriz_agente_qwen_actual]
                                    flpr_agente_qwen_criterio_nueva = generar_flpr(calificaciones_agente_qwen_nuevas)
                                    if flpr_agente_qwen_nueva is None:
                                        flpr_agente_qwen_nueva = flpr_agente_qwen_criterio_nueva
                                    else:
                                        flpr_agente_qwen_nueva = calcular_flpr_comun(flpr_agente_qwen_nueva, flpr_agente_qwen_criterio_nueva)
                                print("\n=== Matriz FLPR del Agente qwen (Actualizada) ===")
                                print(flpr_agente_qwen_nueva)
                                flpr_agente_qwen_actual = flpr_agente_qwen_nueva
                            elif opcion == '3':
                                flpr_agente_gemini_nueva = None
                                for idx, criterio in enumerate(criterios):
                                    calificaciones_agente_gemini_nuevas = [fila[idx] for fila in matriz_agente_gemini_actual]
                                    flpr_agente_gemini_criterio_nueva = generar_flpr(calificaciones_agente_gemini_nuevas)
                                    if flpr_agente_gemini_nueva is None:
                                        flpr_agente_gemini_nueva = flpr_agente_gemini_criterio_nueva
                                    else:
                                        flpr_agente_gemini_nueva = calcular_flpr_comun(flpr_agente_gemini_nueva, flpr_agente_gemini_criterio_nueva)
                                print("\n=== Matriz FLPR del Agente Gemini (Actualizada) ===")
                                print(flpr_agente_gemini_nueva)
                                flpr_agente_gemini_actual = flpr_agente_gemini_nueva

                        # Recalcular matrices FLPR colectivas
                        flpr_agentes_nueva = calcular_flpr_comun(flpr_agente_qwen_actual, flpr_agente_gemini_actual)
                        print("\n=== Matriz FLPR Colectiva (Agentes qwen y Gemini) (Actualizada) ===")
                        print(flpr_agentes_nueva)

                        flpr_colectiva_nueva = calcular_flpr_comun(flpr_agentes_nueva, flpr_usuario_actual)
                        print("\n=== Matriz FLPR Colectiva (Usuario y Agentes) (Actualizada) ===")
                        print(flpr_colectiva_nueva)

                        # Recalcular matrices de similitud
                        matriz_similitud_qwen_usuario_nueva = calcular_matriz_similitud(flpr_usuario_actual, flpr_agente_qwen_actual)
                        matriz_similitud_gemini_usuario_nueva = calcular_matriz_similitud(flpr_usuario_actual, flpr_agente_gemini_actual)
                        matriz_similitud_agentes_nueva = calcular_matriz_similitud(flpr_agente_qwen_actual, flpr_agente_gemini_actual)

                        # Recalcular nivel de consenso
                        matrices_similitud_nuevas = [matriz_similitud_qwen_usuario_nueva, matriz_similitud_gemini_usuario_nueva, matriz_similitud_agentes_nueva]
                        cr_nuevo, consenso_alcanzado_nuevo = calcular_cr(matrices_similitud_nuevas, consenso_minimo)
                        print(f"\n=== Nivel de Consenso (Después de modificaciones finales) ===")
                        print(f"Nivel de consenso (CR): {cr_nuevo}")
                        print(f"Consenso mínimo requerido: {consenso_minimo}")
                        if consenso_alcanzado_nuevo:
                            print("✅ Se ha alcanzado el nivel mínimo de consenso.")
                        else:
                            print("❌ No se ha alcanzado el nivel mínimo de consenso.")

                        # Recalcular el ranking con las matrices actualizadas
                        print("\n=== Ranking de Jugadores (Actualizado) ===")
                        ranking = calcular_ranking_jugadores(flpr_colectiva_nueva, jugadores)

                        print("TOP JUGADORES (de mejor a peor):")
                        for posicion, (jugador, puntuacion) in enumerate(ranking, 1):
                            print(f"{posicion}. {jugador} - Puntuación: {puntuacion:.3f}")

                    print(f"\nSe muestra el ranking con el nivel de consenso actual: {cr_nuevo}")

            # Si no se alcanzó el consenso y no se llegó al máximo de rondas, continuar con la siguiente ronda
    else:
        print("\nSe ha alcanzado el nivel mínimo de consenso. No es necesario realizar la discusión y re-evaluación.")

        # Calcular y mostrar el ranking de jugadores
        print("\n=== Ranking de Jugadores ===")
        ranking = calcular_ranking_jugadores(flpr_colectiva, jugadores)

        print("TOP JUGADORES (de mejor a peor):")
        for posicion, (jugador, puntuacion) in enumerate(ranking, 1):
            print(f"{posicion}. {jugador} - Puntuación: {puntuacion:.3f}")
