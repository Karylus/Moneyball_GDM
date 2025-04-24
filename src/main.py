import csv
import sys
import os
import json
import random
from io import StringIO

sys.path.append(os.path.abspath("src"))

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

from agentes.analista_datos import configurar_agente
from utils.logger import logger
from utils.matrices import generar_flpr, calcular_flpr_comun
from utils.consenso import calcular_matriz_similitud, calcular_cr
from utils.ranking import calcular_ranking_jugadores
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

    prompt_template = ChatPromptTemplate.from_messages([
        (
            "system",
            "Eres un analista de fútbol experto en evaluar jugadores. "
            "Tu deber es asignar una calificación lingüística (Muy Bajo, Bajo, Medio, Alto, Muy Alto) a cada jugador dado para cada criterio proporcionado. "
            "No compares los jugadores entre sí; evalúalos individualmente. "
            "Responde SOLO en el formato CSV\n "

            "Output format:\n\n"
            "1. La Primera linea es: ```csv\n"
            "2. El encabezado será con los campos: 'Jugador', y la lista de todos los criterios separados por comas\n"
            "3. Una linea extra por cada nombre de jugador y SOLO las calificaciones lingüísticas para cada criterio, separadas por comas, sin espacios extra.\n"
            "4. Ultima linea: ```\n\n"

            "Si no puedes generar la salida en ese formato EXACTO, responde con: 'ERROR: Formato CSV no válido'."
        ),
        (
            "user",
            "Dado el listado de jugadores: {jugadores} y los criterios: {criterios}, "
            "asigna una calificación lingüística (Muy Bajo, Bajo, Medio, Alto, Muy Alto) para cada jugador en cada criterio. "
            "Responde usando el formato CSV descrito."
        )
    ])

    prompt = prompt_template.format(jugadores=jugadores, criterios=criterios)

    max_intentos = 3
    intento_actual = 0
    matriz_agente = []

    while intento_actual < max_intentos:
        intento_actual += 1

        # Si no es el primer intento, informamos al agente de su error y pedimos que lo corrija
        if intento_actual > 1:
            print(f"\nReintentando (intento {intento_actual}/{max_intentos})...")
            mensaje_error = """
            Tu respuesta anterior no tenía el formato CSV correcto. Por favor, intenta de nuevo.
            Recuerda que debes responder con el siguiente formato exacto:
            "1. La Primera linea es: ```csv\n"
            "2. El encabezado tendrá los campos: 'Jugador', y la lista de todos los criterios separados por comas\n"
            "3. Una linea extra por cada nombre de jugador y SOLO las calificaciones lingüísticas para cada criterio, separadas por comas, sin espacios extra.\n"
            "4. Ultima linea: ```\n\n"
            """
            agente.invoke({"input": mensaje_error})

        respuesta_agente = agente.invoke({"input": prompt})
        output_agente = respuesta_agente.get("output", "No hay respuesta")

        print("\n=== Calificaciones del Agente ===")
        print(output_agente)

        # Verificar si la respuesta contiene un error explícito
        if "ERROR:" in output_agente:
            print(f"El agente reportó un error. Reintentando...")
            continue

        try:
            matriz_agente = []
            csv_data = StringIO(output_agente.replace("```csv", "").replace("```", "").strip())
            reader = csv.DictReader(csv_data)

            for row in reader:
                row_normalizado = {k.lower().strip(): v for k, v in row.items()}
                calificaciones = []
                for criterio in criterios:
                    criterio_lower = criterio.lower()
                    if criterio_lower in row_normalizado:
                        calificaciones.append(str(row_normalizado[criterio_lower]))
                    else:
                        print(f"Advertencia: El criterio '{criterio}' no está presente en los datos del CSV.")
                        # Tratar la falta de criterios como un error que debe reintentar
                        raise ValueError(f"Criterio '{criterio}' no encontrado en los datos del CSV.")
                matriz_agente.append(calificaciones)

            # Si llegamos aquí sin excepciones, la respuesta es válida
            break

        except Exception as e:
            print(f"ERROR: No se pudo procesar la salida del agente (intento {intento_actual}/{max_intentos}).")
            print(str(e))

            # Si es el último intento, generamos valores lingüísticos aleatorios en lugar de salir con error
            if intento_actual >= max_intentos:
                print(f"Se alcanzó el número máximo de intentos ({max_intentos}). Generando valores lingüísticos aleatorios...")

                # Valores lingüísticos disponibles
                valores_linguisticos = ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]

                # Generar matriz con valores aleatorios
                matriz_agente = []
                for _ in jugadores:
                    calificaciones = []
                    for _ in criterios:
                        calificaciones.append(random.choice(valores_linguisticos))
                    matriz_agente.append(calificaciones)

                print("Se han generado valores lingüísticos aleatorios para continuar con el programa.")
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
    flpr_agente = None

    for idx, criterio in enumerate(criterios):
        calificaciones_usuario = [fila[idx] for fila in matriz_usuario]
        calificaciones_agente = [fila[idx] for fila in matriz_agente]

        flpr_usuario_criterio = generar_flpr(calificaciones_usuario)
        flpr_agente_criterio = generar_flpr(calificaciones_agente)

        if flpr_usuario is None:
            flpr_usuario = flpr_usuario_criterio
            flpr_agente = flpr_agente_criterio
        else:
            flpr_usuario = calcular_flpr_comun(flpr_usuario, flpr_usuario_criterio)
            flpr_agente = calcular_flpr_comun(flpr_agente, flpr_agente_criterio)

    print("\n=== Matriz FLPR Final del Usuario ===")
    print(flpr_usuario)

    print("\n=== Matriz FLPR Final del Agente ===")
    print(flpr_agente)

    # Calcular matriz FLPR colectiva
    flpr_colectiva = calcular_flpr_comun(flpr_agente, flpr_usuario)
    print("\n=== Matriz FLPR Colectiva (Usuario y Agente) ===")
    print(flpr_colectiva)

    # Calcular matriz de similitud entre el usuario y el agente
    matriz_similitud = calcular_matriz_similitud(flpr_usuario, flpr_agente)
    print("\n=== Matriz de Similitud (Usuario y Agente) ===")
    print(matriz_similitud)

    # Calcular nivel de consenso
    cr, consenso_alcanzado = calcular_cr([matriz_similitud], consenso_minimo)
    print(f"\n=== Nivel de Consenso ===")
    print(f"Nivel de consenso (CR): {cr}")
    print(f"Consenso mínimo requerido: {consenso_minimo}")
    if consenso_alcanzado:
        print("✅ Se ha alcanzado el nivel mínimo de consenso.")
    else:
        print("❌ No se ha alcanzado el nivel mínimo de consenso.")

    # Guardar las calificaciones en la memoria del agente
    calificaciones_agente_str = "Mis calificaciones como agente para los jugadores son:\n"
    for i, jugador in enumerate(jugadores):
        calificaciones_agente_str += f"{jugador}: "
        for j, criterio in enumerate(criterios):
            calificaciones_agente_str += f"{criterio}: {matriz_agente[i][j]}, "
        calificaciones_agente_str = calificaciones_agente_str.rstrip(", ") + "\n"

    calificaciones_usuario_str = "Las calificaciones del usuario para los jugadores son:\n"
    for i, jugador in enumerate(jugadores):
        calificaciones_usuario_str += f"{jugador}: "
        for j, criterio in enumerate(criterios):
            calificaciones_usuario_str += f"{criterio}: {matriz_usuario[i][j]}, "
        calificaciones_usuario_str = calificaciones_usuario_str.rstrip(", ") + "\n"

    # Solo realizar la discusión y reevaluación si no se alcanza el consenso mínimo
    if not consenso_alcanzado:
        agente.invoke({"input": f"Recuerda estas calificaciones que ha dado el usuario: {calificaciones_usuario_str}\n"
            "No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del usuario recordadas'."})

        agente.invoke({"input": f"Recuerda estas calificaciones que has dado como agente: {calificaciones_agente_str}\n "
                                f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente recordadas'."})

        print("\n=== Discusión sobre las valoraciones ===")
        print("Ahora puedes discutir con el agente sobre las valoraciones realizadas.")
        print("(Escribe 'finalizar' para terminar la discusión y continuar con la re-evaluación)")

        discusion_activa = True
        while discusion_activa:
            pregunta_usuario = input("\nTu pregunta sobre las valoraciones: ")

            if pregunta_usuario.lower() == 'finalizar':
                print("\nFinalizando discusión sobre valoraciones.")
                discusion_activa = False
                continue

            prompt_discusion = f"""
                Basándote en las calificaciones y la discusión anterior, por favor, responde a la siguiente pregunta: {pregunta_usuario}
                No uses ninguna tool ni evalúes a los jugadores, solo responde esta pregunta.
                Tu objetivo es evaluar críticamente las afirmaciones del usuario.
                Si el usuario dice algo incorrecto o sin sentido, discútelo y explica por qué no estás de acuerdo.
                Proporciona argumentos claros y basados en datos o lógica. No aceptes afirmaciones sin fundamento.
            """

            respuesta = agente.invoke({"input": prompt_discusion})
            output = respuesta.get("output", "No hay respuesta")

            print("\nRespuesta del agente:")
            print(output)

        print("\n=== Re-evaluación de jugadores ===")
        print("El agente volverá a evaluar a los jugadores basándose en la discusión anterior.")

        prompt_reevaluacion = f"""
        Basándote en nuestra discusión anterior sobre las valoraciones de los jugadores, 
        por favor, vuelve a evaluar a los siguientes jugadores: {', '.join(jugadores)} 
        según los criterios: {', '.join(criterios)}.

        Recuerda que anteriormente tú diste estas calificaciones:
        {calificaciones_agente_str}

        Y el usuario dio estas calificaciones:
        {calificaciones_usuario_str}

        Proporciona tu nueva evaluación en el mismo formato CSV que usaste anteriormente.
        """

        max_intentos_reevaluacion = 3
        intento_actual_reevaluacion = 0
        output_reevaluacion = "No hay respuesta"

        while intento_actual_reevaluacion < max_intentos_reevaluacion:
            intento_actual_reevaluacion += 1

            # Si no es el primer intento, informamos al agente de su error y pedimos que lo corrija
            if intento_actual_reevaluacion > 1:
                print(f"\nReintentando re-evaluación (intento {intento_actual_reevaluacion}/{max_intentos_reevaluacion})...")
                mensaje_error = """
                Tu respuesta anterior no tenía el formato CSV correcto. Por favor, intenta de nuevo.
                Recuerda que debes responder con el siguiente formato exacto:
                1. La Primera linea es: ```csv
                2. El encabezado será con los campos: 'Jugador', y la lista de todos los criterios separados por comas
                3. Una linea extra por cada nombre de jugador y las calificaciones lingüísticas para cada criterio, separadas por comas, sin espacios extra.
                4. Ultima linea: ```
                """
                agente.invoke({"input": mensaje_error})

            respuesta_reevaluacion = agente.invoke({"input": prompt_reevaluacion})
            output_reevaluacion = respuesta_reevaluacion.get("output", "No hay respuesta")

            # Verificar si la respuesta contiene un error explícito
            if "ERROR:" in output_reevaluacion:
                print(f"El agente reportó un error en la re-evaluación. Reintentando...")
                continue

            # Verificar si la respuesta contiene formato CSV
            if "```csv" in output_reevaluacion and "```" in output_reevaluacion:
                # Intentar procesar el CSV para verificar que es válido
                try:
                    csv_data = StringIO(output_reevaluacion.replace("```csv", "").replace("```", "").strip())
                    reader = csv.DictReader(csv_data)
                    # Solo verificamos que se pueda leer al menos una fila
                    next(reader, None)
                    # Si llegamos aquí sin excepciones, la respuesta es válida
                    break
                except Exception as e:
                    print(f"ERROR: CSV inválido en la re-evaluación (intento {intento_actual_reevaluacion}/{max_intentos_reevaluacion}).")
                    print(str(e))
                    if intento_actual_reevaluacion >= max_intentos_reevaluacion:
                        print(f"Se alcanzó el número máximo de intentos ({max_intentos_reevaluacion}). Generando valores lingüísticos aleatorios...")
            else:
                # Si no hay formato CSV, asumimos que es una respuesta válida
                break

        print("\n=== Nueva evaluación del agente ===")
        print(output_reevaluacion)

        # Procesar la nueva evaluación del agente
        matriz_agente_nueva = []
        try:
            csv_data = StringIO(output_reevaluacion.replace("```csv", "").replace("```", "").strip())
            reader = csv.DictReader(csv_data)

            for row in reader:
                row_normalizado = {k.lower().strip(): v for k, v in row.items()}
                calificaciones = []
                for criterio in criterios:
                    criterio_lower = criterio.lower()
                    if criterio_lower in row_normalizado:
                        calificaciones.append(str(row_normalizado[criterio_lower]))
                    else:
                        print(f"Advertencia: El criterio '{criterio}' no está presente en los datos del CSV.")
                        # Tratar la falta de criterios como un error que debe reintentar
                        raise ValueError(f"Criterio '{criterio}' no encontrado en los datos del CSV.")
                matriz_agente_nueva.append(calificaciones)
        except Exception as e:
            print(f"ERROR: No se pudo procesar la nueva evaluación del agente.")
            print(str(e))

            # Si no se pudo procesar la salida, generamos valores lingüísticos aleatorios
            if intento_actual_reevaluacion >= max_intentos_reevaluacion:
                print("Generando valores lingüísticos aleatorios para la re-evaluación...")

                # Valores lingüísticos disponibles
                valores_linguisticos = ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]

                # Generar matriz con valores aleatorios
                matriz_agente_nueva = []
                for _ in jugadores:
                    calificaciones = []
                    for _ in criterios:
                        calificaciones.append(random.choice(valores_linguisticos))
                    matriz_agente_nueva.append(calificaciones)

                print("Se han generado valores lingüísticos aleatorios para continuar con el programa.")
            else:
                # Si no es el último intento, usamos la matriz anterior
                matriz_agente_nueva = matriz_agente

        # Re-evaluación del usuario
        print("\n=== Re-evaluación del usuario ===")
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
        flpr_agente_nueva = None

        for idx, criterio in enumerate(criterios):
            calificaciones_usuario_nuevas = [fila[idx] for fila in matriz_usuario_nueva]
            calificaciones_agente_nuevas = [fila[idx] for fila in matriz_agente_nueva]

            flpr_usuario_criterio_nueva = generar_flpr(calificaciones_usuario_nuevas)
            flpr_agente_criterio_nueva = generar_flpr(calificaciones_agente_nuevas)

            if flpr_usuario_nueva is None:
                flpr_usuario_nueva = flpr_usuario_criterio_nueva
                flpr_agente_nueva = flpr_agente_criterio_nueva
            else:
                flpr_usuario_nueva = calcular_flpr_comun(flpr_usuario_nueva, flpr_usuario_criterio_nueva)
                flpr_agente_nueva = calcular_flpr_comun(flpr_agente_nueva, flpr_agente_criterio_nueva)

        print("\n=== Matriz FLPR Final del Usuario (Después de la discusión) ===")
        print(flpr_usuario_nueva)

        print("\n=== Matriz FLPR Final del Agente (Después de la discusión) ===")
        print(flpr_agente_nueva)

        # Calcular matriz FLPR colectiva después de la reevaluación
        flpr_colectiva_nueva = calcular_flpr_comun(flpr_agente_nueva, flpr_usuario_nueva)
        print("\n=== Matriz FLPR Colectiva (Usuario y Agente) (Después de la discusión) ===")
        print(flpr_colectiva_nueva)

        # Calcular matriz de similitud entre el usuario y el agente después de la discusión
        matriz_similitud_nueva = calcular_matriz_similitud(flpr_usuario_nueva, flpr_agente_nueva)
        print("\n=== Matriz de Similitud (Usuario y Agente) (Después de la discusión) ===")
        print(matriz_similitud_nueva)

        # Calcular nivel de consenso después de la discusión
        cr_nuevo, consenso_alcanzado_nuevo = calcular_cr([matriz_similitud_nueva], consenso_minimo)
        print(f"\n=== Nivel de Consenso (Después de la discusión) ===")
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

        # Si se alcanzó el consenso después de la discusión, mostrar el ranking de jugadores
        if consenso_alcanzado_nuevo:
            print("\n=== Ranking de Jugadores (Después de la discusión) ===")
            ranking = calcular_ranking_jugadores(flpr_colectiva_nueva, jugadores)

            print("TOP JUGADORES (de mejor a peor):")
            for posicion, (jugador, puntuacion) in enumerate(ranking, 1):
                print(f"{posicion}. {jugador} - Puntuación: {puntuacion:.3f}")
    else:
        print("\nSe ha alcanzado el nivel mínimo de consenso. No es necesario realizar la discusión y re-evaluación.")

        # Calcular y mostrar el ranking de jugadores
        print("\n=== Ranking de Jugadores ===")
        ranking = calcular_ranking_jugadores(flpr_colectiva, jugadores)

        print("TOP JUGADORES (de mejor a peor):")
        for posicion, (jugador, puntuacion) in enumerate(ranking, 1):
            print(f"{posicion}. {jugador} - Puntuación: {puntuacion:.3f}")
