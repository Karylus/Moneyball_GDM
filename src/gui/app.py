import tkinter as tk
from tkinter import ttk, messagebox, StringVar
import sys
import os
import threading
import json
import csv
import re
from io import StringIO
import random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from fpdf import FPDF

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.agentes.analista_qwen import configurar_agente as configurar_agente_qwen
from src.agentes.analista_gemini import configurar_agente as configurar_agente_gemini
from src.agentes.analista_groq import configurar_agente as configurar_agente_groq
from src.data_management.data_loader import cargar_estadisticas_jugadores
from src.core.logica_ranking import calcular_ranking_jugadores, calcular_ponderacion_estadisticas, normalizar_puntuacion_individual
from src.core.fuzzy_matrices import generar_flpr, calcular_flpr_comun, calcular_matrices_flpr
from src.core.logica_consenso import calcular_matriz_similitud, calcular_cr
from langchain_core.prompts import ChatPromptTemplate


class MoneyballApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Moneyball")
        self.geometry("1600x1080")
        self.iconbitmap("icono.ico")

        self.colors = {
            "bg_dark_main": "#262626",
            "bg_dark_widget": "#333333",
            "bg_dark_entry": "#404040",
            "bg_dark_secondary": "#4A4A4A",
            "fg_light": "#E0E0E0",
            "fg_white": "#FFFFFF",
            "accent_color": "#007ACC",
            "accent_secondary": "#005C99",
            "disabled_fg": "#707070",
            "tooltip_bg": "#3A3A3A",
            "tooltip_border": "#007ACC",
            "red_accent": "#E53935",
            "green_accent": "#4CAF50",
        }

        self.configure(background=self.colors["bg_dark_main"])

        self.style = ttk.Style(self)
        self.style.theme_use('clam')

        # Configuraciones generales de estilo
        self.style.configure(".", background=self.colors["bg_dark_widget"], foreground=self.colors["fg_light"])

        self.style.configure("TNotebook",
                             background=self.colors["bg_dark_main"],
                             borderwidth=0)
        self.style.configure("TNotebook.Tab",
                             background=self.colors["bg_dark_widget"],
                             foreground=self.colors["fg_light"],
                             padding=[10, 7],
                             font=("Arial", 11, "bold"),
                             borderwidth=0)
        self.style.map("TNotebook.Tab",
                       background=[("selected", self.colors["accent_color"]),
                                   ("active", self.colors["accent_secondary"])],
                       foreground=[("selected", self.colors["fg_white"]),
                                   ("active", self.colors["fg_white"])],
                       borderwidth=[("selected", 0)])


        self.style.configure("TFrame", background=self.colors["bg_dark_widget"])

        self.style.configure("TLabel",
                             background=self.colors["bg_dark_widget"],
                             foreground=self.colors["fg_light"],
                             font=("Arial", 10))

        self.style.configure("TLabelFrame",
                             background=self.colors["bg_dark_widget"],
                             foreground=self.colors["fg_light"],
                             font=("Arial", 11, "bold"),
                             borderwidth=1,
                             relief=tk.SOLID)
        self.style.configure("TLabelFrame.Label",
                             background=self.colors["bg_dark_widget"],
                             foreground=self.colors["fg_light"],
                             font=("Arial", 11, "bold"))


        self.style.configure("TButton",
                             font=("Arial", 10, "bold"),
                             background=self.colors["accent_color"],
                             foreground=self.colors["fg_white"],
                             borderwidth=1,
                             relief=tk.FLAT,
                             padding=[10, 5])
        self.style.map("TButton",
                       background=[("active", self.colors["accent_secondary"]),
                                   ("disabled", self.colors["bg_dark_secondary"])],
                       foreground=[("disabled", self.colors["disabled_fg"])],
                       relief=[("pressed", tk.SUNKEN), ("active", tk.RAISED)])


        self.style.configure("TEntry",
                             fieldbackground=self.colors["bg_dark_entry"],
                             foreground=self.colors["fg_light"],
                             insertcolor=self.colors["fg_light"],
                             borderwidth=1,
                             relief=tk.FLAT,
                             padding=6)
        self.style.map("TEntry",
                       bordercolor=[("focus", self.colors["accent_color"])],
                       relief=[("focus", tk.SOLID)])


        self.style.configure("TCombobox",
                             fieldbackground=self.colors["bg_dark_entry"],
                             background=self.colors["bg_dark_entry"],
                             foreground=self.colors["fg_light"],
                             arrowcolor=self.colors["fg_light"],
                             selectbackground=self.colors["accent_secondary"],
                             selectforeground=self.colors["fg_white"],
                             borderwidth=1,
                             relief=tk.FLAT,
                             padding=6)
        self.style.map("TCombobox",
                       bordercolor=[("focus", self.colors["accent_color"])],
                       relief=[("focus", tk.SOLID)],
                       background=[('readonly', self.colors["bg_dark_entry"])],
                       fieldbackground=[('readonly', self.colors["bg_dark_entry"])],
                       foreground=[('readonly', self.colors["fg_light"])])

        self.option_add('*TCombobox*Listbox.background', self.colors["bg_dark_entry"])
        self.option_add('*TCombobox*Listbox.foreground', self.colors["fg_light"])
        self.option_add('*TCombobox*Listbox.selectBackground', self.colors["accent_secondary"])
        self.option_add('*TCombobox*Listbox.selectForeground', self.colors["fg_white"])
        self.option_add('*TCombobox*Listbox.font', ("Arial", 10))
        self.option_add('*TCombobox*Listbox.bd', 0)
        self.option_add('*TCombobox*Listbox.highlightthickness', 0)


        self.style.configure("TScrollbar",
                             background=self.colors["bg_dark_widget"],
                             troughcolor=self.colors["bg_dark_main"],
                             bordercolor=self.colors["bg_dark_widget"],
                             arrowcolor=self.colors["fg_light"],
                             relief=tk.FLAT)
        self.style.map("TScrollbar",
                       background=[("active", self.colors["accent_color"])])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.evaluacion_tab = PestañaEvaluacion(self.notebook, self.colors)
        self.database_tab = PestañaBaseDeDatos(self.notebook, self.colors)

        self.notebook.add(self.evaluacion_tab, text="Evaluar Jugadores")
        self.notebook.add(self.database_tab, text="Consultar Estadísticas")

        self.initialize_agents_thread = threading.Thread(target=self.iniciar_agentes)
        self.initialize_agents_thread.daemon = True
        self.initialize_agents_thread.start()

        self.status_label = ttk.Label(self, text="Iniciando agentes... Por favor espere.", anchor="center")

        self.status_label.configure(background=self.colors["bg_dark_main"],
                                    foreground=self.colors["fg_light"],
                                    font=("Arial", 9))
        self.status_label.pack(pady=5, fill=tk.X)

        self.after(1000, self.check_agents_ready)

    def iniciar_agentes(self):
        """Inicializa los agentes en un hilo separado"""
        try:
            self.agente_qwen = configurar_agente_qwen()
            self.agente_gemini = configurar_agente_gemini()
            self.agente_groq = configurar_agente_groq()
            self.agents_ready = True

            self.evaluacion_tab.establecer_agentes(self.agente_qwen, self.agente_gemini, self.agente_groq)
        except Exception as e:
            self.agents_ready = False
            self.agent_error = str(e)
            print(f"Error initializing agents: {e}")

    def check_agents_ready(self):
        """Verifica si los agentes están listos y actualiza la interfaz"""
        if hasattr(self, 'agents_ready'):
            if self.agents_ready:
                self.status_label.config(text="Agentes iniciados correctamente.", foreground=self.colors["green_accent"])
                self.after(3000, lambda: self.status_label.pack_forget())
            else:
                self.status_label.config(text=f"Error al iniciar agentes: {self.agent_error}", foreground=self.colors["red_accent"])
        else:
            self.after(1000, self.check_agents_ready)


