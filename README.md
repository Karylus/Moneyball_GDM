# Moneyball_GDM

[![Python Version](https://img.shields.io/badge/python-3.12+-blue)](#requisitos-previos)
[![License](https://img.shields.io/badge/license-Apache%202.0-grenn)](#licencia)

Aplica técnicas de evaluaciones asistidas por LLMs para comparar y analizar jugadores de deportes. Ofrece dos modos de uso:  
1. **Evaluar Jugadores**: interacción guiada con agentes LLM para producir un informe en PDF.  
2. **Consultar Base de Datos**: visualiza y compara estadísticas de jugadores en gráficas de radar.

---

## Índice

- [Características](#caracter%C3%ADsticas)  
- [Requisitos previos](#requisitos-previos)  
- [Instalación](#instalaci%C3%B3n)  
- [Configuración](#configuraci%C3%B3n)  
- [Uso](#uso)  
  - [Modo 1: Evaluar Jugadores](#modo-1-evaluar-jugadores)  
  - [Modo 2: Consultar Base de Datos](#modo-2-consultar-base-de-datos)  
- [Exportar resultados](#exportar-resultados)  
- [Solución de problemas](#soluci%C3%B3n-de-problemas)  
- [Contribuir](#contribuir)  
- [Licencia](#licencia)  

---

## Características

- Flujo interactivo guiado por agentes LLM (Groq y Gemini).  
- Generación automática de informes PDF con matrices de evaluación y discusión de sesgos.  
- Consulta y comparación visual de estadísticas de jugadores (gráficas de radar).  
- Exportación de resultados en PDF y PNG.  

---

## Requisitos previos

- Python 3.12 o superior  
- Git  
- Clave API para LLMs (Groq y Gemini)  
- Docker (opcional, para MongoDB)
- Qwen3 descargado con Ollama
- MongoDB (local o Atlas) y credenciales   

---

## Instalación

1. Clona el repositorio:  
   ```bash
   git clone https://github.com/Karylus/Moneyball_GDM.git
   cd Moneyball_GDM
   ```
2. (Opcional) Crea y activa un entorno virtual:  
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```
3. Instala las dependencias:  
   ```bash
   pip install -r requirements.txt
   ```

---

## Configuración

1. Renombra `.env.example` a `.env`.  
2. Rellena tus credenciales en `.env`:
   ```text
   MONGO_INITDB_ROOT_USERNAME=<usuario_mongo>
   MONGO_INITDB_ROOT_PASSWORD=<contraseña_mongo>
   MONGO_URI=<uri_mongodb>

   GEMINI_API_KEY=<tu_gemini_api_key>
   GROQ_API_KEY=<tu_groq_api_key>
   ```

---

## Uso

### Pestaña 1: Evaluar Jugadores

1. Inicia MongoDB (Docker):
   ```bash
   docker compose up -d
   ```
   o asegúrate de que Atlas esté accesible.  
2. Ejecuta la aplicación:
   ```bash
   python gui_launcher.py
   ```
3. Ve a la pestaña **Evaluar Jugadores**:
   - Selecciona hasta 3 jugadores.  
   - Elige criterios de evaluación.  
   - Haz clic en **Evaluar Jugadores**.  
   - Interactúa según las solicitudes del programa.  
   - Al acabar, puedes descargar el informe PDF con **Exportar a PDF**.

### Pestaña 2: Consultar Base de Datos

1. Abre la pestaña **Consultar Base de Datos**.  
2. Selecciona un jugador del desplegable.  
3. Revisa estadísticas (pasa el ratón para ver descripciones).  
4. Añade hasta 3 jugadores para compararlos en un gráfico de radar.  
5. Descarga la imagen con **Exportar Gráfico**.

---

## Exportar resultados

- **PDF**: informe con discusiones, matrices y nivel de consenso.  
- **PNG**: gráfica de radar comparativa (`grafico_radar.png`).  

---

## Solución de problemas

- **Error al conectar con MongoDB**: revisa `MONGO_URI` y comprueba que MongoDB esté activo.  
- **API Key inválida**: asegúrate de que las claves en `.env` sean correctas y no estén expiradas.  
- **CSV mal formateado**: la cabecera debe ser `Jugador, Criterio 1, Criterio 2, ...`.  
- **Error en respuesta de agente**: reinicia el flujo de evaluación.

---

## Licencia

Este proyecto está bajo la licencia Apache 2.0. Véase [LICENSE](LICENSE).