class PestañaEvaluacion(ttk.Frame):
    """
    Pestaña para la evaluación de los jugadores.
    Permite al usuario seleccionar hasta 3 jugadores y criterios para que los agentes los evalúen.
    """
    def __init__(self, padre, colores):
        super().__init__(padre)
        self.colores = colores

        self.agente_qwen = None
        self.agente_gemini = None
        self.agente_groq = None

        self.jugadores_seleccionados = []
        self.criterios_seleccionados = []
        self.max_jugadores = 3
        self.datos_jugadores = {}

        self.valores_linguisticos = ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]

        self.temporadas = ["2022-2023", "2023-2024", "2024-2025"]
        self.temporada_seleccionada = StringVar(value=self.temporadas[-1])

        self.cargar_datos_jugadores()
        self.crear_widgets()

    def cargar_datos_jugadores(self):
        try:
            temporada = self.temporada_seleccionada.get()
            self.df_jugadores = cargar_estadisticas_jugadores(temporada)
            if isinstance(self.df_jugadores, str):
                messagebox.showerror("Error", f"Error al cargar datos de jugadores: {self.df_jugadores}")
                self.df_jugadores = None
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar datos de jugadores: {str(e)}")
            self.df_jugadores = None

    def limpiar_comillas_matriz(self, matriz):
        return [
            [str(x).replace('"', '').replace("'", '') for x in fila]
            for fila in matriz
        ]

    def crear_widgets(self):
        marco_principal = ttk.Frame(self)
        marco_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        marco_izquierdo = ttk.Frame(marco_principal)
        marco_izquierdo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        marco_derecho = ttk.Frame(marco_principal)
        marco_derecho.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        marco_busqueda = ttk.LabelFrame(marco_izquierdo, text="Buscar Jugadores")
        marco_busqueda.pack(fill=tk.X, pady=5, ipady=5)

        marco_temporada = ttk.Frame(marco_busqueda)
        marco_temporada.pack(fill=tk.X, padx=10, pady=(5,10))

        ttk.Label(marco_temporada, text="Temporada:").pack(side=tk.LEFT, padx=(0,5))
        self.combo_temporada = ttk.Combobox(marco_temporada, textvariable=self.temporada_seleccionada,
                                            values=self.temporadas, state="readonly", width=8)
        self.combo_temporada.pack(side=tk.LEFT, padx=5)
        self.combo_temporada.bind("<<ComboboxSelected>>", self.al_seleccionar_temporada)

        self.var_busqueda = StringVar()
        self.entrada_busqueda = ttk.Entry(marco_busqueda, textvariable=self.var_busqueda)
        self.entrada_busqueda.pack(fill=tk.X, padx=10, pady=(0,10))
        self.entrada_busqueda.bind("<KeyRelease>", self.al_escribir_busqueda)

        marco_lista_jugadores = ttk.Frame(marco_busqueda)
        marco_lista_jugadores.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,5))

        self.lista_jugadores = tk.Listbox(marco_lista_jugadores, height=8,
                                          bg=self.colores["bg_dark_entry"], fg=self.colores["fg_light"],
                                          selectbackground=self.colores["accent_color"],
                                          selectforeground=self.colores["fg_white"],
                                          borderwidth=0, highlightthickness=0,
                                          font=("Arial", 10))
        self.lista_jugadores.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        barra_jugadores = ttk.Scrollbar(marco_lista_jugadores, command=self.lista_jugadores.yview)
        barra_jugadores.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista_jugadores.config(yscrollcommand=barra_jugadores.set)

        boton_añadir_jugador = ttk.Button(marco_busqueda, text="Añadir Jugador", command=self.añadir_jugador_seleccionado)
        boton_añadir_jugador.pack(fill=tk.X, padx=10, pady=(5,10))

        marco_jugadores_seleccionados = ttk.LabelFrame(marco_izquierdo, text="Jugadores Seleccionados")
        marco_jugadores_seleccionados.pack(fill=tk.X, pady=5, ipady=5)

        self.lista_jugadores_seleccionados = tk.Listbox(marco_jugadores_seleccionados, height=3,
                                                        bg=self.colores["bg_dark_entry"], fg=self.colores["fg_light"],
                                                        selectbackground=self.colores["accent_color"],
                                                        selectforeground=self.colores["fg_white"],
                                                        borderwidth=0, highlightthickness=0,
                                                        font=("Arial", 10))
        self.lista_jugadores_seleccionados.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        boton_eliminar_jugador = ttk.Button(marco_jugadores_seleccionados, text="Eliminar Jugador", command=self.eliminar_jugador_seleccionado)
        boton_eliminar_jugador.pack(fill=tk.X, padx=10, pady=(0,10))

        marco_criterios = ttk.LabelFrame(marco_izquierdo, text="Criterios de Evaluación")
        marco_criterios.pack(fill=tk.X, pady=5, ipady=5)

        self.criterios_predefinidos = {
            "General": ["Técnica", "Físico", "Visión de juego", "Posicionamiento", "Toma de decisiones", "Liderazgo", "Disciplina táctica", "Versatilidad"],
            "Porteros": ["Paradas", "Juego aéreo", "Juego con los pies", "Reflejos", "Posicionamiento", "Comunicación", "Salidas", "Distribución", "Penaltis"],
            "Defensas": ["Anticipación", "Juego aéreo", "Entradas", "Posicionamiento", "Salida de balón", "Marcaje", "Bloqueos", "Despejes", "Velocidad", "Agresividad"],
            "Mediocentros defensivos": ["Recuperación", "Pases", "Posicionamiento", "Visión de juego", "Resistencia", "Cobertura", "Presión", "Duelos aéreos", "Intercepciones"],
            "Mediocentros": ["Control", "Pases", "Visión de juego", "Técnica", "Movilidad", "Llegada al área", "Regate", "Creatividad", "Trabajo defensivo"],
            "Mediopuntas": ["Creatividad", "Regate", "Pases", "Disparo", "Movimiento sin balón", "Asociación", "Llegada", "Finalización", "Desmarque"],
            "Carrileros": ["Velocidad", "Centros", "Resistencia", "Defensa", "Ataque", "Regate", "Apoyo ofensivo", "Cobertura defensiva", "Desborde"],
            "Delanteros": ["Definición", "Movimiento", "Juego aéreo", "Técnica", "Posicionamiento", "Desmarque", "Finalización", "Regate", "Asociación", "Presión alta"]
        }

        marco_posicion = ttk.Frame(marco_criterios)
        marco_posicion.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(marco_posicion, text="Posición:").pack(side=tk.LEFT, padx=(0,5))
        self.var_posicion = StringVar()
        posiciones = list(self.criterios_predefinidos.keys())
        self.combo_posicion = ttk.Combobox(marco_posicion, textvariable=self.var_posicion,
                                           values=posiciones, state="readonly", width=20)
        self.combo_posicion.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.combo_posicion.current(0)
        self.combo_posicion.bind("<<ComboboxSelected>>", self.al_seleccionar_posicion)

        marco_seleccion_criterios = ttk.Frame(marco_criterios)
        marco_seleccion_criterios.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        marco_criterios_disponibles = ttk.LabelFrame(marco_seleccion_criterios, text="Disponibles")
        marco_criterios_disponibles.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        self.lista_criterios_disponibles = tk.Listbox(marco_criterios_disponibles, height=5,
                                                      bg=self.colores["bg_dark_entry"], fg=self.colores["fg_light"],
                                                      selectbackground=self.colores["accent_color"],
                                                      selectforeground=self.colores["fg_white"],
                                                      borderwidth=0, highlightthickness=0,
                                                      font=("Arial", 10))
        self.lista_criterios_disponibles.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        marco_criterios_seleccionados = ttk.LabelFrame(marco_seleccion_criterios, text="Seleccionados")
        marco_criterios_seleccionados.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
        self.lista_criterios_seleccionados = tk.Listbox(marco_criterios_seleccionados, height=5,
                                                        bg=self.colores["bg_dark_entry"], fg=self.colores["fg_light"],
                                                        selectbackground=self.colores["accent_color"],
                                                        selectforeground=self.colores["fg_white"],
                                                        borderwidth=0, highlightthickness=0,
                                                        font=("Arial", 10))
        self.lista_criterios_seleccionados.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        marco_botones_criterios = ttk.Frame(marco_criterios)
        marco_botones_criterios.pack(fill=tk.X, padx=10, pady=5)
        boton_añadir_criterio = ttk.Button(marco_botones_criterios, text="Añadir →", command=self.añadir_criterio_seleccionado)
        boton_añadir_criterio.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        boton_eliminar_criterio = ttk.Button(marco_botones_criterios, text="← Eliminar", command=self.eliminar_criterio)
        boton_eliminar_criterio.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

        self.actualizar_criterios_disponibles("General")

        marco_parametros = ttk.LabelFrame(marco_izquierdo, text="Parámetros de Evaluación")
        marco_parametros.pack(fill=tk.X, pady=5, ipady=5)

        marco_consenso = ttk.Frame(marco_parametros)
        marco_consenso.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(marco_consenso, text="Nivel de consenso (0-1):").pack(side=tk.LEFT)
        self.var_consenso = StringVar(value="0.90")
        entrada_consenso = ttk.Entry(marco_consenso, textvariable=self.var_consenso, width=5)
        entrada_consenso.pack(side=tk.RIGHT)

        marco_rondas = ttk.Frame(marco_parametros)
        marco_rondas.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(marco_rondas, text="Máximo de rondas:").pack(side=tk.LEFT)
        self.var_rondas = StringVar(value="3")
        entrada_rondas = ttk.Entry(marco_rondas, textvariable=self.var_rondas, width=5)
        entrada_rondas.pack(side=tk.RIGHT)

        self.boton_evaluar = ttk.Button(marco_izquierdo, text="Evaluar Jugadores", command=self.evaluar_jugadores)
        self.boton_evaluar.pack(fill=tk.X, pady=10, ipady=5)

        marco_resultados = ttk.LabelFrame(marco_derecho, text="Resultados de la Evaluación")
        marco_resultados.pack(fill=tk.BOTH, expand=True, ipady=5)

        self.texto_resultados = tk.Text(marco_resultados, wrap=tk.WORD, state=tk.DISABLED,
                                        bg=self.colores["bg_dark_entry"], fg=self.colores["fg_light"],
                                        insertbackground=self.colores["fg_white"],
                                        borderwidth=0, highlightthickness=0,
                                        font=("Arial", 10), relief=tk.FLAT, padx=5, pady=5)
        self.texto_resultados.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)

        barra_resultados = ttk.Scrollbar(marco_resultados, command=self.texto_resultados.yview)
        barra_resultados.pack(side=tk.RIGHT, fill=tk.Y)
        self.texto_resultados.config(yscrollcommand=barra_resultados.set)

        self.agregar_resultado("Bienvenido al sistema de evaluación de jugadores.\n\n"
                              "Instrucciones:\n"
                              "1. Seleccione hasta 3 jugadores\n"
                              "2. Defina los criterios de evaluación\n"
                              "3. Ajuste los parámetros si lo desea\n"
                              "4. Haga clic en 'Evaluar Jugadores'\n\n"
                              "Los agentes evaluarán a los jugadores y mostrarán los resultados aquí.")

        self.boton_exportar_pdf = ttk.Button(marco_izquierdo, text="Exportar a PDF", command=self.exportar_pdf, state=tk.DISABLED)
        self.boton_exportar_pdf.pack(fill=tk.X, pady=5, ipady=5)

    def establecer_agentes(self, agente_qwen, agente_gemini, agente_groq):
        self.agente_qwen = agente_qwen
        self.agente_gemini = agente_gemini
        self.agente_groq = agente_groq

        if hasattr(self, 'texto_resultados') and self.texto_resultados.winfo_exists():
            self.agregar_resultado("Los agentes están listos para la evaluación.")

    def agregar_resultado(self, mensaje):
        if not hasattr(self, 'texto_resultados') or not self.texto_resultados.winfo_exists():
            return
        self.texto_resultados.config(state=tk.NORMAL)
        self.texto_resultados.insert(tk.END, f"{mensaje}\n\n")
        self.texto_resultados.see(tk.END)
        self.texto_resultados.config(state=tk.DISABLED)

    def al_seleccionar_temporada(self, evento):
        self.cargar_datos_jugadores()
        self.lista_jugadores.delete(0, tk.END)
        self.var_busqueda.set("")

    def al_escribir_busqueda(self, evento):
        texto_busqueda = self.var_busqueda.get().lower()
        self.lista_jugadores.delete(0, tk.END)
        if not texto_busqueda or self.df_jugadores is None:
            return
        try:
            if 'normalized_name' not in self.df_jugadores.columns:
                self.df_jugadores['normalized_name'] = self.df_jugadores['Player'].fillna('').astype(str).str.lower()
            mascara = self.df_jugadores['normalized_name'].astype(str).str.contains(texto_busqueda, na=False)
            jugadores_filtrados = self.df_jugadores[mascara]
            jugadores_filtrados = jugadores_filtrados.head(20)
            self.datos_jugadores.clear()
            for _, fila_jugador in jugadores_filtrados.iterrows():
                nombre_jugador = fila_jugador.get('Player', 'Desconocido')
                self.datos_jugadores[nombre_jugador] = fila_jugador
                self.lista_jugadores.insert(tk.END, nombre_jugador)
        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar jugadores: {str(e)}")

    def añadir_jugador_seleccionado(self):
        seleccion = self.lista_jugadores.curselection()
        if not seleccion:
            messagebox.showinfo("Información", "Por favor, seleccione un jugador de la lista.")
            return
        nombre = self.lista_jugadores.get(seleccion[0])
        if nombre in self.jugadores_seleccionados:
            messagebox.showinfo("Información", f"El jugador '{nombre}' ya está seleccionado.")
            return
        if len(self.jugadores_seleccionados) >= self.max_jugadores:
            messagebox.showinfo("Información", f"Solo puede seleccionar hasta {self.max_jugadores} jugadores.")
            return
        self.jugadores_seleccionados.append(nombre)
        self.lista_jugadores_seleccionados.insert(tk.END, nombre)

    def eliminar_jugador_seleccionado(self):
        seleccion = self.lista_jugadores_seleccionados.curselection()
        if not seleccion:
            messagebox.showinfo("Información", "Por favor, seleccione un jugador de la lista para eliminarlo.")
            return
        indice = seleccion[0]
        nombre = self.lista_jugadores_seleccionados.get(indice)
        if nombre in self.jugadores_seleccionados:
            self.jugadores_seleccionados.remove(nombre)
        self.lista_jugadores_seleccionados.delete(indice)

    def al_seleccionar_posicion(self, evento):
        posicion = self.var_posicion.get()
        self.actualizar_criterios_disponibles(posicion)

    def actualizar_criterios_disponibles(self, posicion):
        self.lista_criterios_disponibles.delete(0, tk.END)
        if posicion in self.criterios_predefinidos:
            for criterio in self.criterios_predefinidos[posicion]:
                if criterio not in self.criterios_seleccionados:
                    self.lista_criterios_disponibles.insert(tk.END, criterio)

    def añadir_criterio_seleccionado(self):
        seleccion = self.lista_criterios_disponibles.curselection()
        if not seleccion:
            messagebox.showinfo("Información", "Por favor, seleccione un criterio de la lista disponible.")
            return
        criterio = self.lista_criterios_disponibles.get(seleccion[0])
        if criterio in self.criterios_seleccionados:
            messagebox.showinfo("Información", f"El criterio '{criterio}' ya está en la lista.")
            return
        self.criterios_seleccionados.append(criterio)
        self.lista_criterios_seleccionados.insert(tk.END, criterio)
        self.lista_criterios_disponibles.delete(seleccion[0])

    def eliminar_criterio(self):
        seleccion = self.lista_criterios_seleccionados.curselection()
        if not seleccion:
            messagebox.showinfo("Información", "Por favor, seleccione un criterio de la lista para eliminarlo.")
            return
        indice = seleccion[0]
        criterio = self.lista_criterios_seleccionados.get(indice)
        if criterio in self.criterios_seleccionados:
            self.criterios_seleccionados.remove(criterio)
        self.lista_criterios_seleccionados.delete(indice)
        posicion_actual = self.var_posicion.get()
        if posicion_actual in self.criterios_predefinidos and \
           criterio in self.criterios_predefinidos[posicion_actual]:
            if criterio not in self.lista_criterios_disponibles.get(0, tk.END):
                self.lista_criterios_disponibles.insert(tk.END, criterio)

    def evaluar_jugadores(self):
        if not self.jugadores_seleccionados:
            messagebox.showinfo("Información", "Por favor, seleccione al menos un jugador.")
            return
        if not self.criterios_seleccionados:
            messagebox.showinfo("Información", "Por favor, ingrese al menos un criterio.")
            return
        if not all([self.agente_qwen, self.agente_gemini, self.agente_groq]):
            messagebox.showinfo("Información", "Los agentes aún no están inicializados. Por favor, espere.")
            return
        try:
            consenso_minimo = float(self.var_consenso.get())
            if not (0 <= consenso_minimo <= 1):
                messagebox.showinfo("Información", "El nivel de consenso debe estar entre 0 y 1.")
                return
        except ValueError:
            messagebox.showinfo("Información", "Por favor, ingrese un valor numérico válido para el nivel de consenso.")
            return
        try:
            max_rondas = int(self.var_rondas.get())
            if max_rondas <= 0:
                messagebox.showinfo("Información", "El número máximo de rondas debe ser mayor que 0.")
                return
        except ValueError:
            messagebox.showinfo("Información", "Por favor, ingrese un valor numérico válido para el máximo de rondas.")
            return
        self.boton_evaluar.config(state=tk.DISABLED)
        self.texto_resultados.config(state=tk.NORMAL)
        self.texto_resultados.delete("1.0", tk.END)
        self.texto_resultados.config(state=tk.DISABLED)
        self.agregar_resultado("Iniciando evaluación de jugadores...\n")
        self.agregar_resultado(f"Jugadores: {', '.join(self.jugadores_seleccionados)}")
        self.agregar_resultado(f"Criterios: {', '.join(self.criterios_seleccionados)}")
        self.agregar_resultado(f"Nivel de consenso: {consenso_minimo}")
        self.agregar_resultado(f"Máximo de rondas: {max_rondas}")
        threading.Thread(target=self.ejecutar_evaluacion, args=(
            self.jugadores_seleccionados,
            self.criterios_seleccionados,
            consenso_minimo,
            max_rondas
        ), daemon=True).start()

    def exportar_pdf(self):
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
        pdf.add_font('DejaVu', 'I', 'DejaVuSans-Oblique.ttf', uni=True)
        pdf.add_font('DejaVu', 'BI', 'DejaVuSans-BoldOblique.ttf', uni=True)
        pdf.set_font("DejaVu", size=12)
        pdf.cell(0, 10, "Resultados de la Evaluación", ln=True)
        pdf.ln(5)

        pdf.set_font("DejaVu", style="B", size=12)
        pdf.cell(0, 10, "Jugadores evaluados:", ln=True)
        pdf.set_font("DejaVu", size=10)
        for jugador in self.jugadores_seleccionados:
            pdf.cell(0, 8, f"- {jugador}", ln=True)
        pdf.ln(2)

        pdf.set_font("DejaVu", style="B", size=12)
        pdf.cell(0, 10, "Criterios de evaluación:", ln=True)
        pdf.set_font("DejaVu", size=10)
        for criterio in self.criterios_seleccionados:
            pdf.cell(0, 8, f"- {criterio}", ln=True)
        pdf.ln(5)

        pdf.set_font("DejaVu", style="B", size=12)
        pdf.cell(0, 10, "Matrices:", ln=True)
        pdf.set_font("DejaVu", style="I", size=10)
        for nombre, matriz in (self.resultados_evaluacion.get("matrices") or {}).items():
            pdf.cell(0, 8, f"{nombre}:", ln=True)
            for fila in matriz:
                pdf.cell(0, 8, ", ".join(str(x) for x in fila), ln=True)
            pdf.ln(2)

        if self.resultados_evaluacion.get("discusiones"):
            pdf.set_font("DejaVu", style="B", size=12)
            pdf.cell(0, 10, "Discusiones:", ln=True)
            pdf.set_font("DejaVu", size=10)
            pdf.multi_cell(0, 8, str(self.resultados_evaluacion["discusiones"]))
            pdf.ln(2)

        pdf.set_font("DejaVu", style="B", size=12)
        pdf.cell(0, 10, "Nivel de Consenso (CR):", ln=True)
        pdf.set_font("DejaVu", style="I", size=10)
        pdf.cell(0, 8, str(self.resultados_evaluacion.get("crs", "")), ln=True)
        pdf.ln(2)

        pdf.set_font("DejaVu", style="B", size=12)
        pdf.cell(0, 10, "Ranking Final:", ln=True)
        pdf.set_font("DejaVu", size=10)
        for jugador, puntuacion in (self.resultados_evaluacion.get("ranking") or []):
            pdf.cell(0, 8, f"{jugador}: {round(puntuacion, 3)}", ln=True)

        pdf.output("evaluacion_resultados.pdf")

        messagebox.showinfo("Exportación", "PDF exportado correctamente.")

    def mostrar_distancias_al_consenso(self, flpr_usuario, flpr_agente_qwen, flpr_agente_gemini, flpr_agente_groq, flpr_colectiva):
        distancias_agentes = []

        if flpr_usuario is not None and flpr_colectiva is not None:
            similitud_usuario = np.mean(calcular_matriz_similitud(flpr_usuario, flpr_colectiva))
            distancia_usuario = 1 - similitud_usuario
            distancias_agentes.append(("Usuario", distancia_usuario))

        if flpr_agente_qwen is not None and flpr_colectiva is not None:
            similitud_qwen = np.mean(calcular_matriz_similitud(flpr_agente_qwen, flpr_colectiva))
            distancia_qwen = 1 - similitud_qwen
            distancias_agentes.append(("Agente Qwen", distancia_qwen))

        if flpr_agente_gemini is not None and flpr_colectiva is not None:
            similitud_gemini = np.mean(calcular_matriz_similitud(flpr_agente_gemini, flpr_colectiva))
            distancia_gemini = 1 - similitud_gemini
            distancias_agentes.append(("Agente Gemini", distancia_gemini))

        if flpr_agente_groq is not None and flpr_colectiva is not None:
            similitud_groq = np.mean(calcular_matriz_similitud(flpr_agente_groq, flpr_colectiva))
            distancia_groq = 1 - similitud_groq
            distancias_agentes.append(("Agente Groq", distancia_groq))

        distancias_agentes.sort(key=lambda x: x[1], reverse=True)

        self.agregar_resultado(f"\n=== Ranking de Agentes por Distancia al Consenso ===")
        self.agregar_resultado("Este ranking muestra qué agentes están más lejos de la opinión colectiva:")
        for posicion, (agente, distancia) in enumerate(distancias_agentes, 1):
            self.agregar_resultado(f"{posicion}. {agente} - Distancia al consenso: {distancia:.3f}")

        if distancias_agentes:
            agente_mas_lejano = distancias_agentes[0][0]
            distancia_maxima = distancias_agentes[0][1]
            self.agregar_resultado(f"\nEl agente que más influye en reducir el consenso global es: {agente_mas_lejano} (distancia: {distancia_maxima:.3f})")

    def ejecutar_evaluacion(self, jugadores, criterios, consenso_minimo, max_rondas):
        """Ejecuta el proceso de evaluación en un hilo separado"""
        try:
            prompt_template = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "Eres un analista de fútbol experto en evaluar jugadores. "
                    "Tu deber es asignar una calificación lingüística (Muy Bajo, Bajo, Medio, Alto, Muy Alto) a cada jugador dado para cada criterio proporcionado. "
                    "No compares los jugadores entre sí; evalúalos individualmente. Usa la herramienta 'analizador_jugadores'."
                    "Responde siempre SOLO en el formato CSV siguiente, no devuelvas ningún texto adicional\n "

                    "Output format:\n\n"
                    "1. La Primera linea es SIEMPRE: ```CSV\n"
                    "2. El encabezado será con los campos: la palabra Jugador, y cada criterio separado por comas\n"
                    "3. Una linea extra por cada nombre de jugador junto a SOLO sus calificaciones lingüísticas, separadas por comas.\n"
                    "4. Ultima linea: ```\n\n"

                    "IMPORTANTE: Si no puedes generar la salida en ese formato EXACTO, tu respuesta será eliminada."
                    "No inventes por tu cuenta el formato, sigue las instrucciones al pie de la letra.\n\n"
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

            def procesar_csv_agente(output_agente, criterios_list):
                matriz = []
                try:
                    csv_match = re.search(r'```(?:csv|CSV)?\s*([\s\S]*?)```', output_agente)
                    if csv_match:
                        csv_content = csv_match.group(1).strip()
                    else:
                        lines = output_agente.strip().split('\n')
                        header_line_index = -1
                        for i, line in enumerate(lines):
                            if "jugador" in line.lower() and all(c.lower() in line.lower() for c in criterios_list):
                                header_line_index = i
                                break
                        if header_line_index != -1:
                             csv_content = '\n'.join(lines[header_line_index:]).strip()
                        else:
                            potential_csv_lines = [line for line in lines if line.count(',') >= len(criterios_list)-1]
                            if potential_csv_lines:
                                csv_content = "\n".join(potential_csv_lines)
                            else:
                                self.agregar_resultado(f"ADVERTENCIA: No se pudo extraer contenido CSV claro de la respuesta del agente.")
                                return [], False


                    csv_data = StringIO(csv_content)
                    reader = csv.DictReader(csv_data)

                    for row in reader:
                        calificaciones = []
                        csv_headers = [h.strip().lower() for h in reader.fieldnames if h]

                        for criterio_esperado in criterios_list:
                            criterio_esperado_lower = criterio_esperado.lower()
                            valor_encontrado = None

                            for csv_header in csv_headers:
                                if criterio_esperado_lower == csv_header:
                                    valor_encontrado = row.get(reader.fieldnames[csv_headers.index(csv_header)])
                                    break
                                elif criterio_esperado_lower in csv_header: # Coincidencia parcial (contenida)
                                    valor_encontrado = row.get(reader.fieldnames[csv_headers.index(csv_header)])
                                    break

                            if valor_encontrado is not None:
                                calificaciones.append(str(valor_encontrado).replace("'", "").replace('"', "").strip())
                            else:
                                if len(row) == len(criterios_list) + 1:
                                    try:
                                        idx_criterio = criterios_list.index(criterio_esperado)
                                        valor_encontrado = list(row.values())[idx_criterio + 1]
                                        calificaciones.append(str(valor_encontrado).replace("'", "").replace('"', "").strip())
                                        self.agregar_resultado(f"ADVERTENCIA: Criterio '{criterio_esperado}' no encontrado por nombre, usando posición.")
                                    except (ValueError, IndexError):
                                        self.agregar_resultado(f"ERROR: Criterio '{criterio_esperado}' no encontrado en los datos del CSV ni por posición.")
                                        return [], False
                                else:
                                    self.agregar_resultado(f"ERROR: Criterio '{criterio_esperado}' no encontrado en los datos del CSV. Headers: {csv_headers}")
                                    return [], False
                        matriz.append(calificaciones)
                    if not matriz:
                        self.agregar_resultado(f"ERROR: No se pudieron extraer datos de la matriz del CSV. Contenido CSV procesado:\n{csv_content}")
                        return [], False
                    return matriz, True
                except Exception as e:
                    self.agregar_resultado(f"ERROR: No se pudo procesar la salida del agente: {str(e)}\nContenido CSV intentado:\n{csv_content if 'csv_content' in locals() else 'No disponible'}")
                    return [], False

            def generar_matriz_aleatoria(jugadores_list, criterios_list, valores_linguisticos):
                import random
                matriz = []
                for _ in jugadores_list:
                    calificaciones = [random.choice(valores_linguisticos) for _ in criterios_list]
                    matriz.append(calificaciones)
                return matriz

            def evaluar_con_agente(agente, prompt_str, jugadores_list, criterios_list,
                                   valores_linguisticos, nombre_agente, max_intentos_agente):
                self.agregar_resultado(f"\n=== Evaluación con el Agente {nombre_agente} ===")
                intento_actual = 0
                matriz_agente = []



                while intento_actual < max_intentos_agente:
                    intento_actual += 1
                    self.agregar_resultado(
                        f"Consultando al agente {nombre_agente} (Intento {intento_actual}/{max_intentos_agente})...")
                    try:

                        respuesta_agente = agente.invoke({"input": prompt_str})
                        output_agente = respuesta_agente.get("output",
                                                             "No hay respuesta del agente.")
                    except Exception as e:
                        output_agente = f"ERROR: Excepción al invocar agente {nombre_agente}: {str(e)}"
                        self.agregar_resultado(output_agente)
                        reintentar = messagebox.askretrycancel(
                            "Error en agente",
                            f"El agente {nombre_agente} falló:\n{str(e)}\n\n¿Desea reintentar?"
                        )
                        if not reintentar:
                            self.agregar_resultado(
                                f"Evaluación abortada por el usuario tras fallo en {nombre_agente}.")
                            return [], "Abortado por el usuario"
                        else:
                            intento_actual -= 1
                        continue

                    if nombre_agente == "Qwen":
                        output_agente = re.sub(r"<think>.*?</think>", "", output_agente,
                                               flags=re.DOTALL)

                    self.agregar_resultado(
                        f"\nRespuesta del Agente {nombre_agente}:\n{output_agente}")

                    if "ERROR:" in output_agente.upper() or "NO HAY RESPUESTA" in output_agente.upper():
                        self.agregar_resultado(
                            f"El agente {nombre_agente} reportó un error o no respondió.")
                        reintentar = messagebox.askretrycancel(
                            "Error en agente",
                            f"El agente {nombre_agente} reportó un error o no respondió.\n\n¿Desea reintentar?"
                        )
                        if not reintentar:
                            self.agregar_resultado(
                                f"Evaluación abortada por el usuario tras fallo en {nombre_agente}.")
                            return [], "Abortado por el usuario"
                        else:
                            intento_actual -= 1
                        continue

                    matriz_agente, exito = procesar_csv_agente(output_agente, criterios_list)

                    if exito:
                        self.agregar_resultado(
                            f"✅ CSV procesado correctamente para el agente {nombre_agente}.")
                        break
                    elif intento_actual >= max_intentos_agente:
                        self.agregar_resultado(
                            f"Se alcanzó el número máximo de intentos ({max_intentos_agente}) para el agente {nombre_agente} o el CSV no fue válido.")
                        break
                    else:
                        self.agregar_resultado(f"Formato CSV no válido del agente {nombre_agente}.")
                        reintentar = messagebox.askretrycancel(
                            "Error en agente",
                            f"El agente {nombre_agente} devolvió un CSV no válido.\n\n¿Desea reintentar?"
                        )
                        if not reintentar:
                            self.agregar_resultado(
                                f"Evaluación abortada por el usuario tras fallo en {nombre_agente}.")
                            return [], "Abortado por el usuario"
                        else:
                            intento_actual -= 1

                if not matriz_agente:
                    self.agregar_resultado(
                        f"Generando valores lingüísticos aleatorios para el agente {nombre_agente}...")
                    matriz_agente = generar_matriz_aleatoria(jugadores_list, criterios_list,
                                                             valores_linguisticos)
                    self.agregar_resultado(
                        f"Se han generado valores lingüísticos aleatorios para el agente {nombre_agente}.")

                return matriz_agente, output_agente if 'output_agente' in locals() else "No se obtuvo respuesta."


            self.agregar_resultado("\nIniciando evaluación con los agentes...")

            matriz_agente_qwen, _ = evaluar_con_agente(
                self.agente_qwen, prompt, jugadores, criterios, self.valores_linguisticos, "Qwen", 1) # Solo un intento para qwen

            matriz_agente_gemini, _ = evaluar_con_agente(
                self.agente_gemini, prompt, jugadores, criterios, self.valores_linguisticos, "Gemini", max_intentos)

            matriz_agente_groq, _ = evaluar_con_agente(
                self.agente_groq, prompt, jugadores, criterios, self.valores_linguisticos, "Groq", max_intentos)


            self.agregar_resultado("\n\nAhora es tu turno de evaluar a los jugadores.")
            self.agregar_resultado("Por favor, selecciona las calificaciones en la ventana emergente.")

            user_matrices = self.get_user_evaluacion(jugadores, criterios)

            if not user_matrices:
                self.agregar_resultado("Evaluación cancelada por el usuario.")
                if hasattr(self, 'evaluate_button') and self.evaluate_button.winfo_exists():
                    self.evaluate_button.config(state=tk.NORMAL)
                return

            matriz_usuario = user_matrices



            matrices = {
                "Usuario": matriz_usuario,
                "Qwen": matriz_agente_qwen,
                "Gemini": matriz_agente_gemini,
                "Groq": matriz_agente_groq
            }

            self.agregar_resultado("\nCalculando matrices FLPR...")

            flpr_matrices = {}
            for nombre, matriz_eval in matrices.items():
                if not matriz_eval or not any(matriz_eval):
                    self.agregar_resultado(f"ADVERTENCIA: Matriz de evaluación para '{nombre}' está vacía. Saltando cálculo de FLPR.")
                    flpr_matrices[nombre] = None
                    continue

                flpr_matriz_calculada = None
                if criterios and len(matriz_eval[0]) == len(criterios):
                    for idx, criterio_item in enumerate(criterios):
                        calificaciones_criterio = [fila[idx] for fila in matriz_eval if len(fila) > idx]

                        if not calificaciones_criterio:
                             self.agregar_resultado(f"ADVERTENCIA: No hay calificaciones para el criterio '{criterio_item}' en la matriz de '{nombre}'.")
                             continue

                        flpr_criterio = generar_flpr(calificaciones_criterio)

                        if flpr_matriz_calculada is None:
                            flpr_matriz_calculada = flpr_criterio
                        elif flpr_criterio is not None :
                            flpr_matriz_calculada = calcular_flpr_comun(flpr_matriz_calculada, flpr_criterio)
                    flpr_matrices[nombre] = flpr_matriz_calculada
                else:
                    self.agregar_resultado(f"ADVERTENCIA: No se pudo calcular FLPR para '{nombre}' debido a discrepancia en criterios o estructura de matriz.")
                    flpr_matrices[nombre] = None


            flpr_usuario = flpr_matrices.get("Usuario")
            flpr_agente_qwen = flpr_matrices.get("Qwen")
            flpr_agente_gemini = flpr_matrices.get("Gemini")
            flpr_agente_groq = flpr_matrices.get("Groq")

            flpr_validas_agentes = [f for f in [flpr_agente_qwen, flpr_agente_gemini, flpr_agente_groq] if f is not None]

            if len(flpr_validas_agentes) < 2:
                self.agregar_resultado("ADVERTENCIA: No hay suficientes FLPRs de agentes válidas para calcular FLPR común de agentes.")
                flpr_agentes = None
            elif len(flpr_validas_agentes) == 2:
                flpr_agentes = calcular_flpr_comun(flpr_validas_agentes[0], flpr_validas_agentes[1])
            else:
                flpr_agentes_temp = calcular_flpr_comun(flpr_validas_agentes[0], flpr_validas_agentes[1])
                flpr_agentes = calcular_flpr_comun(flpr_agentes_temp, flpr_validas_agentes[2])


            if flpr_agentes is not None and flpr_usuario is not None:
                flpr_colectiva = calcular_flpr_comun(flpr_agentes, flpr_usuario)
            elif flpr_agentes is not None:
                flpr_colectiva = flpr_agentes
                self.agregar_resultado("ADVERTENCIA: Usando FLPR de agentes como colectiva debido a FLPR de usuario no válida.")
            elif flpr_usuario is not None:
                flpr_colectiva = flpr_usuario
                self.agregar_resultado("ADVERTENCIA: Usando FLPR de usuario como colectiva debido a FLPR de agentes no válida.")
            else:
                self.agregar_resultado("ERROR CRÍTICO: No se pudieron calcular FLPRs válidas. No se puede continuar con el ranking.")
                if hasattr(self, 'evaluate_button') and self.evaluate_button.winfo_exists():
                    self.evaluate_button.config(state=tk.NORMAL)
                return

            matrices_similitud_validas = []
            if flpr_usuario is not None and flpr_agente_qwen is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_usuario, flpr_agente_qwen))
            if flpr_usuario is not None and flpr_agente_gemini is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_usuario, flpr_agente_gemini))
            if flpr_usuario is not None and flpr_agente_groq is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_usuario, flpr_agente_groq))
            if flpr_agente_qwen is not None and flpr_agente_gemini is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_agente_qwen, flpr_agente_gemini))
            if flpr_agente_qwen is not None and flpr_agente_groq is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_agente_qwen, flpr_agente_groq))
            if flpr_agente_gemini is not None and flpr_agente_groq is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_agente_gemini, flpr_agente_groq))

            self.agregar_resultado("\n=== Revisión de Matrices de Agentes ===")
            self.agregar_resultado("Antes de calcular el consenso global, puedes revisar las matrices de los "
                            "agentes para detectar y corregir posibles sesgos.")

            matrices_originales = {
                "Usuario": matriz_usuario,
                "Agente Qwen": matriz_agente_qwen,
                "Agente Gemini": matriz_agente_gemini,
                "Agente Groq": matriz_agente_groq
            }

            matrices_revisadas = self.revisar_matrices_agentes(jugadores, criterios, matrices_originales)

            if matrices_revisadas is not None:
                self.agregar_resultado("Aplicando cambios de la revisión de matrices y recalculando FLPRs...")

                matriz_usuario = matrices_revisadas.get("Usuario", matriz_usuario)
                matriz_agente_qwen = matrices_revisadas.get("Agente Qwen", matriz_agente_qwen)
                matriz_agente_gemini = matrices_revisadas.get("Agente Gemini", matriz_agente_gemini)
                matriz_agente_groq = matrices_revisadas.get("Agente Groq", matriz_agente_groq)

                matrices_actualizadas_para_flpr = {
                    "Usuario": matriz_usuario,
                    "Agente Qwen": matriz_agente_qwen,
                    "Agente Gemini": matriz_agente_gemini,
                    "Agente Groq": matriz_agente_groq
                }

                flpr_matrices = calcular_matrices_flpr(matrices_actualizadas_para_flpr, criterios)

                flpr_usuario = flpr_matrices.get("Usuario")
                flpr_agente_qwen = flpr_matrices.get("Agente Qwen")
                flpr_agente_gemini = flpr_matrices.get("Agente Gemini")
                flpr_agente_groq = flpr_matrices.get("Agente Groq")

                matrices_similitud_validas = []
                if flpr_usuario is not None and flpr_agente_qwen is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_usuario, flpr_agente_qwen))
                if flpr_usuario is not None and flpr_agente_gemini is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_usuario, flpr_agente_gemini))
                if flpr_usuario is not None and flpr_agente_groq is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_usuario, flpr_agente_groq))
                if flpr_agente_qwen is not None and flpr_agente_gemini is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_agente_qwen, flpr_agente_gemini))
                if flpr_agente_qwen is not None and flpr_agente_groq is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_agente_qwen, flpr_agente_groq))
                if flpr_agente_gemini is not None and flpr_agente_groq is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_agente_gemini, flpr_agente_groq))

            if not matrices_similitud_validas:
                self.agregar_resultado("ERROR: No se pudieron calcular matrices de similitud. No se puede determinar el consenso.")
                cr, consenso_alcanzado = 0, False
            else:
                cr, consenso_alcanzado = calcular_cr(matrices_similitud_validas, consenso_minimo)


            self.agregar_resultado(f"\n=== Nivel de Consenso ===")
            self.agregar_resultado(f"Nivel de consenso (CR): {cr:.3f}")
            self.agregar_resultado(f"Consenso mínimo requerido: {consenso_minimo}")

            self.mostrar_distancias_al_consenso(
                flpr_usuario, flpr_agente_qwen, flpr_agente_gemini, flpr_agente_groq, flpr_colectiva
            )

            if consenso_alcanzado:
                self.agregar_resultado("Se ha alcanzado el nivel mínimo de consenso.")
                if flpr_colectiva is not None:
                    self.agregar_resultado("\n=== Ranking de Jugadores ===")
                    ranking = calcular_ranking_jugadores(flpr_colectiva, jugadores)
                    self.agregar_resultado("TOP JUGADORES (de mejor a peor):")
                    for posicion, (jugador, puntuacion) in enumerate(ranking, 1):
                        if puntuacion == 0:
                            puntuacion = "10.000"
                        self.agregar_resultado(f"{posicion}. {jugador} - Puntuación: {puntuacion:.3f}")
                else:
                    self.agregar_resultado("No se puede generar ranking debido a FLPR colectiva no válida.")
            else:
                self.agregar_resultado("No se ha alcanzado el nivel mínimo de consenso.")
                self.agregar_resultado("\n=== Iniciando fase de discusión y re-evaluación ===")

                ronda_actual = 1
                consenso_alcanzado_nuevo = False
                cr_nuevo = cr
                flpr_usuario_actual = flpr_usuario
                flpr_agente_qwen_actual = flpr_agente_qwen
                flpr_agente_gemini_actual = flpr_agente_gemini
                flpr_agente_groq_actual = flpr_agente_groq
                flpr_colectiva_actual = flpr_colectiva
                matriz_usuario_actual = matriz_usuario
                matriz_agente_qwen_actual = matriz_agente_qwen
                matriz_agente_gemini_actual = matriz_agente_gemini
                matriz_agente_groq_actual = matriz_agente_groq

                while ronda_actual <= max_rondas and not consenso_alcanzado_nuevo:
                    self.agregar_resultado(f"\n\n=== RONDA DE DISCUSIÓN {ronda_actual}/{max_rondas} ===")

                    def formatear_calificaciones(jugadores_list, criterios_list, matriz, nombre_agente):
                        calificaciones_str = f"Mis calificaciones como agente {nombre_agente} para los jugadores son:\n"
                        for i, jugador in enumerate(jugadores_list):
                            calificaciones_str += f"{jugador}: "
                            for j, criterio in enumerate(criterios_list):
                                calificaciones_str += f"{criterio}: {matriz[i][j]}, "
                            calificaciones_str = calificaciones_str.rstrip(", ") + "\n"
                        return calificaciones_str

                    calificaciones_qwen_str = formatear_calificaciones(jugadores, criterios, matriz_agente_qwen_actual, f"Qwen (Ronda {ronda_actual})")
                    calificaciones_gemini_str = formatear_calificaciones(jugadores, criterios, matriz_agente_gemini_actual, f"Gemini (Ronda {ronda_actual})")
                    calificaciones_groq_str = formatear_calificaciones(jugadores, criterios, matriz_agente_groq_actual, f"Groq (Ronda {ronda_actual})")

                    calificaciones_usuario_str = f"Las calificaciones del usuario para los jugadores (Ronda {ronda_actual}) son:\n"
                    for i, jugador in enumerate(jugadores):
                        calificaciones_usuario_str += f"{jugador}: "
                        for j, criterio in enumerate(criterios):
                            calificaciones_usuario_str += f"{criterio}: {matriz_usuario_actual[i][j]}, "
                        calificaciones_usuario_str = calificaciones_usuario_str.rstrip(", ") + "\n"

                    self.agregar_resultado("Informando a los agentes sobre las calificaciones actuales...")
                    self.agente_qwen.invoke({"input": f"Estas son las calificaciones que has dado TU a los jugadores:\n{calificaciones_qwen_str}\n"
                        "No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Qwen recordadas'."})
                    self.agente_gemini.invoke({"input": f"Estas son las calificaciones que has dado TU a los jugadores:\n{calificaciones_gemini_str}\n"
                        "No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Gemini recordadas'."})
                    self.agente_groq.invoke({"input": f"Estas son las calificaciones que has dado TU a los jugadores:\n{calificaciones_groq_str}\n"
                        "No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Groq recordadas'."})

                    # Informar a cada agente sobre las calificaciones del usuario
                    self.agente_qwen.invoke({"input": f"Recuerda estas calificaciones que ha dado el usuario: {calificaciones_usuario_str}\n"
                        "No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del usuario recordadas'."})

                    self.agente_gemini.invoke({"input": f"Recuerda estas calificaciones que ha dado el usuario: {calificaciones_usuario_str}\n"
                        "No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del usuario recordadas'."})

                    self.agente_groq.invoke({"input": f"Recuerda estas calificaciones que ha dado el usuario: {calificaciones_usuario_str}\n"
                        "No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del usuario recordadas'."})

                    # Informar a cada agente sobre las calificaciones de los otros agentes
                    self.agente_qwen.invoke({"input": f"El agente Gemini ha dado estas calificaciones: {calificaciones_gemini_str}\n "
                                            f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Gemini recordadas'."})

                    self.agente_qwen.invoke({"input": f"El agente Groq ha dado estas calificaciones: {calificaciones_groq_str}\n "
                                            f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Groq recordadas'."})

                    self.agente_gemini.invoke({"input": f"El agente Qwen ha dado estas calificaciones: {calificaciones_qwen_str}\n "
                                            f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Qwen recordadas'."})

                    self.agente_gemini.invoke({"input": f"El agente Groq ha dado estas calificaciones: {calificaciones_groq_str}\n "
                                            f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Groq recordadas'."})

                    self.agente_groq.invoke({"input": f"El agente Qwen ha dado estas calificaciones: {calificaciones_qwen_str}\n "
                                            f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Qwen recordadas'."})

                    self.agente_groq.invoke({"input": f"El agente Gemini ha dado estas calificaciones: {calificaciones_gemini_str}\n "
                                            f"No uses ninguna tool ni evalues a los jugadores, solo responde: 'Calificaciones del agente Gemini recordadas'."})

                    self.agregar_resultado(f"\n=== Discusión sobre las valoraciones (Ronda {ronda_actual}/{max_rondas}) ===")
                    self.agregar_resultado("Ahora puedes discutir con los agentes sobre las valoraciones realizadas.")

                    discusion_window = tk.Toplevel(self.master)
                    discusion_window.configure(background=self.colores["bg_dark_widget"])
                    discusion_window.title(f"Discusión sobre valoraciones - Ronda {ronda_actual}/{max_rondas}")
                    discusion_window.geometry("800x600")
                    discusion_window.transient(self.master)
                    discusion_window.grab_set()

                    main_frame = ttk.Frame(discusion_window, padding=10)
                    main_frame.pack(fill=tk.BOTH, expand=True)

                    ttk.Label(main_frame, text=f"Discusión sobre valoraciones (Ronda {ronda_actual}/{max_rondas}):",
                             font=("Arial", 11, "bold")).pack(pady=(0, 15))

                    selection_frame = ttk.Frame(main_frame)
                    selection_frame.pack(fill=tk.X, pady=(0, 10))

                    ttk.Label(selection_frame, text="Selecciona un agente:").pack(side=tk.LEFT, padx=(0, 10))

                    selected_agent = StringVar(value="Qwen")

                    agent_selector = ttk.Combobox(selection_frame, textvariable=selected_agent,
                                                 values=["Qwen", "Gemini", "Groq"], state="readonly", width=15)
                    agent_selector.pack(side=tk.LEFT)

                    conversation_frame = ttk.Frame(main_frame)
                    conversation_frame.pack(fill=tk.BOTH, expand=True, pady=10)

                    conversation_text = tk.Text(conversation_frame, wrap=tk.WORD, width=80, height=15,
                                              bg=self.colores["bg_dark_widget"], fg=self.colores["fg_light"])
                    conversation_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

                    scrollbar = ttk.Scrollbar(conversation_frame, command=conversation_text.yview)
                    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                    conversation_text.config(yscrollcommand=scrollbar.set)

                    input_frame = ttk.Frame(main_frame)
                    input_frame.pack(fill=tk.X, pady=(10, 0))

                    user_input = tk.Text(input_frame, wrap=tk.WORD, width=80, height=3,
                                       bg=self.colores["bg_dark_entry"], fg=self.colores["fg_light"])
                    user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

                    conversation_history = []

                    def send_message():
                        agent_name = selected_agent.get()
                        message = user_input.get("1.0", tk.END).strip()

                        if not message:
                            return

                        conversation_text.config(state=tk.NORMAL)
                        conversation_text.insert(tk.END, f"\nTú: {message}\n")
                        conversation_history.append(("user", message))

                        user_input.delete("1.0", tk.END)

                        prompt_discusion = f"""
                            Basándote en las calificaciones y la discusión anterior, por favor, responde a la siguiente pregunta: {message}
                            No uses ninguna tool si no se pide explicitamente, solo responde esta pregunta.
                            Tu objetivo es evaluar críticamente las afirmaciones del usuario.
                            Si el usuario dice algo incorrecto o sin sentido, discútelo y explica por qué no estás de acuerdo.
                            Proporciona argumentos claros y basados en datos o lógica. No aceptes afirmaciones sin fundamento.
                            Si recibes una orden, explica tu punta de vista pero debes respetar la orden.
                        """

                        conversation_text.insert(tk.END, f"\n{agent_name} está respondiendo...\n")
                        conversation_text.see(tk.END)
                        conversation_text.config(state=tk.DISABLED)

                        discusion_window.update()

                        if agent_name == "Qwen":
                            respuesta = self.agente_qwen.invoke({"input": prompt_discusion})
                            agent_response = respuesta.get("output", "No hay respuesta")
                            agent_response = re.sub(r"<think>.*?</think>", "", agent_response,
                                                    flags=re.DOTALL)
                        elif agent_name == "Gemini":
                            respuesta = self.agente_gemini.invoke({"input": prompt_discusion})
                            agent_response = respuesta.get("output", "No hay respuesta")
                        else:  # Groq
                            respuesta = self.agente_groq.invoke({"input": prompt_discusion})
                            agent_response = respuesta.get("output", "No hay respuesta")

                        conversation_text.config(state=tk.NORMAL)
                        conversation_text.delete("end-2l", tk.END)
                        conversation_text.insert(tk.END, f"\n{agent_name}: {agent_response}\n")
                        conversation_text.see(tk.END)
                        conversation_text.config(state=tk.DISABLED)

                        conversation_history.append((agent_name, agent_response))

                    send_button = ttk.Button(input_frame, text="Enviar", command=send_message)
                    send_button.pack(side=tk.RIGHT)

                    user_input.bind("<Return>", lambda e: send_message() or "break")

                    button_frame = ttk.Frame(main_frame)
                    button_frame.pack(fill=tk.X, pady=(15, 0))

                    continue_reevaluation = [True]

                    def on_cancel():
                        continue_reevaluation[0] = False
                        discusion_window.destroy()

                    def on_continue():
                        discusion_window.destroy()

                    cancel_button = ttk.Button(button_frame, text="Cancelar discusión y finalizar", command=on_cancel)
                    cancel_button.pack(side=tk.LEFT, padx=5, expand=True)

                    continue_button = ttk.Button(button_frame, text="Finalizar discusión y continuar", command=on_continue)
                    continue_button.pack(side=tk.RIGHT, padx=5, expand=True)

                    conversation_text.config(state=tk.NORMAL)
                    conversation_text.insert(tk.END, "Bienvenido a la discusión sobre valoraciones. Selecciona un agente y haz preguntas sobre las valoraciones.\n")
                    conversation_text.config(state=tk.DISABLED)

                    self.master.wait_window(discusion_window)

                    if not continue_reevaluation[0]:
                        self.agregar_resultado("\nDiscusión cancelada. Finalizando evaluación.")
                        break

                    self.agregar_resultado(f"\n=== Re-evaluación de jugadores (Ronda {ronda_actual}/{max_rondas}) ===")
                    self.agregar_resultado("Los agentes volverán a evaluar a los jugadores basándose en la discusión anterior.")

                    prompt_reevaluacion_qwen = f"""
                    Basándote en nuestra discusión anterior sobre las valoraciones de los jugadores, 
                    por favor, vuelve a evaluar a los siguientes jugadores: {', '.join(jugadores)} 
                    según los criterios: {', '.join(criterios)}.

                    Proporciona tu nueva evaluación en el mismo formato CSV que usaste anteriormente.
                    """

                    prompt_reevaluacion_gemini = f"""
                    Basándote en nuestra discusión anterior sobre las valoraciones de los jugadores, 
                    por favor, vuelve a evaluar a los siguientes jugadores: {', '.join(jugadores)} 
                    según los criterios: {', '.join(criterios)}.

                    Recuerda que anteriormente tú diste estas calificaciones como agente Gemini:
                    {calificaciones_gemini_str}

                    El agente Qwen dio estas calificaciones:
                    {calificaciones_qwen_str}

                    El agente Groq dio estas calificaciones:
                    {calificaciones_groq_str}

                    Y el usuario dio estas calificaciones:
                    {calificaciones_usuario_str}

                    Proporciona tu nueva evaluación en el mismo formato CSV que usaste anteriormente.
                    """

                    prompt_reevaluacion_groq = f"""
                    Basándote en nuestra discusión anterior sobre las valoraciones de los jugadores, 
                    por favor, vuelve a evaluar a los siguientes jugadores: {', '.join(jugadores)} 
                    según los criterios: {', '.join(criterios)}.

                    Recuerda que anteriormente tú diste estas calificaciones como agente Groq:
                    {calificaciones_groq_str}

                    El agente Qwen dio estas calificaciones:
                    {calificaciones_qwen_str}

                    El agente Gemini dio estas calificaciones:
                    {calificaciones_gemini_str}

                    Y el usuario dio estas calificaciones:
                    {calificaciones_usuario_str}

                    Proporciona tu nueva evaluación en el mismo formato CSV que usaste anteriormente.
                    """

                    max_intentos_reevaluacion = 3

                    self.agregar_resultado(f"\n=== Re-evaluación con el Agente Qwen (Ronda {ronda_actual}/{max_rondas}) ===")
                    matriz_agente_qwen_nueva, output_reevaluacion_qwen = evaluar_con_agente(
                        self.agente_qwen, prompt_reevaluacion_qwen, jugadores, criterios, self.valores_linguisticos, "Qwen", max_intentos_reevaluacion)

                    self.agregar_resultado("\n=== Nueva evaluación del agente Qwen ===")
                    self.agregar_resultado(output_reevaluacion_qwen)

                    self.agregar_resultado(f"\n=== Re-evaluación con el Agente Gemini (Ronda {ronda_actual}/{max_rondas}) ===")
                    matriz_agente_gemini_nueva, output_reevaluacion_gemini = evaluar_con_agente(
                        self.agente_gemini, prompt_reevaluacion_gemini, jugadores, criterios, self.valores_linguisticos, "Gemini", max_intentos_reevaluacion)

                    self.agregar_resultado("\n=== Nueva evaluación del agente Gemini ===")
                    self.agregar_resultado(output_reevaluacion_gemini)

                    self.agregar_resultado(f"\n=== Re-evaluación con el Agente Groq (Ronda {ronda_actual}/{max_rondas}) ===")
                    matriz_agente_groq_nueva, output_reevaluacion_groq = evaluar_con_agente(
                        self.agente_groq, prompt_reevaluacion_groq, jugadores, criterios, self.valores_linguisticos, "Groq", max_intentos_reevaluacion)

                    self.agregar_resultado("\n=== Nueva evaluación del agente Groq ===")
                    self.agregar_resultado(output_reevaluacion_groq)

                    self.agregar_resultado(f"\n=== Re-evaluación del usuario (Ronda {ronda_actual}/{max_rondas}) ===")
                    self.agregar_resultado("Ahora es tu turno de volver a evaluar a los jugadores después de la discusión.")

                    matriz_usuario_nueva = self.get_user_evaluacion(jugadores, criterios)
                    if matriz_usuario_nueva is None:
                        self.agregar_resultado("Re-evaluación del usuario cancelada. Finalizando evaluación.")
                        break

                    matrices_nuevas = {
                        "Usuario": matriz_usuario_nueva,
                        "Agente Qwen": matriz_agente_qwen_nueva,
                        "Agente Gemini": matriz_agente_gemini_nueva,
                        "Agente Groq": matriz_agente_groq_nueva
                    }

                    flpr_matrices_nuevas = calcular_matrices_flpr(matrices_nuevas, criterios)

                    flpr_usuario_nueva = flpr_matrices_nuevas["Usuario"]
                    flpr_agente_qwen_nueva = flpr_matrices_nuevas["Agente Qwen"]
                    flpr_agente_gemini_nueva = flpr_matrices_nuevas["Agente Gemini"]
                    flpr_agente_groq_nueva = flpr_matrices_nuevas["Agente Groq"]

                    flpr_agentes_qwen_gemini_nueva = calcular_flpr_comun(flpr_agente_qwen_nueva, flpr_agente_gemini_nueva)
                    flpr_agentes_nueva = calcular_flpr_comun(flpr_agentes_qwen_gemini_nueva, flpr_agente_groq_nueva)

                    flpr_colectiva_nueva = calcular_flpr_comun(flpr_agentes_nueva, flpr_usuario_nueva)

                    matrices_similitud_nuevas = []
                    if flpr_usuario_nueva is not None and flpr_agente_qwen_nueva is not None: matrices_similitud_nuevas.append(calcular_matriz_similitud(flpr_usuario_nueva, flpr_agente_qwen_nueva))
                    if flpr_usuario_nueva is not None and flpr_agente_gemini_nueva is not None: matrices_similitud_nuevas.append(calcular_matriz_similitud(flpr_usuario_nueva, flpr_agente_gemini_nueva))
                    if flpr_usuario_nueva is not None and flpr_agente_groq_nueva is not None: matrices_similitud_nuevas.append(calcular_matriz_similitud(flpr_usuario_nueva, flpr_agente_groq_nueva))
                    if flpr_agente_qwen_nueva is not None and flpr_agente_gemini_nueva is not None: matrices_similitud_nuevas.append(calcular_matriz_similitud(flpr_agente_qwen_nueva, flpr_agente_gemini_nueva))
                    if flpr_agente_qwen_nueva is not None and flpr_agente_groq_nueva is not None: matrices_similitud_nuevas.append(calcular_matriz_similitud(flpr_agente_qwen_nueva, flpr_agente_groq_nueva))
                    if flpr_agente_gemini_nueva is not None and flpr_agente_groq_nueva is not None: matrices_similitud_nuevas.append(calcular_matriz_similitud(flpr_agente_gemini_nueva, flpr_agente_groq_nueva))

                    if not matrices_similitud_nuevas:
                        self.agregar_resultado("ERROR: No se pudieron calcular matrices de similitud nuevas. No se puede determinar el consenso.")
                        cr_nuevo, consenso_alcanzado_nuevo = 0, False
                    else:
                        cr_nuevo, consenso_alcanzado_nuevo = calcular_cr(matrices_similitud_nuevas, consenso_minimo)

                    self.agregar_resultado(f"\n=== Nivel de Consenso (Después de la ronda {ronda_actual} de discusión) ===")
                    self.agregar_resultado(f"Nivel de consenso (CR): {cr_nuevo:.3f}")
                    self.agregar_resultado(f"Consenso mínimo requerido: {consenso_minimo}")

                    self.mostrar_distancias_al_consenso(
                        flpr_usuario, flpr_agente_qwen, flpr_agente_gemini, flpr_agente_groq,
                        flpr_colectiva
                    )

                    if consenso_alcanzado_nuevo:
                        self.agregar_resultado("Se ha alcanzado el nivel mínimo de consenso.")
                    else:
                        self.agregar_resultado("No se ha alcanzado el nivel mínimo de consenso.")

                    if cr_nuevo > cr:
                        self.agregar_resultado(f"\nEl nivel de consenso ha mejorado después de la discusión: {cr:.3f} → {cr_nuevo:.3f}")
                        cr = cr_nuevo
                    elif cr_nuevo < cr:
                        self.agregar_resultado(f"\nEl nivel de consenso ha disminuido después de la discusión: {cr:.3f} → {cr_nuevo:.3f}")
                        cr = cr_nuevo
                    else:
                        self.agregar_resultado(f"\nEl nivel de consenso se ha mantenido igual después de la discusión: {cr:.3f}")

                    flpr_usuario_actual = flpr_usuario_nueva
                    flpr_agente_qwen_actual = flpr_agente_qwen_nueva
                    flpr_agente_gemini_actual = flpr_agente_gemini_nueva
                    flpr_agente_groq_actual = flpr_agente_groq_nueva
                    flpr_colectiva_actual = flpr_colectiva_nueva
                    matriz_usuario_actual = matriz_usuario_nueva
                    matriz_agente_qwen_actual = matriz_agente_qwen_nueva
                    matriz_agente_gemini_actual = matriz_agente_gemini_nueva
                    matriz_agente_groq_actual = matriz_agente_groq_nueva

                    self.mostrar_distancias_al_consenso(
                        flpr_usuario_actual,
                        flpr_agente_qwen_actual,
                        flpr_agente_gemini_actual,
                        flpr_agente_groq_actual,
                        flpr_colectiva_actual
                    )

                    ronda_actual += 1

                    if consenso_alcanzado_nuevo or ronda_actual > max_rondas:
                        self.agregar_resultado("\n=== Ranking de Jugadores (Después de la discusión) ===")
                        ranking = calcular_ranking_jugadores(flpr_colectiva_nueva, jugadores)

                        self.agregar_resultado("TOP JUGADORES (de mejor a peor):")
                        for posicion, (jugador, puntuacion) in enumerate(ranking, 1):
                            self.agregar_resultado(f"{posicion}. {jugador} - Puntuación: {puntuacion:.3f}")

                        if not consenso_alcanzado_nuevo and ronda_actual > max_rondas:
                            self.agregar_resultado(f"\nSe ha alcanzado el número máximo de rondas de discusión ({max_rondas}) sin llegar al consenso mínimo requerido.")
                            self.agregar_resultado(f"Nivel de consenso actual: {cr_nuevo:.3f}")

                            self.agregar_resultado("\n=== Última oportunidad para corregir sesgos ===")
                            self.agregar_resultado("Puedes revisar y modificar las matrices de términos lingüísticos una última vez antes de calcular el ranking final.")

                            matrices_finales = {
                                "Usuario": matriz_usuario_actual,
                                "Agente Qwen": matriz_agente_qwen_actual,
                                "Agente Gemini": matriz_agente_gemini_actual,
                                "Agente Groq": matriz_agente_groq_actual
                            }

                            matrices_revisadas_final = self.revisar_matrices_agentes(jugadores, criterios, matrices_finales)

                            if matrices_revisadas_final is not None:
                                flpr_matrices_final = calcular_matrices_flpr(matrices_revisadas_final, criterios)

                                flpr_usuario_final = flpr_matrices_final["Usuario"]
                                flpr_agente_qwen_final = flpr_matrices_final["Agente Qwen"]
                                flpr_agente_gemini_final = flpr_matrices_final["Agente Gemini"]
                                flpr_agente_groq_final = flpr_matrices_final["Agente Groq"]

                                flpr_agentes_qwen_gemini_final = calcular_flpr_comun(flpr_agente_qwen_final, flpr_agente_gemini_final)
                                flpr_agentes_final = calcular_flpr_comun(flpr_agentes_qwen_gemini_final, flpr_agente_groq_final)
                                flpr_colectiva_final = calcular_flpr_comun(flpr_agentes_final, flpr_usuario_final)

                                matrices_similitud_final = []
                                if flpr_usuario_final is not None and flpr_agente_qwen_final is not None: matrices_similitud_final.append(calcular_matriz_similitud(flpr_usuario_final, flpr_agente_qwen_final))
                                if flpr_usuario_final is not None and flpr_agente_gemini_final is not None: matrices_similitud_final.append(calcular_matriz_similitud(flpr_usuario_final, flpr_agente_gemini_final))
                                if flpr_usuario_final is not None and flpr_agente_groq_final is not None: matrices_similitud_final.append(calcular_matriz_similitud(flpr_usuario_final, flpr_agente_groq_final))
                                if flpr_agente_qwen_final is not None and flpr_agente_gemini_final is not None: matrices_similitud_final.append(calcular_matriz_similitud(flpr_agente_qwen_final, flpr_agente_gemini_final))
                                if flpr_agente_qwen_final is not None and flpr_agente_groq_final is not None: matrices_similitud_final.append(calcular_matriz_similitud(flpr_agente_qwen_final, flpr_agente_groq_final))
                                if flpr_agente_gemini_final is not None and flpr_agente_groq_final is not None: matrices_similitud_final.append(calcular_matriz_similitud(flpr_agente_gemini_final, flpr_agente_groq_final))

                                if not matrices_similitud_final:
                                    self.agregar_resultado("ERROR: No se pudieron calcular matrices de similitud finales. No se puede determinar el consenso.")
                                    cr_final, consenso_alcanzado_final = 0, False
                                else:
                                    cr_final, consenso_alcanzado_final = calcular_cr(matrices_similitud_final, consenso_minimo)

                                self.agregar_resultado(f"\n=== Nivel de Consenso (Después de modificaciones finales) ===")
                                self.agregar_resultado(f"Nivel de consenso (CR): {cr_final:.3f}")
                                self.agregar_resultado(f"Consenso mínimo requerido: {consenso_minimo}")

                                if consenso_alcanzado_final:
                                    self.agregar_resultado("Se ha alcanzado el nivel mínimo de consenso.")
                                else:
                                    self.agregar_resultado("No se ha alcanzado el nivel mínimo de consenso.")

                                self.agregar_resultado("\n=== Ranking de Jugadores (Actualizado) ===")
                                ranking_final = calcular_ranking_jugadores(flpr_colectiva_final, jugadores)

                                self.agregar_resultado("TOP JUGADORES (de mejor a peor):")
                                for posicion, (jugador, puntuacion) in enumerate(ranking_final, 1):
                                    self.agregar_resultado(f"{posicion}. {jugador} - Puntuación: {puntuacion:.3f}")

                                self.agregar_resultado(f"\nSe muestra el ranking con el nivel de consenso actual: {cr_final:.3f}")
                            else:
                                self.agregar_resultado(f"\nSe muestra el ranking con el nivel de consenso actual: {cr_nuevo:.3f}")

                if consenso_alcanzado:
                    self.agregar_resultado("\nSe ha alcanzado el nivel mínimo de consenso. No es necesario realizar la discusión y re-evaluación.")


            self.agregar_resultado("\nEvaluación completada.")

            self.resultados_evaluacion = {
                "matrices": matrices_revisadas_final if 'matrices_revisadas_final' in locals() and matrices_revisadas_final is not None
                else matrices_nuevas if 'matrices_nuevas' in locals() and matrices_nuevas is not None
                else matrices,
                "discusiones": conversation_history if 'conversation_history' in locals() else None,
                "crs": cr_final if 'cr_final' in locals() else cr_nuevo if 'cr_nuevo' in locals() else cr,
                "ranking": ranking_final if 'ranking_final' in locals() else ranking if 'ranking' in locals() else [],
            }

            self.boton_exportar_pdf.config(state=tk.NORMAL)

        except Exception as e:
            self.agregar_resultado(f"Error durante la evaluación: {str(e)}")
            import traceback
            self.agregar_resultado(f"Traceback: {traceback.format_exc()}")
        finally:
            if hasattr(self, 'evaluate_button') and self.evaluate_button.winfo_exists():
                 self.evaluate_button.config(state=tk.NORMAL)


    def get_user_evaluacion(self, jugadores, criterios):
        """
        Muestra una ventana emergente para que el usuario evalúe a los jugadores.
        Retorna la matriz de evaluación del usuario.
        """
        eval_window = tk.Toplevel(self.master)
        eval_window.configure(background=self.colores["bg_dark_widget"])
        eval_window.title("Evaluación de Jugadores")
        eval_window.geometry("700x450") # Tamaño ajustado
        eval_window.transient(self.master) # O self
        eval_window.grab_set()

        user_matrix_vars = []
        for _ in jugadores:
            user_matrix_vars.append([StringVar(value="Medio") for _ in criterios])

        main_frame_eval = ttk.Frame(eval_window, padding=10)
        main_frame_eval.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame_eval, text="Evalúa a cada jugador según los criterios:", font=("Arial", 11, "bold")).pack(pady=(0, 15))

        table_frame = ttk.Frame(main_frame_eval)
        table_frame.pack(fill=tk.BOTH, expand=True)

        header_font = ("Arial", 10, "bold")
        ttk.Label(table_frame, text="Jugador", font=header_font).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        for i, criterio_item in enumerate(criterios):
            ttk.Label(table_frame, text=criterio_item, font=header_font).grid(row=0, column=i+1, padx=5, pady=5, sticky=tk.W)

        for i, jugador in enumerate(jugadores):
            ttk.Label(table_frame, text=jugador, font=("Arial", 10)).grid(row=i+1, column=0, padx=5, pady=5, sticky=tk.W)

            for j in range(len(criterios)):
                combo = ttk.Combobox(table_frame, textvariable=user_matrix_vars[i][j],
                                    values=self.valores_linguisticos, state="readonly", width=12, font=("Arial", 9))
                combo.grid(row=i+1, column=j+1, padx=5, pady=5, sticky=tk.EW)
                combo.current(2)

        table_frame.grid_columnconfigure(0, weight=1)
        for j in range(len(criterios)):
            table_frame.grid_columnconfigure(j+1, weight=1)

        button_frame = ttk.Frame(main_frame_eval)
        button_frame.pack(fill=tk.X, pady=(15,0))

        result_matrix = [None]

        def on_cancel():
            result_matrix[0] = None
            eval_window.destroy()

        def on_submit():
            matrix_eval = []
            for i in range(len(jugadores)):
                row = [user_matrix_vars[i][j].get() for j in range(len(criterios))]
                matrix_eval.append(row)

            result_matrix[0] = matrix_eval
            eval_window.destroy()

        cancel_button = ttk.Button(button_frame, text="Cancelar", command=on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=5, expand=True)

        submit_button = ttk.Button(button_frame, text="Enviar Evaluación", command=on_submit)
        submit_button.pack(side=tk.RIGHT, padx=5, expand=True)

        self.master.wait_window(eval_window)

        return result_matrix[0]

    def revisar_matrices_agentes(self, jugadores, criterios, matrices):
        """
        Muestra una ventana emergente para que el usuario revise y modifique las matrices de los agentes.
        Permite detectar y corregir sesgos antes de calcular el consenso.

        Args:
            jugadores (list): Lista de jugadores
            criterios (list): Lista de criterios
            matrices (dict): Diccionario con las matrices de los agentes

        Returns:
            dict: Diccionario con las matrices modificadas
        """
        self.agregar_resultado("\n=== Revisión de Matrices de Agentes ===")
        self.agregar_resultado("Puedes revisar las matrices de términos lingüísticos para identificar posibles sesgos.")

        review_window = tk.Toplevel(self.master)
        review_window.configure(background=self.colores["bg_dark_widget"])
        review_window.title("Revisión de Matrices de Agentes")
        review_window.geometry("800x600")
        review_window.transient(self.master)
        review_window.grab_set()

        main_frame = ttk.Frame(review_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Revisa las matrices de los agentes y modifica valores si detectas sesgos:",
                 font=("Arial", 11, "bold")).pack(pady=(0, 15))

        selection_frame = ttk.Frame(main_frame)
        selection_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(selection_frame, text="Selecciona una matriz:").pack(side=tk.LEFT, padx=(0, 10))

        selected_matrix = StringVar(value=list(matrices.keys())[0])

        matrix_selector = ttk.Combobox(selection_frame, textvariable=selected_matrix,
                                      values=list(matrices.keys()), state="readonly", width=15)
        matrix_selector.pack(side=tk.LEFT)

        table_container = ttk.Frame(main_frame)
        table_container.pack(fill=tk.BOTH, expand=True, pady=10)

        scrollbar_y = ttk.Scrollbar(table_container)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        scrollbar_x = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        canvas = tk.Canvas(table_container, yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set,
                          background=self.colores["bg_dark_widget"])
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar_y.config(command=canvas.yview)
        scrollbar_x.config(command=canvas.xview)

        table_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=table_frame, anchor=tk.NW)

        matrix_vars = {}

        def mostrar_matriz_seleccionada():
            for widget in table_frame.winfo_children():
                widget.destroy()

            matrix_name = selected_matrix.get()
            matrix = matrices[matrix_name]

            if matrix_name not in matrix_vars:
                matrix_vars[matrix_name] = []
                for i in range(len(jugadores)):
                    row_vars = []
                    for j in range(len(criterios)):
                        row_vars.append(StringVar(value=matrix[i][j]))
                    matrix_vars[matrix_name].append(row_vars)

            header_font = ("Arial", 10, "bold")
            ttk.Label(table_frame, text="Jugador", font=header_font).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            for j, criterio in enumerate(criterios):
                ttk.Label(table_frame, text=criterio, font=header_font).grid(row=0, column=j+1, padx=5, pady=5, sticky=tk.W)

            for i, jugador in enumerate(jugadores):
                ttk.Label(table_frame, text=jugador, font=("Arial", 10)).grid(row=i+1, column=0, padx=5, pady=5, sticky=tk.W)

                for j in range(len(criterios)):
                    combo = ttk.Combobox(table_frame, textvariable=matrix_vars[matrix_name][i][j],
                                        values=self.valores_linguisticos, state="readonly", width=12, font=("Arial", 9))
                    combo.grid(row=i+1, column=j+1, padx=5, pady=5, sticky=tk.EW)

                    current_value = matrix_vars[matrix_name][i][j].get()
                    if current_value in self.valores_linguisticos:
                        combo.current(self.valores_linguisticos.index(current_value))

            table_frame.grid_columnconfigure(0, weight=1)
            for j in range(len(criterios)):
                table_frame.grid_columnconfigure(j+1, weight=1)

            table_frame.update_idletasks()
            canvas.config(scrollregion=canvas.bbox("all"))

        matrix_selector.bind("<<ComboboxSelected>>", lambda e: mostrar_matriz_seleccionada())

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))

        result_matrices = [None]

        def al_cancelar():
            result_matrices[0] = None
            review_window.destroy()

        def al_enviar():
            modified_matrices = {}
            for matrix_name, vars_matrix in matrix_vars.items():
                modified_matrix = []
                for i in range(len(jugadores)):
                    row = [vars_matrix[i][j].get() for j in range(len(criterios))]
                    modified_matrix.append(row)
                modified_matrices[matrix_name] = modified_matrix

            result_matrices[0] = modified_matrices
            review_window.destroy()

        cancel_button = ttk.Button(button_frame, text="Cancelar", command=al_cancelar)
        cancel_button.pack(side=tk.LEFT, padx=5, expand=True)

        submit_button = ttk.Button(button_frame, text="Guardar Cambios", command=al_enviar)
        submit_button.pack(side=tk.RIGHT, padx=5, expand=True)

        mostrar_matriz_seleccionada()

        self.master.wait_window(review_window)

        if result_matrices[0] is not None:
            self.agregar_resultado("Matrices revisadas y modificadas correctamente.")
            return result_matrices[0]
        else:
            self.agregar_resultado("Revisión de matrices cancelada.")
            return matrices


class PestañaBaseDeDatos(ttk.Frame):
    def __init__(self, padre, colores):
        super().__init__(padre)
        self.colores = colores
        self.posiciones = {
            "GK": "Portero",
            "Defender": "Defensa",
            "Defensive-Midfielders": "Mediocentro defensivo",
            "Central Midfielders": "Mediocentro",
            "Attacking Midfielders": "Mediapunta",
            "Wing-Back": "Carrilero",
            "Forwards": "Delantero"
        }

        self.temporadas = ["2022-2023", "2023-2024", "2024-2025"]
        self.temporada_seleccionada = StringVar(value=self.temporadas[-1])
        self.ventana_tooltip = None
        self.jugadores_comparar = []
        self.info_jugador_actual = None
        self.cargar_datos_jugadores()
        self.crear_widgets()

    def cargar_datos_jugadores(self):
        try:
            temporada = self.temporada_seleccionada.get()
            self.df_jugadores = cargar_estadisticas_jugadores(temporada)
            if isinstance(self.df_jugadores, str):
                messagebox.showerror("Error", f"Error al cargar datos de jugadores: {self.df_jugadores}")
                self.df_jugadores = None
            elif self.df_jugadores is not None and 'Player' in self.df_jugadores.columns:
                self.df_jugadores['nombre_normalizado'] = self.df_jugadores['Player'].fillna('').astype(str).str.lower()
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar datos de jugadores: {str(e)}")
            self.df_jugadores = None

    def crear_widgets(self):
        marco_principal = ttk.Frame(self)
        marco_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        marco_izquierdo = ttk.Frame(marco_principal)
        marco_izquierdo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10))

        marco_derecho = ttk.Frame(marco_principal)
        marco_derecho.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10,0))

        marco_seleccion = ttk.Frame(marco_izquierdo)
        marco_seleccion.pack(fill=tk.X, padx=5, pady=5)

        marco_posicion = ttk.Frame(marco_seleccion)
        marco_posicion.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))

        ttk.Label(marco_posicion, text="Posición:").pack(side=tk.LEFT, padx=(0,5))
        self.var_posicion = StringVar()
        self.combo_posicion = ttk.Combobox(marco_posicion, textvariable=self.var_posicion,
                                          values=list(self.posiciones.values()), state="readonly", width=20)
        self.combo_posicion.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.combo_posicion.bind("<<ComboboxSelected>>", self.al_seleccionar_posicion)

        marco_temporada = ttk.Frame(marco_seleccion)
        marco_temporada.pack(side=tk.RIGHT, fill=tk.X, padx=(5,0))
        ttk.Label(marco_temporada, text="Temporada:").pack(side=tk.LEFT, padx=(0,5))

        self.combo_temporada = ttk.Combobox(marco_temporada, textvariable=self.temporada_seleccionada,
                                        values=self.temporadas, state="readonly", width=8)
        self.combo_temporada.pack(side=tk.LEFT, padx=5)
        self.combo_temporada.bind("<<ComboboxSelected>>", self.al_seleccionar_temporada)

        marco_busqueda = ttk.LabelFrame(marco_izquierdo, text="Buscar un Jugador")
        marco_busqueda.pack(fill=tk.X, padx=5, pady=10, ipady=5)

        self.var_busqueda = StringVar()
        self.entrada_busqueda = ttk.Entry(marco_busqueda, textvariable=self.var_busqueda)
        self.entrada_busqueda.pack(fill=tk.X, padx=10, pady=10)
        self.entrada_busqueda.bind("<KeyRelease>", self.al_escribir_busqueda)

        self.marco_lista_jugadores = ttk.LabelFrame(marco_izquierdo, text="Jugadores")
        self.marco_lista_jugadores.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, ipady=5)
        marco_lista = ttk.Frame(self.marco_lista_jugadores)
        marco_lista.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.lista_jugadores = tk.Listbox(marco_lista,
                                         bg=self.colores["bg_dark_entry"], fg=self.colores["fg_light"],
                                         selectbackground=self.colores["accent_color"],
                                         selectforeground=self.colores["fg_white"],
                                         borderwidth=0, highlightthickness=0, font=("Arial",10))

        self.lista_jugadores.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra_lista = ttk.Scrollbar(marco_lista, command=self.lista_jugadores.yview)
        barra_lista.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista_jugadores.config(yscrollcommand=barra_lista.set)
        self.lista_jugadores.bind("<<ListboxSelect>>", self.al_seleccionar_jugador)

        self.marco_comparar = ttk.LabelFrame(marco_izquierdo, text="Comparar Jugadores")
        self.marco_comparar.pack(fill=tk.X, padx=5, pady=10, ipady=5)

        self.lista_comparar = tk.Listbox(self.marco_comparar, height=3,
                                          bg=self.colores["bg_dark_entry"], fg=self.colores["fg_light"],
                                          selectbackground=self.colores["accent_color"],
                                          selectforeground=self.colores["fg_white"],
                                          borderwidth=0, highlightthickness=0, font=("Arial",10))
        self.lista_comparar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=10)

        marco_botones_comparar = ttk.Frame(self.marco_comparar)
        marco_botones_comparar.pack(side=tk.RIGHT, padx=10, pady=10)

        self.boton_añadir_comparar = ttk.Button(marco_botones_comparar, text="Añadir",
                                         command=self.añadir_jugador_comparar)
        self.boton_añadir_comparar.pack(fill=tk.X, pady=2)

        self.boton_quitar_comparar = ttk.Button(marco_botones_comparar, text="Quitar",
                                           command=self.quitar_jugador_comparar)
        self.boton_quitar_comparar.pack(fill=tk.X, pady=2)

        self.marco_detalles = ttk.LabelFrame(marco_derecho, text="Estadísticas del Jugador")
        self.marco_detalles.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, ipady=5, ipadx=5)

        self.texto_detalles = tk.Text(self.marco_detalles, wrap=tk.WORD, state=tk.DISABLED,
                                   bg=self.colores["bg_dark_entry"], fg=self.colores["fg_light"],
                                   insertbackground=self.colores["fg_white"],
                                   borderwidth=0, highlightthickness=0, font=("Arial", 10), relief=tk.FLAT, padx=5, pady=5)
        self.texto_detalles.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)
        barra_detalles = ttk.Scrollbar(self.marco_detalles, command=self.texto_detalles.yview)
        barra_detalles.pack(side=tk.RIGHT, fill=tk.Y)
        self.texto_detalles.config(yscrollcommand=barra_detalles.set)

        self.marco_grafico = ttk.LabelFrame(marco_derecho, text="Gráfico de  Araña")
        self.marco_grafico.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, ipady=5, ipadx=5)
        self.etiqueta_grafico = ttk.Label(self.marco_grafico, text="Seleccione al menos un jugador para ver en el gráfico", anchor="center")
        self.etiqueta_grafico.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def al_seleccionar_posicion(self, evento):
        nombre_posicion = self.var_posicion.get()
        clave_posicion = None

        for clave, valor in self.posiciones.items():
            if valor == nombre_posicion:
                clave_posicion = clave
                break

        if clave_posicion:
            self.actualizar_lista_jugadores(clave_posicion)

    def añadir_jugador_comparar(self):
        seleccion = self.lista_jugadores.curselection()

        if not seleccion:
            return

        nombre_jugador = self.lista_jugadores.get(seleccion[0])

        if nombre_jugador not in [self.lista_comparar.get(i) for i in range(self.lista_comparar.size())]:
            if self.lista_comparar.size() < 3:
                self.lista_comparar.insert(tk.END, nombre_jugador)
                if self.df_jugadores is not None:
                    datos_jugador = self.df_jugadores[self.df_jugadores['Player'] == nombre_jugador]
                    if not datos_jugador.empty:
                        self.jugadores_comparar.append(datos_jugador.iloc[0])
                        if self.info_jugador_actual is not None:
                            self.actualizar_grafico_radar()

            else:
                messagebox.showinfo("Límite alcanzado", "Solo se puede comparar hasta 3 jugadores.")

    def quitar_jugador_comparar(self):
        seleccion = self.lista_comparar.curselection()

        if not seleccion:
            return

        indice = seleccion[0]
        self.lista_comparar.delete(indice)

        if 0 <= indice < len(self.jugadores_comparar):
            self.jugadores_comparar.pop(indice)
            if self.info_jugador_actual is not None:
                self.actualizar_grafico_radar()

    def al_seleccionar_temporada(self, evento):
        nombre_posicion = self.var_posicion.get()

        if nombre_posicion:
            clave_posicion = None

            for clave, valor in self.posiciones.items():
                if valor == nombre_posicion:
                    clave_posicion = clave
                    break

            if clave_posicion:
                self.cargar_datos_jugadores()
                self.actualizar_lista_jugadores(clave_posicion)

        else:
            self.cargar_datos_jugadores()
            self.lista_jugadores.delete(0, tk.END)

    def actualizar_lista_jugadores(self, clave_posicion):
        if self.df_jugadores is None:
            return

        self.lista_jugadores.delete(0, tk.END)

        try:
            jugadores_filtrados = self.df_jugadores[self.df_jugadores['position_group'] == clave_posicion]

            for _, fila_jugador in jugadores_filtrados.iterrows():
                nombre_jugador = fila_jugador.get('Player', 'Desconocido')
                self.lista_jugadores.insert(tk.END, nombre_jugador)

        except Exception as e:
            messagebox.showerror("Error", f"Error al actualizar la lista de jugadores: {str(e)}")

    def al_escribir_busqueda(self, evento):
        texto_busqueda = self.var_busqueda.get().lower()

        if not texto_busqueda:
            nombre_posicion = self.var_posicion.get()

            if nombre_posicion:
                clave_posicion = next((clave for clave, valor in self.posiciones.items() if valor == nombre_posicion), None)

                if clave_posicion:
                    self.actualizar_lista_jugadores(clave_posicion)

            else:
                 self.lista_jugadores.delete(0, tk.END)
            return

        self.lista_jugadores.delete(0, tk.END)

        if self.df_jugadores is None:
            return

        try:
            mascara = self.df_jugadores['nombre_normalizado'].astype(str).str.contains(texto_busqueda, na=False)
            jugadores_filtrados = self.df_jugadores[mascara]

            for _, fila_jugador in jugadores_filtrados.iterrows():
                nombre_jugador = fila_jugador.get('Player', 'Desconocido')
                self.lista_jugadores.insert(tk.END, nombre_jugador)

        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar jugadores: {str(e)}")

    def al_seleccionar_jugador(self, evento):
        seleccion = self.lista_jugadores.curselection()

        if not seleccion:
            return

        nombre_jugador = self.lista_jugadores.get(seleccion[0])

        if self.df_jugadores is None:
            return

        try:
            datos_jugador = self.df_jugadores[self.df_jugadores['Player'] == nombre_jugador]

            if datos_jugador.empty:
                return

            self.info_jugador_actual = datos_jugador.iloc[0]
            self.mostrar_detalles_jugador(self.info_jugador_actual)

        except Exception as e:
            messagebox.showerror("Error", f"Error al mostrar estadísticas del jugador: {str(e)}")

    def mostrar_detalles_jugador(self, serie_info_jugador):
        self.info_jugador_actual = serie_info_jugador
        self.texto_detalles.config(state=tk.NORMAL)
        self.texto_detalles.delete("1.0", tk.END)

        def añadir_detalle(etiqueta, valor, negrita=False, es_puntuacion=False):
            if negrita:
                self.texto_detalles.insert(tk.END, etiqueta + ": ", ("negrita_detalle",))

            else:
                 self.texto_detalles.insert(tk.END, etiqueta + ": ")

            if es_puntuacion:
                self.texto_detalles.insert(tk.END, f"{valor:.2f}/10\n", ("puntuacion_detalle",))

            else:
                self.texto_detalles.insert(tk.END, f"{valor}\n")

        self.texto_detalles.tag_configure("negrita_detalle", font=("Arial", 10, "bold"), foreground=self.colores["fg_white"])
        self.texto_detalles.tag_configure("categoria_encabezado", font=("Arial", 11, "bold"), foreground=self.colores["accent_color"], spacing1=5, spacing3=5)
        self.texto_detalles.tag_configure("etiqueta_estadistica", font=("Arial", 9), foreground=self.colores["fg_light"])
        self.texto_detalles.tag_configure("valor_estadistica", font=("Arial", 9, "bold"), foreground=self.colores["fg_white"])
        self.texto_detalles.tag_configure("puntuacion_detalle", font=("Arial", 10, "bold"), foreground=self.colores["green_accent"])

        añadir_detalle("Nombre", serie_info_jugador.get('Player', 'Desconocido'), negrita=True)
        añadir_detalle("Posición", serie_info_jugador.get('position_group', 'Desconocida'))
        añadir_detalle("Equipo", serie_info_jugador.get('Squad', 'Desconocido'))
        añadir_detalle("Liga", serie_info_jugador.get('Comp', 'Desconocida'))
        añadir_detalle("Temporada", serie_info_jugador.get('Season', 'Desconocida'))

        puntuacion = calcular_ponderacion_estadisticas(serie_info_jugador)
        puntuacion_normalizada = normalizar_puntuacion_individual(puntuacion, min_teorico=0, max_teorico=100, escala=10)
        añadir_detalle("Puntuación", round(puntuacion_normalizada, 2), es_puntuacion=True)

        self.texto_detalles.insert(tk.END, "\nEstadísticas completas:\n", ("categoria_encabezado",))

        categorias = {
            "STANDARD": ["Player", "Nation", "Pos", "Squad", "Age", "Born", "90s", "Comp", "Season"],
            "POSESIÓN": ["Touches", "Def Pen", "Def 3rd", "Mid 3rd", "Att 3rd", "Att Pen", "Live_x", "Take Ons - Attempted", "Succ", "Succ%", "Tkld", "Tkld%", "Carries", "Carries - TotDist", "Carries - PrgDist", "Carries - PrgC", "Carries - 1/3", "Carries - CPA", "Carries - Mis", "Carries - Dis", "Rec", "PrgR"],
            "MISC": ["CrdY", "CrdR", "2CrdY", "Fls", "Fld", "Off_x", "Crs_x", "Int_x", "TklW_x", "PKwon", "PKcon", "OG", "Recov", "Won", "Lost_x", "Won%"],
            "PASES": ["Total - Cmp", "Total - Att", "Total - Cmp%", "TotDist", "PrgDist", "Short - Cmp", "Short - Att", "Short - Cmp%", "Medium - Cmp", "Medium - Att", "Medium - Cmp%", "Long - Cmp", "Long - Att", "Long - Cmp%", "Ast", "xAG", "xA", "A-xAG", "KP", "1/3", "PPA", "CrsPA", "PrgP"],
            "DEFENSA": ["Total - Tkl", "TklW_y", "Tackles - Def 3rd", "Tackles - Mid 3rd", "Tackles - Att 3rd", "Dribblers- Tkl", "Att_x", "Tkl%", "Lost_y", "Total Blocks", "Shots Blocked", "Passes Blocked", "Int_y", "Tkl+Int", "Clr", "Err"],
            "TIROS": ["Gls", "Sh", "SoT", "SoT%", "Sh/90", "SoT/90", "G/Sh", "G/SoT", "Dist", "FK_x", "PK", "PKatt", "xG", "npxG", "npxG/Sh", "G-xG", "np:G-xG"],
            "CREACIÓN": ["SCA", "SCA90", "SCA - PassLive", "SCA - PassDead", "TO", "SCA - Sh", "SCA - Fld", "SCA - Def", "GCA", "GCA90", "GCA - PassLive", "GCA - PassDead", "TO.1", "GCA - Sh", "GCA - Fld", "GCA - Def"],
            "TIPOS DE PASES": ["Att_y", "Live_y", "Dead", "FK_y", "TB", "Sw", "Crs_y", "TI", "CK", "In", "Out", "Str", "Cmp", "Off_y", "Blocks"]
        }

        try:
            dir_script = os.path.dirname(__file__)
            dir_raiz = os.path.abspath(os.path.join(dir_script, "..", ".."))
            ruta_explicacion = os.path.join(dir_raiz, "data", "fbref_stats_explained.json")

            with open(ruta_explicacion, 'r', encoding='utf-8') as f:
                self.explicaciones_estadisticas = json.load(f)

        except FileNotFoundError:
            self.explicaciones_estadisticas = {}

        except json.JSONDecodeError:
            self.explicaciones_estadisticas = {}

        except Exception as e:
            self.explicaciones_estadisticas = {}

        for categoria, lista_estadisticas in categorias.items():
            self.texto_detalles.insert(tk.END, f"\n{categoria.upper()}:\n", ("categoria_encabezado",))

            for clave_estadistica in lista_estadisticas:
                if clave_estadistica in serie_info_jugador and not pd.isna(serie_info_jugador[clave_estadistica]):
                    valor = serie_info_jugador[clave_estadistica]

                    if isinstance(valor, (int, float)):
                        if clave_estadistica.endswith('%'):
                            valor_str = f"{valor:.1f}%"

                        else:
                            valor_str = f"{valor:.2f}" if isinstance(valor, float) else f"{valor}"

                    else:
                        valor_str = str(valor)

                    clave_segura = re.sub(r'\W+', '_', clave_estadistica)
                    nombre_tag = f"estadistica_{clave_segura}"
                    self.texto_detalles.insert(tk.END, f"  • {clave_estadistica}: ", (nombre_tag, "etiqueta_estadistica"))
                    self.texto_detalles.insert(tk.END, f"{valor_str}\n", ("valor_estadistica",))

                    if clave_estadistica in self.explicaciones_estadisticas:
                        self.texto_detalles.tag_bind(nombre_tag, "<Enter>",
                                                lambda evento, s=clave_estadistica: self.mostrar_tooltip_estadistica(evento, s))
                        self.texto_detalles.tag_bind(nombre_tag, "<Leave>", self.ocultar_tooltip_estadistica)

        self.texto_detalles.config(state=tk.DISABLED)
        self.actualizar_grafico_radar()

    def mostrar_tooltip_estadistica(self, evento, clave_estadistica_tooltip):
        self.ocultar_tooltip_estadistica(None)

        if clave_estadistica_tooltip in self.explicaciones_estadisticas:
            explicacion = self.explicaciones_estadisticas[clave_estadistica_tooltip]
            bbox = self.texto_detalles.bbox(tk.CURRENT)

            if not bbox: return
            x_rel, y_rel, _, _ = bbox
            x_root = self.texto_detalles.winfo_rootx()
            y_root = self.texto_detalles.winfo_rooty()

            self.ventana_tooltip = tk.Toplevel(self.master)
            self.ventana_tooltip.wm_overrideredirect(True)

            final_x = x_root + x_rel + 20
            final_y = y_root + y_rel + 20

            etiqueta_dummy = tk.Label(self.ventana_tooltip, text=explicacion, wraplength=300, font=("Arial", 9))
            etiqueta_dummy.pack()

            self.ventana_tooltip.update_idletasks()

            ancho_tip = self.ventana_tooltip.winfo_width()
            alto_tip = self.ventana_tooltip.winfo_height()

            etiqueta_dummy.destroy()

            ancho_pantalla = self.master.winfo_screenwidth()
            alto_pantalla = self.master.winfo_screenheight()

            if final_x + ancho_tip > ancho_pantalla:
                final_x = ancho_pantalla - ancho_tip - 10

            if final_x < 0 : final_x = 10

            if final_y + alto_tip > alto_pantalla:
                final_y = y_root + y_rel - alto_tip - 10

            if final_y < 0 : final_y = 10

            self.ventana_tooltip.wm_geometry(f"+{int(final_x)}+{int(final_y)}")
            self.ventana_tooltip.configure(background=self.colores["tooltip_bg"])

            etiqueta = tk.Label(self.ventana_tooltip, text=explicacion, justify=tk.LEFT,
                           background=self.colores["tooltip_bg"], foreground=self.colores["fg_light"],
                           relief=tk.SOLID,
                           borderwidth=1,
                           wraplength=300, font=("Arial", 9),
                           highlightbackground=self.colores["tooltip_border"],
                           highlightcolor=self.colores["tooltip_border"],
                           highlightthickness=1,
                           padx=5, pady=5)
            etiqueta.pack()

    def ocultar_tooltip_estadistica(self, evento):
        if self.ventana_tooltip:
            self.ventana_tooltip.destroy()
            self.ventana_tooltip = None

    def actualizar_grafico_radar(self):
        for widget in self.marco_grafico.winfo_children():
            if widget != self.etiqueta_grafico:
                widget.destroy()

        if self.info_jugador_actual is None:
            if not self.etiqueta_grafico.winfo_ismapped():
                 self.etiqueta_grafico.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            return

        if self.etiqueta_grafico.winfo_ismapped():
            self.etiqueta_grafico.pack_forget()

        posicion = self.info_jugador_actual.get('position_group', '')

        estadisticas_por_posicion = {
            "GK": {"Save%": "% Paradas", "CS%": "% Porterías 0", "PSxG/SoT": "Calidad Paradas", "Stp%": "% Salidas Exitosas", "Total - Cmp%": "Precisión Pases", "Long - Cmp%": "Prec. Pases Largos"},
            "Defender": {"Tkl%": "% Entradas Exitosas", "Won%": "% Duelos Aéreos Gan.", "Total - Cmp%": "Precisión Pases", "Long - Cmp%": "Prec. Pases Largos", "Succ%": "% Regates Exitosos", "Blocks": "Bloqueos Tot."},
            "Defensive-Midfielders": {"Tkl%": "% Entradas Exitosas", "Total - Cmp%": "Precisión Pases", "Won%": "% Duelos Aéreos Gan.", "Succ%": "% Regates Exitosos", "Medium - Cmp%": "Prec. Pases Medios", "Int_y": "Intercepciones"},
            "Central Midfielders": {"Total - Cmp%": "Precisión Pases", "Medium - Cmp%": "Prec. Pases Medios", "Long - Cmp%": "Prec. Pases Largos", "Succ%": "% Regates Exitosos", "KP": "Pases Clave", "SoT%": "% Tiros Puerta"},
            "Attacking Midfielders": {"SoT%": "% Tiros Puerta", "G/Sh": "Efic. Tiro", "Succ%": "% Regates Exitosos", "Total - Cmp%": "Precisión Pases", "KP": "Pases Clave", "Ast": "Asistencias"},
            "Wing-Back": {"Total - Cmp%": "Precisión Pases", "Succ%": "% Regates Exitosos", "Tkl%": "% Entradas Exitosas", "CrsPA": "Centros", "Won%": "% Duelos Aéreos Gan.", "Carries - PrgC": "Progresión Conducción"},
            "Forwards": {"G/Sh": "Efic. Tiro", "SoT%": "% Tiros Puerta", "G/SoT": "Goles/Tiro Puerta", "Succ%": "% Regates Exitosos", "Won%": "% Duelos Aéreos Gan.", "npxG": "xG (sin penaltis)"}
        }

        estadisticas_usar = estadisticas_por_posicion.get(posicion, {
            "SoT%": "% Tiros Puerta", "G/Sh": "Efic. Tiro", "Total - Cmp%": "Precisión Pases",
            "Succ%": "% Regates Exitosos", "Won%": "% Duelos Aéreos Gan.", "Tkl%": "% Entradas Exitosas"
        })

        claves_estadisticas = list(estadisticas_usar.keys())
        etiquetas_estadisticas = list(estadisticas_usar.values())

        todos_jugadores_grafico = [self.info_jugador_actual] + self.jugadores_comparar
        todos_valores_norm = {estad: [] for estad in claves_estadisticas}

        for serie_jugador in todos_jugadores_grafico:
            for clave_estadistica_grafico in claves_estadisticas:
                if clave_estadistica_grafico in serie_jugador and pd.notna(serie_jugador[clave_estadistica_grafico]):
                    try:
                        todos_valores_norm[clave_estadistica_grafico].append(float(serie_jugador[clave_estadistica_grafico]))
                    except ValueError:
                        todos_valores_norm[clave_estadistica_grafico].append(0.0)

                else:
                    todos_valores_norm[clave_estadistica_grafico].append(0.0)

        figura = Figure(figsize=(6, 5.5), facecolor=self.colores["bg_dark_widget"], dpi=100)
        eje = figura.add_subplot(111, polar=True, facecolor=self.colores["bg_dark_entry"])

        N = len(claves_estadisticas)
        angulos = [n / float(N) * 2 * np.pi for n in range(N)]
        angulos += angulos[:1]

        eje.set_xticks(angulos[:-1])
        eje.set_xticklabels(etiquetas_estadisticas, color=self.colores["fg_light"], fontdict={'fontsize': 9})
        eje.tick_params(axis='x', pad=10)
        eje.set_ylim(0, 100)
        eje.set_yticks([20, 40, 60, 80, 100])
        eje.set_yticklabels([f"{val}%" for val in [20, 40, 60, 80, 100]], color=self.colores["fg_light"], fontsize=8)
        eje.grid(True, color=self.colores["fg_light"], linestyle='--', linewidth=0.5, alpha=0.3)
        eje.spines['polar'].set_color(self.colores["fg_light"])
        eje.spines['polar'].set_linewidth(0.5)

        colores_grafico = [self.colores["accent_color"]] + ['#FFCA28', '#66BB6A', '#EF5350'][:len(self.jugadores_comparar)]

        for i, serie_jugador in enumerate(todos_jugadores_grafico):
            if i > 3 : break

            valores_normalizados = []

            for clave_estadistica_grafico in claves_estadisticas:
                valor = 0.0

                if clave_estadistica_grafico in serie_jugador and pd.notna(serie_jugador[clave_estadistica_grafico]):
                    try:
                        valor = float(serie_jugador[clave_estadistica_grafico])

                    except ValueError:
                        pass

                valor_normalizado = 0.0

                if clave_estadistica_grafico.endswith('%'):
                    valor_normalizado = valor

                elif clave_estadistica_grafico in ["G/Sh", "G/SoT", "PSxG/SoT"]:
                    valor_normalizado = min(100, valor * 100 if clave_estadistica_grafico in ["G/Sh", "G/SoT"] else valor + 50 if clave_estadistica_grafico == "PSxG/SoT" else valor)

                else:
                    max_valor = max(todos_valores_norm[clave_estadistica_grafico]) if todos_valores_norm[clave_estadistica_grafico] else 1
                    valor_normalizado = (valor / max_valor) * 100 if max_valor > 0 else 0

                valores_normalizados.append(min(100, max(0, valor_normalizado)))

            valores_normalizados += valores_normalizados[:1]

            eje.plot(angulos, valores_normalizados, linewidth=1.5, linestyle='solid', label=serie_jugador['Player'], color=colores_grafico[i % len(colores_grafico)])
            eje.fill(angulos, valores_normalizados, alpha=0.25, color=colores_grafico[i % len(colores_grafico)])

        leyenda = eje.legend(loc='lower center', bbox_to_anchor=(0.5, -0.25), ncol=min(len(todos_jugadores_grafico), 4), frameon=False)

        for texto in leyenda.get_texts():
            texto.set_color(self.colores["fg_light"])
            texto.set_fontsize(9)

        figura.tight_layout(pad=1.5)

        self.figura = figura

        canvas = FigureCanvasTkAgg(figura, master=self.marco_grafico)
        canvas.draw()

        widget_canvas = canvas.get_tk_widget()
        widget_canvas.configure(background=self.colores["bg_dark_widget"])
        widget_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        if hasattr(self, "boton_exportar_grafico") and self.boton_exportar_grafico.winfo_exists():
            self.boton_exportar_grafico.pack_forget()
        else:
            self.boton_exportar_grafico = ttk.Button(self.marco_grafico, text="Exportar Gráfico",
                                                     command=self.exportar_grafico)
        self.boton_exportar_grafico.pack(side=tk.BOTTOM, pady=5)


    def exportar_grafico(self):
        if hasattr(self, "figura") and self.figura is not None:
            self.figura.savefig("grafico_radar.png")
            messagebox.showinfo("Exportación", "Gráfico exportado como PNG.")
        else:
            messagebox.showwarning("Exportación", "No hay gráfico para exportar.")