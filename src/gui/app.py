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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.agentes.analista_qwen import configurar_agente as configurar_agente_qwen
from src.agentes.analista_gemini import configurar_agente as configurar_agente_gemini
from src.agentes.analista_groq import configurar_agente as configurar_agente_groq
from src.data_management.data_loader import cargar_estadisticas_jugadores
from src.core.ranking_logic import calcular_ranking_jugadores, calcular_ponderacion_estadisticas
from src.core.fuzzy_matrices import generar_flpr, calcular_flpr_comun, calcular_matrices_flpr
from src.core.consensus_logic import calcular_matriz_similitud, calcular_cr
from langchain_core.prompts import ChatPromptTemplate


class FootballAnalysisApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Moneyball")
        self.geometry("1600x1080")

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
                             foreground=self.colors["fg_light"], # Color del texto del borde
                             font=("Arial", 11, "bold"),
                             borderwidth=1,
                             relief=tk.SOLID) # Relieve cambiado para mejor definición
        self.style.configure("TLabelFrame.Label",
                             background=self.colors["bg_dark_widget"], # Fondo de la parte de la etiqueta
                             foreground=self.colors["fg_light"],
                             font=("Arial", 11, "bold"))


        self.style.configure("TButton",
                             font=("Arial", 10, "bold"),
                             background=self.colors["accent_color"],
                             foreground=self.colors["fg_white"],
                             borderwidth=1, # Mantener un borde delgado para definición
                             relief=tk.FLAT, # Aspecto plano moderno
                             padding=[10, 5])
        self.style.map("TButton",
                       background=[("active", self.colors["accent_secondary"]),
                                   ("disabled", self.colors["bg_dark_secondary"])],
                       foreground=[("disabled", self.colors["disabled_fg"])],
                       relief=[("pressed", tk.SUNKEN), ("active", tk.RAISED)])


        self.style.configure("TEntry",
                             fieldbackground=self.colors["bg_dark_entry"],
                             foreground=self.colors["fg_light"],
                             insertcolor=self.colors["fg_light"], # Color del cursor
                             borderwidth=1, # Borde sutil
                             relief=tk.FLAT,
                             padding=6) # Padding aumentado
        self.style.map("TEntry",
                       bordercolor=[("focus", self.colors["accent_color"])],
                       relief=[("focus", tk.SOLID)])


        self.style.configure("TCombobox",
                             fieldbackground=self.colors["bg_dark_entry"],
                             background=self.colors["bg_dark_entry"], # Fondo de la flecha
                             foreground=self.colors["fg_light"],
                             arrowcolor=self.colors["fg_light"],
                             selectbackground=self.colors["accent_secondary"], # Fondo de selección del desplegable
                             selectforeground=self.colors["fg_white"], # Texto de selección del desplegable
                             borderwidth=1,
                             relief=tk.FLAT,
                             padding=6) # Padding aumentado
        self.style.map("TCombobox",
                       bordercolor=[("focus", self.colors["accent_color"])],
                       relief=[("focus", tk.SOLID)],
                       background=[('readonly', self.colors["bg_dark_entry"])],
                       fieldbackground=[('readonly', self.colors["bg_dark_entry"])],
                       foreground=[('readonly', self.colors["fg_light"])])

        # Para la lista desplegable de TCombobox
        self.option_add('*TCombobox*Listbox.background', self.colors["bg_dark_entry"])
        self.option_add('*TCombobox*Listbox.foreground', self.colors["fg_light"])
        self.option_add('*TCombobox*Listbox.selectBackground', self.colors["accent_secondary"])
        self.option_add('*TCombobox*Listbox.selectForeground', self.colors["fg_white"])
        self.option_add('*TCombobox*Listbox.font', ("Arial", 10))
        self.option_add('*TCombobox*Listbox.bd', 0) # Sin borde para el listbox mismo
        self.option_add('*TCombobox*Listbox.highlightthickness', 0)


        self.style.configure("TScrollbar",
                             background=self.colors["bg_dark_widget"],
                             troughcolor=self.colors["bg_dark_main"],
                             bordercolor=self.colors["bg_dark_widget"],
                             arrowcolor=self.colors["fg_light"],
                             relief=tk.FLAT)
        self.style.map("TScrollbar",
                       background=[("active", self.colors["accent_color"])])

        # Crear el notebook (contenedor de pestañas)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Crear las pestañas, pasando los colores
        self.evaluation_tab = EvaluationTab(self.notebook, self.colors)
        self.database_tab = DatabaseTab(self.notebook, self.colors)

        # Añadir las pestañas al notebook
        self.notebook.add(self.evaluation_tab, text="Evaluar Jugadores")
        self.notebook.add(self.database_tab, text="Consultar Estadísticas")

        # Inicializar los agentes en un hilo separado para no bloquear la interfaz
        self.initialize_agents_thread = threading.Thread(target=self.initialize_agents)
        self.initialize_agents_thread.daemon = True
        self.initialize_agents_thread.start()

        # Mostrar mensaje de inicialización
        self.status_label = ttk.Label(self, text="Inicializando agentes... Por favor espere.", anchor="center")
        # Usar el fondo principal para la etiqueta de estado para que se mezcle con la parte inferior de la ventana
        self.status_label.configure(background=self.colors["bg_dark_main"],
                                    foreground=self.colors["fg_light"],
                                    font=("Arial", 9))
        self.status_label.pack(pady=5, fill=tk.X)


        # Verificar periódicamente si los agentes están listos
        self.after(1000, self.check_agents_ready)

    def initialize_agents(self):
        """Inicializa los agentes en un hilo separado"""
        try:
            self.agente_qwen = configurar_agente_qwen()
            self.agente_gemini = configurar_agente_gemini()
            self.agente_groq = configurar_agente_groq()
            self.agents_ready = True

            # Pasar los agentes a la pestaña de evaluación
            self.evaluation_tab.set_agents(self.agente_qwen, self.agente_gemini, self.agente_groq)
        except Exception as e:
            self.agents_ready = False
            self.agent_error = str(e)
            print(f"Error initializing agents: {e}") # Imprimir error para depuración

    def check_agents_ready(self):
        """Verifica si los agentes están listos y actualiza la interfaz"""
        if hasattr(self, 'agents_ready'):
            if self.agents_ready:
                self.status_label.config(text="Agentes inicializados correctamente.", foreground=self.colors["green_accent"])
                self.after(3000, lambda: self.status_label.pack_forget()) # Hacer que desaparezca después de un tiempo
            else:
                self.status_label.config(text=f"Error al inicializar agentes: {self.agent_error}", foreground=self.colors["red_accent"])
        else:
            # Verificar de nuevo en 1 segundo
            self.after(1000, self.check_agents_ready)


class EvaluationTab(ttk.Frame):
    """
    Pestaña para la evaluación de jugadores con agentes.
    Permite al usuario seleccionar hasta 3 jugadores y criterios para que los agentes los evalúen.
    """
    def __init__(self, parent, colors):
        super().__init__(parent)
        self.colors = colors

        self.agente_qwen = None
        self.agente_gemini = None
        self.agente_groq = None

        self.selected_players = []
        self.selected_criteria = []
        self.max_players = 3
        self.player_data_dict = {}

        self.valores_linguisticos = ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]

        self.seasons = ["2022-2023", "2023-2024", "2024-2025"]
        self.selected_season = StringVar(value=self.seasons[-1])

        self.load_player_data()

        self.create_widgets()

    def load_player_data(self):
        """Carga los datos de jugadores desde la base de datos"""
        try:
            season = self.selected_season.get()
            self.df_players = cargar_estadisticas_jugadores(season)
            if isinstance(self.df_players, str):  # Si hay un error
                messagebox.showerror("Error", f"Error al cargar datos de jugadores: {self.df_players}")
                self.df_players = None
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar datos de jugadores: {str(e)}")
            self.df_players = None

    def create_widgets(self):
        """Crea los widgets para la pestaña de evaluación"""
        # Frame principal con dos columnas
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame izquierdo para selección de jugadores y criterios
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Frame derecho para resultados
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # --- FRAME IZQUIERDO ---

        # Frame para búsqueda de jugadores
        search_frame = ttk.LabelFrame(left_frame, text="Buscar Jugadores")
        search_frame.pack(fill=tk.X, pady=5, ipady=5) # Añadido ipady para padding interno

        # Frame para selección de temporada
        season_frame = ttk.Frame(search_frame)
        season_frame.pack(fill=tk.X, padx=10, pady=(5,10)) # Padding aumentado

        ttk.Label(season_frame, text="Temporada:").pack(side=tk.LEFT, padx=(0,5))
        self.season_combo = ttk.Combobox(season_frame, textvariable=self.selected_season,
                                        values=self.seasons, state="readonly", width=8) # Ancho aumentado
        self.season_combo.pack(side=tk.LEFT, padx=5)
        self.season_combo.bind("<<ComboboxSelected>>", self.on_season_selected)

        # Entrada para buscar jugador
        self.search_var = StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X, padx=10, pady=(0,10)) # Padding aumentado
        self.search_entry.bind("<KeyRelease>", self.on_search_key_release)

        # Listbox para mostrar jugadores encontrados
        players_frame_inner = ttk.Frame(search_frame) # Renombrado para evitar conflicto
        players_frame_inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,5))

        self.players_listbox = tk.Listbox(players_frame_inner, height=8,
                                         bg=self.colors["bg_dark_entry"], fg=self.colors["fg_light"],
                                         selectbackground=self.colors["accent_color"],
                                         selectforeground=self.colors["fg_white"],
                                         borderwidth=0, highlightthickness=0,
                                         font=("Arial", 10))
        self.players_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        players_scrollbar = ttk.Scrollbar(players_frame_inner, command=self.players_listbox.yview)
        players_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.players_listbox.config(yscrollcommand=players_scrollbar.set)

        # Botón para añadir jugador seleccionado
        add_player_button = ttk.Button(search_frame, text="Añadir Jugador", command=self.add_selected_player)
        add_player_button.pack(fill=tk.X, padx=10, pady=(5,10))

        # Frame para jugadores seleccionados
        selected_players_frame = ttk.LabelFrame(left_frame, text="Jugadores Seleccionados")
        selected_players_frame.pack(fill=tk.X, pady=5, ipady=5)

        # Listbox para mostrar jugadores seleccionados
        self.selected_players_listbox = tk.Listbox(selected_players_frame, height=3,
                                                   bg=self.colors["bg_dark_entry"], fg=self.colors["fg_light"],
                                                   selectbackground=self.colors["accent_color"],
                                                   selectforeground=self.colors["fg_white"],
                                                   borderwidth=0, highlightthickness=0,
                                                   font=("Arial", 10))
        self.selected_players_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Botón para eliminar jugador seleccionado
        remove_player_button = ttk.Button(selected_players_frame, text="Eliminar Jugador", command=self.remove_selected_player)
        remove_player_button.pack(fill=tk.X, padx=10, pady=(0,10))

        # Frame para criterios de evaluación
        criteria_frame = ttk.LabelFrame(left_frame, text="Criterios de Evaluación")
        criteria_frame.pack(fill=tk.X, pady=5, ipady=5)

        # Definir criterios predefinidos por posición
        self.predefined_criteria = {
                "General": ["Técnica", "Físico", "Visión de juego", "Posicionamiento", "Toma de decisiones", "Liderazgo", "Disciplina táctica", "Versatilidad"],
                "Porteros": ["Paradas", "Juego aéreo", "Juego con los pies", "Reflejos", "Posicionamiento", "Comunicación", "Salidas", "Distribución", "Penaltis"],
                "Defensas": ["Anticipación", "Juego aéreo", "Entradas", "Posicionamiento", "Salida de balón", "Marcaje", "Bloqueos", "Despejes", "Velocidad", "Agresividad"],
                "Mediocentros defensivos": ["Recuperación", "Pases", "Posicionamiento", "Visión de juego", "Resistencia", "Cobertura", "Presión", "Duelos aéreos", "Intercepciones"],
                "Mediocentros": ["Control", "Pases", "Visión de juego", "Técnica", "Movilidad", "Llegada al área", "Regate", "Creatividad", "Trabajo defensivo"],
                "Mediopuntas": ["Creatividad", "Regate", "Pases", "Disparo", "Movimiento sin balón", "Asociación", "Llegada", "Finalización", "Desmarque"],
                "Carrileros": ["Velocidad", "Centros", "Resistencia", "Defensa", "Ataque", "Regate", "Apoyo ofensivo", "Cobertura defensiva", "Desborde"],
                "Delanteros": ["Definición", "Movimiento", "Juego aéreo", "Técnica", "Posicionamiento", "Desmarque", "Finalización", "Regate", "Asociación", "Presión alta"]
            }

        # Frame para selección de posición
        position_frame = ttk.Frame(criteria_frame)
        position_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(position_frame, text="Posición:").pack(side=tk.LEFT, padx=(0,5))
        self.position_var = StringVar()
        positions = list(self.predefined_criteria.keys())
        self.position_combo = ttk.Combobox(position_frame, textvariable=self.position_var,
                                          values=positions, state="readonly", width=20)
        self.position_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.position_combo.current(0)  # Seleccionar "General" por defecto
        self.position_combo.bind("<<ComboboxSelected>>", self.on_position_selected)

        # Frame para mostrar criterios disponibles y seleccionados
        criteria_selection_frame = ttk.Frame(criteria_frame)
        criteria_selection_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Frame para criterios disponibles
        available_criteria_frame = ttk.LabelFrame(criteria_selection_frame, text="Disponibles") # Título más corto
        available_criteria_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        self.available_criteria_listbox = tk.Listbox(available_criteria_frame, height=5,
                                                      bg=self.colors["bg_dark_entry"], fg=self.colors["fg_light"],
                                                      selectbackground=self.colors["accent_color"],
                                                      selectforeground=self.colors["fg_white"],
                                                      borderwidth=0, highlightthickness=0,
                                                      font=("Arial", 10))
        self.available_criteria_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Frame para criterios seleccionados
        selected_criteria_frame = ttk.LabelFrame(criteria_selection_frame, text="Seleccionados") # Título más corto
        selected_criteria_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
        self.criteria_listbox = tk.Listbox(selected_criteria_frame, height=5,
                                           bg=self.colors["bg_dark_entry"], fg=self.colors["fg_light"],
                                           selectbackground=self.colors["accent_color"],
                                           selectforeground=self.colors["fg_white"],
                                           borderwidth=0, highlightthickness=0,
                                           font=("Arial", 10))
        self.criteria_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Botones para añadir/eliminar criterios
        criteria_buttons_frame = ttk.Frame(criteria_frame)
        criteria_buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        add_criteria_button = ttk.Button(criteria_buttons_frame, text="Añadir →", command=self.add_selected_criteria)
        add_criteria_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        remove_criteria_button = ttk.Button(criteria_buttons_frame, text="← Eliminar", command=self.remove_criteria)
        remove_criteria_button.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

        # Inicializar la lista de criterios disponibles
        self.update_available_criteria("General")

        # Frame para parámetros de evaluación
        params_frame = ttk.LabelFrame(left_frame, text="Parámetros de Evaluación")
        params_frame.pack(fill=tk.X, pady=5, ipady=5)

        # Nivel de consenso
        consensus_frame = ttk.Frame(params_frame)
        consensus_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(consensus_frame, text="Nivel de consenso (0-1):").pack(side=tk.LEFT)
        self.consensus_var = StringVar(value="0.8")
        consensus_entry = ttk.Entry(consensus_frame, textvariable=self.consensus_var, width=5)
        consensus_entry.pack(side=tk.RIGHT)

        # Máximo de rondas
        rounds_frame = ttk.Frame(params_frame)
        rounds_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(rounds_frame, text="Máximo de rondas:").pack(side=tk.LEFT)
        self.rounds_var = StringVar(value="3")
        rounds_entry = ttk.Entry(rounds_frame, textvariable=self.rounds_var, width=5)
        rounds_entry.pack(side=tk.RIGHT)

        # Botón para iniciar evaluación
        self.evaluate_button = ttk.Button(left_frame, text="Evaluar Jugadores", command=self.evaluate_players)
        self.evaluate_button.pack(fill=tk.X, pady=10, ipady=5) # Añadido ipady para un botón más grande

        # --- FRAME DERECHO ---

        # Área de texto para mostrar resultados
        results_frame = ttk.LabelFrame(right_frame, text="Resultados de la Evaluación")
        results_frame.pack(fill=tk.BOTH, expand=True, ipady=5)

        self.results_text = tk.Text(results_frame, wrap=tk.WORD, state=tk.DISABLED,
                                    bg=self.colors["bg_dark_entry"], fg=self.colors["fg_light"],
                                    insertbackground=self.colors["fg_white"], # Cursor más brillante
                                    borderwidth=0, highlightthickness=0,
                                    font=("Arial", 10), relief=tk.FLAT, padx=5, pady=5) # Padding añadido
        self.results_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)

        results_scrollbar = ttk.Scrollbar(results_frame, command=self.results_text.yview)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_text.config(yscrollcommand=results_scrollbar.set)

        # Añadir mensaje inicial
        self.add_result("Bienvenido al sistema de evaluación de jugadores.\n\n"
                       "Instrucciones:\n"
                       "1. Seleccione hasta 3 jugadores\n"
                       "2. Defina los criterios de evaluación\n"
                       "3. Ajuste los parámetros si lo desea\n"
                       "4. Haga clic en 'Evaluar Jugadores'\n\n"
                       "Los agentes evaluarán a los jugadores y mostrarán los resultados aquí.")

    def set_agents(self, agente_qwen, agente_gemini, agente_groq):
        """Establece los agentes para la evaluación"""
        self.agente_qwen = agente_qwen
        self.agente_gemini = agente_gemini
        self.agente_groq = agente_groq
        # Asegurarse que results_text existe antes de llamar a add_result
        if hasattr(self, 'results_text') and self.results_text.winfo_exists():
            self.add_result("Los agentes están listos para la evaluación.")


    def add_result(self, message):
        """Añade un mensaje al área de resultados"""
        if not hasattr(self, 'results_text') or not self.results_text.winfo_exists(): # Comprobar si el widget existe
            return
        self.results_text.config(state=tk.NORMAL)
        self.results_text.insert(tk.END, f"{message}\n\n")
        self.results_text.see(tk.END)
        self.results_text.config(state=tk.DISABLED)

    def on_season_selected(self, event):
        """Maneja la selección de una temporada"""
        # Recargar los datos con la nueva temporada
        self.load_player_data()
        # Limpiar la lista de jugadores
        self.players_listbox.delete(0, tk.END)
        # Limpiar la búsqueda
        self.search_var.set("")

    def on_search_key_release(self, event):
        """Maneja la búsqueda de jugadores mientras se escribe"""
        search_text = self.search_var.get().lower()

        # Limpiar la lista actual
        self.players_listbox.delete(0, tk.END)

        if not search_text or self.df_players is None:
            return

        try:
            # Filtrar jugadores que coincidan con la búsqueda
            if 'normalized_name' not in self.df_players.columns:
                # Crear 'normalized_name' si no existe, manejando posibles NaNs en 'Player'
                self.df_players['normalized_name'] = self.df_players['Player'].fillna('').astype(str).str.lower()


            # Asegurarse que 'normalized_name' sea de tipo string para operaciones de string
            # Esto es crucial si 'Player' puede tener valores no-string que no se convierten bien
            mask = self.df_players['normalized_name'].astype(str).str.contains(search_text, na=False)
            filtered_players = self.df_players[mask]


            # Limitar a 20 resultados para no sobrecargar la interfaz
            filtered_players = filtered_players.head(20)

            # Limpiar y rellenar el diccionario de datos de jugadores
            self.player_data_dict.clear()

            # Añadir jugadores a la listbox
            for index, player_row in filtered_players.iterrows(): # Usar player_row para evitar conflicto
                player_name = player_row.get('Player', 'Desconocido')
                # Guardar los datos del jugador para usarlos más tarde
                self.player_data_dict[player_name] = player_row # Guardar el Series completo

                self.players_listbox.insert(tk.END, player_name)
        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar jugadores: {str(e)}")


    def add_selected_player(self):
        """Añade el jugador seleccionado a la lista de jugadores seleccionados"""
        selection = self.players_listbox.curselection()
        if not selection:
            messagebox.showinfo("Información", "Por favor, seleccione un jugador de la lista.")
            return

        display_name = self.players_listbox.get(selection[0])

        # Verificar si ya está en la lista
        if display_name in self.selected_players:
            messagebox.showinfo("Información", f"El jugador '{display_name}' ya está seleccionado.")
            return

        # Verificar si ya hay 3 jugadores seleccionados
        if len(self.selected_players) >= self.max_players:
            messagebox.showinfo("Información", f"Solo puede seleccionar hasta {self.max_players} jugadores.")
            return

        # Añadir a la lista y actualizar la interfaz
        self.selected_players.append(display_name)
        self.selected_players_listbox.insert(tk.END, display_name)

    def remove_selected_player(self):
        """Elimina el jugador seleccionado de la lista de jugadores seleccionados"""
        selection = self.selected_players_listbox.curselection()
        if not selection:
            messagebox.showinfo("Información", "Por favor, seleccione un jugador de la lista para eliminarlo.")
            return

        index = selection[0]
        player_name = self.selected_players_listbox.get(index)

        # Eliminar de la lista y actualizar la interfaz
        if player_name in self.selected_players: # Asegurarse que está en la lista antes de remover
             self.selected_players.remove(player_name)
        self.selected_players_listbox.delete(index)


    def on_position_selected(self, event):
        """Maneja la selección de una posición"""
        selected_position = self.position_var.get()
        self.update_available_criteria(selected_position)

    def update_available_criteria(self, position):
        """Actualiza la lista de criterios disponibles según la posición seleccionada"""
        # Limpiar la lista actual
        self.available_criteria_listbox.delete(0, tk.END)

        # Añadir los criterios predefinidos para la posición seleccionada
        if position in self.predefined_criteria:
            for criteria_item in self.predefined_criteria[position]: # Renombrar criteria a criteria_item
                # Solo añadir si no está ya en la lista de seleccionados
                if criteria_item not in self.selected_criteria:
                    self.available_criteria_listbox.insert(tk.END, criteria_item)


    def add_selected_criteria(self):
        """Añade el criterio seleccionado a la lista de criterios seleccionados"""
        selection = self.available_criteria_listbox.curselection()
        if not selection:
            messagebox.showinfo("Información", "Por favor, seleccione un criterio de la lista disponible.")
            return

        criteria_item = self.available_criteria_listbox.get(selection[0]) # Renombrar criteria a criteria_item

        # Verificar si ya está en la lista
        if criteria_item in self.selected_criteria:
            messagebox.showinfo("Información", f"El criterio '{criteria_item}' ya está en la lista.")
            return

        # Añadir a la lista y actualizar la interfaz
        self.selected_criteria.append(criteria_item)
        self.criteria_listbox.insert(tk.END, criteria_item)

        # Eliminar de la lista de disponibles
        self.available_criteria_listbox.delete(selection[0])

    def remove_criteria(self):
        """Elimina el criterio seleccionado de la lista de criterios"""
        selection = self.criteria_listbox.curselection()
        if not selection:
            messagebox.showinfo("Información", "Por favor, seleccione un criterio de la lista para eliminarlo.")
            return

        index = selection[0]
        criteria_item = self.criteria_listbox.get(index) # Renombrar criteria a criteria_item

        # Eliminar de la lista y actualizar la interfaz
        if criteria_item in self.selected_criteria: # Asegurarse que está en la lista antes de remover
            self.selected_criteria.remove(criteria_item)
        self.criteria_listbox.delete(index)

        # Añadir de nuevo a disponibles si estaba predefinido para la posición actual
        current_pos = self.position_var.get()
        if current_pos in self.predefined_criteria and \
           criteria_item in self.predefined_criteria[current_pos]:
            # Solo añadir si no está ya en la lista de disponibles (evitar duplicados)
            if criteria_item not in self.available_criteria_listbox.get(0, tk.END):
                 self.available_criteria_listbox.insert(tk.END, criteria_item)


    def evaluate_players(self):
        """Inicia el proceso de evaluación de jugadores"""
        # Verificar que haya jugadores seleccionados
        if not self.selected_players:
            messagebox.showinfo("Información", "Por favor, seleccione al menos un jugador.")
            return

        # Verificar que haya criterios seleccionados
        if not self.selected_criteria:
            messagebox.showinfo("Información", "Por favor, ingrese al menos un criterio.")
            return

        # Verificar que los agentes estén inicializados
        if not all([self.agente_qwen, self.agente_gemini, self.agente_groq]):
            messagebox.showinfo("Información", "Los agentes aún no están inicializados. Por favor, espere.")
            return

        # Obtener parámetros
        try:
            consenso_minimo = float(self.consensus_var.get())
            if not (0 <= consenso_minimo <= 1):
                messagebox.showinfo("Información", "El nivel de consenso debe estar entre 0 y 1.")
                return
        except ValueError:
            messagebox.showinfo("Información", "Por favor, ingrese un valor numérico válido para el nivel de consenso.")
            return

        try:
            max_rondas = int(self.rounds_var.get())
            if max_rondas <= 0:
                messagebox.showinfo("Información", "El número máximo de rondas debe ser mayor que 0.")
                return
        except ValueError:
            messagebox.showinfo("Información", "Por favor, ingrese un valor numérico válido para el máximo de rondas.")
            return

        # Deshabilitar el botón de evaluación mientras se procesa
        self.evaluate_button.config(state=tk.DISABLED)

        # Limpiar el área de resultados
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)
        self.results_text.config(state=tk.DISABLED)

        # Añadir mensaje de inicio
        self.add_result("Iniciando evaluación de jugadores...\n")
        self.add_result(f"Jugadores: {', '.join(self.selected_players)}")
        self.add_result(f"Criterios: {', '.join(self.selected_criteria)}")
        self.add_result(f"Nivel de consenso: {consenso_minimo}")
        self.add_result(f"Máximo de rondas: {max_rondas}")

        # Iniciar evaluación en un hilo separado para no bloquear la interfaz
        threading.Thread(target=self.run_evaluation, args=(
            self.selected_players,
            self.selected_criteria,
            consenso_minimo,
            max_rondas
        ), daemon=True).start() # daemon=True para que el hilo se cierre si la app principal se cierra

    def run_evaluation(self, jugadores, criterios, consenso_minimo, max_rondas):
        """Ejecuta el proceso de evaluación en un hilo separado"""
        try:
            # Crear el prompt para los agentes
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

            def procesar_csv_agente(output_agente, criterios_list): # Renombrar criterios a criterios_list
                matriz = []
                try:
                    csv_match = re.search(r'```(?:csv|CSV)\s*([\s\S]*?)```', output_agente)
                    if csv_match:
                        csv_content = csv_match.group(1).strip()
                    else: # Fallback si no hay ```CSV```
                        lines = output_agente.strip().split('\n')
                        # Heurística: encontrar la línea que parece ser el encabezado
                        header_line_index = -1
                        for i, line in enumerate(lines):
                            if "jugador" in line.lower() and all(c.lower() in line.lower() for c in criterios_list):
                                header_line_index = i
                                break
                        if header_line_index != -1:
                             csv_content = '\n'.join(lines[header_line_index:]).strip()
                        else: # Si no se encuentra un encabezado claro, intentar con las últimas líneas que tengan comas
                            potential_csv_lines = [line for line in lines if line.count(',') >= len(criterios_list)-1]
                            if potential_csv_lines:
                                csv_content = "\n".join(potential_csv_lines)
                            else:
                                self.add_result(f"ADVERTENCIA: No se pudo extraer contenido CSV claro de la respuesta del agente.")
                                return [], False


                    csv_data = StringIO(csv_content)
                    reader = csv.DictReader(csv_data)

                    for row in reader:
                        calificaciones = []
                        csv_headers = [h.strip().lower() for h in reader.fieldnames if h]

                        for criterio_esperado in criterios_list:
                            criterio_esperado_lower = criterio_esperado.lower()
                            valor_encontrado = None
                            # Buscar el criterio en los encabezados del CSV
                            for csv_header in csv_headers:
                                if criterio_esperado_lower == csv_header: # Coincidencia exacta
                                    valor_encontrado = row.get(reader.fieldnames[csv_headers.index(csv_header)]) # Usar el nombre original del fieldname
                                    break
                                elif criterio_esperado_lower in csv_header: # Coincidencia parcial (contenida)
                                    valor_encontrado = row.get(reader.fieldnames[csv_headers.index(csv_header)])
                                    # Podríamos añadir una lógica para preferir la coincidencia más específica si hay varias
                                    break # Tomar la primera coincidencia parcial por ahora

                            if valor_encontrado is not None:
                                calificaciones.append(str(valor_encontrado).replace("'", "").replace('"', "").strip())
                            else:
                                if len(row) == len(criterios_list) + 1:
                                    try:
                                        idx_criterio = criterios_list.index(criterio_esperado)
                                        valor_encontrado = list(row.values())[idx_criterio + 1]
                                        calificaciones.append(str(valor_encontrado).replace("'", "").replace('"', "").strip())
                                        self.add_result(f"ADVERTENCIA: Criterio '{criterio_esperado}' no encontrado por nombre, usando posición.")
                                    except (ValueError, IndexError):
                                        self.add_result(f"ERROR: Criterio '{criterio_esperado}' no encontrado en los datos del CSV ni por posición.")
                                        return [], False # Fallo si un criterio no se puede mapear
                                else:
                                    self.add_result(f"ERROR: Criterio '{criterio_esperado}' no encontrado en los datos del CSV. Headers: {csv_headers}")
                                    return [], False # Fallo si un criterio no se puede mapear
                        matriz.append(calificaciones)
                    if not matriz:
                        self.add_result(f"ERROR: No se pudieron extraer datos de la matriz del CSV. Contenido CSV procesado:\n{csv_content}")
                        return [], False
                    return matriz, True
                except Exception as e:
                    self.add_result(f"ERROR: No se pudo procesar la salida del agente: {str(e)}\nContenido CSV intentado:\n{csv_content if 'csv_content' in locals() else 'No disponible'}")
                    return [], False


            def generar_matriz_aleatoria(jugadores_list, criterios_list, valores_linguisticos): # Renombrar
                import random
                matriz = []
                for _ in jugadores_list:
                    calificaciones = [random.choice(valores_linguisticos) for _ in criterios_list]
                    matriz.append(calificaciones)
                return matriz

            def evaluar_con_agente(agente, prompt_str, jugadores_list, criterios_list, valores_linguisticos, nombre_agente, max_intentos_agente): # Renombrar
                self.add_result(f"\n=== Evaluación con el Agente {nombre_agente} ===")
                intento_actual = 0
                matriz_agente = []

                while intento_actual < max_intentos_agente:
                    intento_actual += 1
                    self.add_result(f"Consultando al agente {nombre_agente} (Intento {intento_actual}/{max_intentos_agente})...")
                    try:
                        respuesta_agente = agente.invoke({"input": prompt_str})
                        output_agente = respuesta_agente.get("output", "No hay respuesta del agente.")
                    except Exception as e:
                        output_agente = f"ERROR: Excepción al invocar agente {nombre_agente}: {str(e)}"
                        self.add_result(output_agente)
                        if intento_actual >= max_intentos_agente:
                            break
                        continue

                    if nombre_agente == "Qwen":
                        output_agente = re.sub(r"<think>.*?</think>", "", output_agente, flags=re.DOTALL)

                    self.add_result(f"\nRespuesta del Agente {nombre_agente}:\n{output_agente}")

                    if "ERROR:" in output_agente.upper() or "NO HAY RESPUESTA" in output_agente.upper() :
                        self.add_result(f"El agente {nombre_agente} reportó un error o no respondió. Reintentando si es posible...")
                        if intento_actual >= max_intentos_agente: break
                        continue

                    matriz_agente, exito = procesar_csv_agente(output_agente, criterios_list)

                    if exito:
                        self.add_result(f"✅ CSV procesado correctamente para el agente {nombre_agente}.")
                        break
                    elif intento_actual >= max_intentos_agente:
                        self.add_result(f"Se alcanzó el número máximo de intentos ({max_intentos_agente}) para el agente {nombre_agente} o el CSV no fue válido.")
                        break
                    else:
                        self.add_result(f"Formato CSV no válido del agente {nombre_agente}. Reintentando...")
                        # Modificar el prompt para el reintento podría ser útil aquí, pero por ahora solo reintenta.

                if not matriz_agente:
                    self.add_result(f"Generando valores lingüísticos aleatorios para el agente {nombre_agente}...")
                    matriz_agente = generar_matriz_aleatoria(jugadores_list, criterios_list, valores_linguisticos)
                    self.add_result(f"Se han generado valores lingüísticos aleatorios para el agente {nombre_agente}.")

                return matriz_agente, output_agente if 'output_agente' in locals() else "No se obtuvo respuesta."


            # Evaluación con los agentes
            self.add_result("\nIniciando evaluación con los agentes...")

            matriz_agente_qwen, _ = evaluar_con_agente(
                self.agente_qwen, prompt, jugadores, criterios, self.valores_linguisticos, "Qwen", 1) # Solo un intento para qwen

            matriz_agente_gemini, _ = evaluar_con_agente(
                self.agente_gemini, prompt, jugadores, criterios, self.valores_linguisticos, "Gemini", max_intentos)

            matriz_agente_groq, _ = evaluar_con_agente(
                self.agente_groq, prompt, jugadores, criterios, self.valores_linguisticos, "Groq", max_intentos)


            # Solicitar evaluación del usuario
            self.add_result("\n\nAhora es tu turno de evaluar a los jugadores.")
            self.add_result("Por favor, selecciona las calificaciones en la ventana emergente.")

            # Crear ventana emergente para la evaluación del usuario
            user_matrices = self.get_user_evaluation(jugadores, criterios)

            if not user_matrices:
                self.add_result("Evaluación cancelada por el usuario.")
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

            self.add_result("\nCalculando matrices FLPR...")

            flpr_matrices = {}
            for nombre, matriz_eval in matrices.items(): # Renombrar matriz a matriz_eval
                if not matriz_eval or not any(matriz_eval): # Comprobar si la matriz está vacía o contiene solo listas vacías
                    self.add_result(f"ADVERTENCIA: Matriz de evaluación para '{nombre}' está vacía. Saltando cálculo de FLPR.")
                    flpr_matrices[nombre] = None # O una FLPR por defecto si es necesario
                    continue

                flpr_matriz_calculada = None
                if criterios and len(matriz_eval[0]) == len(criterios):
                    for idx, criterio_item in enumerate(criterios):
                        calificaciones_criterio = [fila[idx] for fila in matriz_eval if len(fila) > idx]

                        if not calificaciones_criterio:
                             self.add_result(f"ADVERTENCIA: No hay calificaciones para el criterio '{criterio_item}' en la matriz de '{nombre}'.")
                             continue

                        flpr_criterio = generar_flpr(calificaciones_criterio)

                        if flpr_matriz_calculada is None:
                            flpr_matriz_calculada = flpr_criterio
                        elif flpr_criterio is not None :
                            flpr_matriz_calculada = calcular_flpr_comun(flpr_matriz_calculada, flpr_criterio)
                    flpr_matrices[nombre] = flpr_matriz_calculada
                else:
                    self.add_result(f"ADVERTENCIA: No se pudo calcular FLPR para '{nombre}' debido a discrepancia en criterios o estructura de matriz.")
                    flpr_matrices[nombre] = None


            flpr_usuario = flpr_matrices.get("Usuario")
            flpr_agente_qwen = flpr_matrices.get("Qwen")
            flpr_agente_gemini = flpr_matrices.get("Gemini")
            flpr_agente_groq = flpr_matrices.get("Groq")

            # Manejar el caso donde alguna FLPR sea None antes de calcular FLPR comunes
            flpr_validas_agentes = [f for f in [flpr_agente_qwen, flpr_agente_gemini, flpr_agente_groq] if f is not None]

            if len(flpr_validas_agentes) < 2:
                self.add_result("ADVERTENCIA: No hay suficientes FLPRs de agentes válidas para calcular FLPR común de agentes.")
                flpr_agentes = None
            elif len(flpr_validas_agentes) == 2:
                flpr_agentes = calcular_flpr_comun(flpr_validas_agentes[0], flpr_validas_agentes[1])
            else: # 3 FLPRs válidas
                flpr_agentes_temp = calcular_flpr_comun(flpr_validas_agentes[0], flpr_validas_agentes[1])
                flpr_agentes = calcular_flpr_comun(flpr_agentes_temp, flpr_validas_agentes[2])


            if flpr_agentes is not None and flpr_usuario is not None:
                flpr_colectiva = calcular_flpr_comun(flpr_agentes, flpr_usuario)
            elif flpr_agentes is not None:
                flpr_colectiva = flpr_agentes
                self.add_result("ADVERTENCIA: Usando FLPR de agentes como colectiva debido a FLPR de usuario no válida.")
            elif flpr_usuario is not None:
                flpr_colectiva = flpr_usuario
                self.add_result("ADVERTENCIA: Usando FLPR de usuario como colectiva debido a FLPR de agentes no válida.")
            else:
                self.add_result("ERROR CRÍTICO: No se pudieron calcular FLPRs válidas. No se puede continuar con el ranking.")
                if hasattr(self, 'evaluate_button') and self.evaluate_button.winfo_exists():
                    self.evaluate_button.config(state=tk.NORMAL)
                return


            # Calcular matrices de similitud solo si las FLPRs son válidas
            matrices_similitud_validas = []
            if flpr_usuario is not None and flpr_agente_qwen is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_usuario, flpr_agente_qwen))
            if flpr_usuario is not None and flpr_agente_gemini is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_usuario, flpr_agente_gemini))
            if flpr_usuario is not None and flpr_agente_groq is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_usuario, flpr_agente_groq))
            if flpr_agente_qwen is not None and flpr_agente_gemini is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_agente_qwen, flpr_agente_gemini))
            if flpr_agente_qwen is not None and flpr_agente_groq is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_agente_qwen, flpr_agente_groq))
            if flpr_agente_gemini is not None and flpr_agente_groq is not None: matrices_similitud_validas.append(calcular_matriz_similitud(flpr_agente_gemini, flpr_agente_groq))

            self.add_result("\n=== Revisión de Matrices de Agentes ===")
            self.add_result("Antes de calcular el consenso global, puedes revisar las matrices de los "
                            "agentes para detectar y corregir posibles sesgos.")

            matrices_originales = {
                "Usuario": matriz_usuario,
                "Agente Qwen": matriz_agente_qwen,
                "Agente Gemini": matriz_agente_gemini,
                "Agente Groq": matriz_agente_groq
            }

            # Mostrar diálogo para revisar matrices
            matrices_revisadas = self.review_agent_matrices(jugadores, criterios, matrices_originales)

            if matrices_revisadas is not None:
                self.add_result("Aplicando cambios de la revisión de matrices y recalculando FLPRs...")

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
                self.add_result("ERROR: No se pudieron calcular matrices de similitud. No se puede determinar el consenso.")
                cr, consenso_alcanzado = 0, False
            else:
                cr, consenso_alcanzado = calcular_cr(matrices_similitud_validas, consenso_minimo)


            self.add_result(f"\n=== Nivel de Consenso ===")
            self.add_result(f"Nivel de consenso (CR): {cr:.3f}") # Formatear CR
            self.add_result(f"Consenso mínimo requerido: {consenso_minimo}")

            # Calcular y mostrar el ranking de agentes según su distancia al consenso
            self.add_result(f"\n=== Ranking de Agentes por Distancia al Consenso ===")
            self.add_result("Este ranking muestra qué agentes están más lejos de la opinión colectiva:")

            # Calcular la similitud de cada agente con la FLPR colectiva
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

            # Ordenar por distancia (de mayor a menor)
            distancias_agentes.sort(key=lambda x: x[1], reverse=True)

            # Mostrar el ranking
            for posicion, (agente, distancia) in enumerate(distancias_agentes, 1):
                self.add_result(f"{posicion}. {agente} - Distancia al consenso: {distancia:.3f}")

            # Explicar el impacto en el consenso global
            if distancias_agentes:
                agente_mas_lejano = distancias_agentes[0][0]
                distancia_maxima = distancias_agentes[0][1]
                self.add_result(f"\nEl agente que más influye en reducir el consenso global es: {agente_mas_lejano} (distancia: {distancia_maxima:.3f})")

            if consenso_alcanzado:
                self.add_result("✅ Se ha alcanzado el nivel mínimo de consenso.")
                if flpr_colectiva is not None:
                    self.add_result("\n=== Ranking de Jugadores ===")
                    ranking = calcular_ranking_jugadores(flpr_colectiva, jugadores)
                    self.add_result("TOP JUGADORES (de mejor a peor):")
                    for posicion, (jugador, puntuacion) in enumerate(ranking, 1):
                        self.add_result(f"{posicion}. {jugador} - Puntuación: {puntuacion:.3f}")
                else:
                    self.add_result("No se puede generar ranking debido a FLPR colectiva no válida.")
            else:
                self.add_result("❌ No se ha alcanzado el nivel mínimo de consenso.")
                self.add_result("\n=== Iniciando fase de discusión y re-evaluación ===")

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

                # Bucle de rondas de discusión
                while ronda_actual <= max_rondas and not consenso_alcanzado_nuevo:
                    self.add_result(f"\n\n=== RONDA DE DISCUSIÓN {ronda_actual}/{max_rondas} ===")

                    # Formatear calificaciones para mostrar a los agentes
                    def formatear_calificaciones(jugadores_list, criterios_list, matriz, nombre_agente):
                        calificaciones_str = f"Mis calificaciones como agente {nombre_agente} para los jugadores son:\n"
                        for i, jugador in enumerate(jugadores_list):
                            calificaciones_str += f"{jugador}: "
                            for j, criterio in enumerate(criterios_list):
                                calificaciones_str += f"{criterio}: {matriz[i][j]}, "
                            calificaciones_str = calificaciones_str.rstrip(", ") + "\n"
                        return calificaciones_str

                    # Preparar las cadenas de calificaciones para esta ronda
                    calificaciones_qwen_str = formatear_calificaciones(jugadores, criterios, matriz_agente_qwen_actual, f"Qwen (Ronda {ronda_actual})")
                    calificaciones_gemini_str = formatear_calificaciones(jugadores, criterios, matriz_agente_gemini_actual, f"Gemini (Ronda {ronda_actual})")
                    calificaciones_groq_str = formatear_calificaciones(jugadores, criterios, matriz_agente_groq_actual, f"Groq (Ronda {ronda_actual})")

                    # Para el usuario usamos un formato ligeramente diferente
                    calificaciones_usuario_str = f"Las calificaciones del usuario para los jugadores (Ronda {ronda_actual}) son:\n"
                    for i, jugador in enumerate(jugadores):
                        calificaciones_usuario_str += f"{jugador}: "
                        for j, criterio in enumerate(criterios):
                            calificaciones_usuario_str += f"{criterio}: {matriz_usuario_actual[i][j]}, "
                        calificaciones_usuario_str = calificaciones_usuario_str.rstrip(", ") + "\n"

                    self.add_result("Informando a los agentes sobre las calificaciones actuales...")

                    # Informar a cada agente sobre sus propias calificaciones y las de los demás
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

                    # Crear ventana de discusión
                    self.add_result(f"\n=== Discusión sobre las valoraciones (Ronda {ronda_actual}/{max_rondas}) ===")
                    self.add_result("Ahora puedes discutir con los agentes sobre las valoraciones realizadas.")

                    # Crear ventana emergente para la discusión
                    discusion_window = tk.Toplevel(self.master)
                    discusion_window.configure(background=self.colors["bg_dark_widget"])
                    discusion_window.title(f"Discusión sobre valoraciones - Ronda {ronda_actual}/{max_rondas}")
                    discusion_window.geometry("800x600")
                    discusion_window.transient(self.master)
                    discusion_window.grab_set()

                    # Frame principal
                    main_frame = ttk.Frame(discusion_window, padding=10)
                    main_frame.pack(fill=tk.BOTH, expand=True)

                    # Instrucciones
                    ttk.Label(main_frame, text=f"Discusión sobre valoraciones (Ronda {ronda_actual}/{max_rondas}):", 
                             font=("Arial", 11, "bold")).pack(pady=(0, 15))

                    # Frame para selección de agente
                    selection_frame = ttk.Frame(main_frame)
                    selection_frame.pack(fill=tk.X, pady=(0, 10))

                    ttk.Label(selection_frame, text="Selecciona un agente:").pack(side=tk.LEFT, padx=(0, 10))

                    # Variable para el agente seleccionado
                    selected_agent = StringVar(value="Qwen")

                    # Combobox para seleccionar agente
                    agent_selector = ttk.Combobox(selection_frame, textvariable=selected_agent, 
                                                 values=["Qwen", "Gemini", "Groq"], state="readonly", width=15)
                    agent_selector.pack(side=tk.LEFT)

                    # Frame para el historial de la conversación
                    conversation_frame = ttk.Frame(main_frame)
                    conversation_frame.pack(fill=tk.BOTH, expand=True, pady=10)

                    # Crear un widget Text para mostrar la conversación
                    conversation_text = tk.Text(conversation_frame, wrap=tk.WORD, width=80, height=15,
                                              bg=self.colors["bg_dark_widget"], fg=self.colors["fg_light"])
                    conversation_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

                    # Scrollbar para el texto
                    scrollbar = ttk.Scrollbar(conversation_frame, command=conversation_text.yview)
                    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                    conversation_text.config(yscrollcommand=scrollbar.set)

                    # Frame para entrada de texto
                    input_frame = ttk.Frame(main_frame)
                    input_frame.pack(fill=tk.X, pady=(10, 0))

                    # Entrada de texto
                    user_input = tk.Text(input_frame, wrap=tk.WORD, width=80, height=3,
                                       bg=self.colors["bg_dark_entry"], fg=self.colors["fg_light"])
                    user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

                    # Historial de la conversación
                    conversation_history = []

                    # Función para enviar mensaje
                    def send_message():
                        agent_name = selected_agent.get()
                        message = user_input.get("1.0", tk.END).strip()

                        if not message:
                            return

                        # Añadir mensaje del usuario al historial
                        conversation_text.config(state=tk.NORMAL)
                        conversation_text.insert(tk.END, f"\nTú: {message}\n")
                        conversation_history.append(("user", message))

                        # Limpiar entrada
                        user_input.delete("1.0", tk.END)

                        # Preparar prompt para el agente
                        prompt_discusion = f"""
                            Basándote en las calificaciones y la discusión anterior, por favor, responde a la siguiente pregunta: {message}
                            No uses ninguna tool ni evalúes a los jugadores, solo responde esta pregunta.
                            Tu objetivo es evaluar críticamente las afirmaciones del usuario.
                            Si el usuario dice algo incorrecto o sin sentido, discútelo y explica por qué no estás de acuerdo.
                            Proporciona argumentos claros y basados en datos o lógica. No aceptes afirmaciones sin fundamento.
                            Si recibes una orden, explica tu punta de vista pero debes respetar la orden.
                        """

                        # Seleccionar el agente adecuado para responder
                        conversation_text.insert(tk.END, f"\n{agent_name} está respondiendo...\n")
                        conversation_text.see(tk.END)
                        conversation_text.config(state=tk.DISABLED)

                        # Actualizar la interfaz
                        discusion_window.update()

                        # Invocar al agente seleccionado
                        if agent_name == "Qwen":
                            respuesta = self.agente_qwen.invoke({"input": prompt_discusion})
                            agent_response = respuesta.get("output", "No hay respuesta")
                        elif agent_name == "Gemini":
                            respuesta = self.agente_gemini.invoke({"input": prompt_discusion})
                            agent_response = respuesta.get("output", "No hay respuesta")
                        else:  # Groq
                            respuesta = self.agente_groq.invoke({"input": prompt_discusion})
                            agent_response = respuesta.get("output", "No hay respuesta")

                        # Añadir respuesta del agente al historial
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

                    # Mensaje inicial
                    conversation_text.config(state=tk.NORMAL)
                    conversation_text.insert(tk.END, "Bienvenido a la discusión sobre valoraciones. Selecciona un agente y haz preguntas sobre las valoraciones.\n")
                    conversation_text.config(state=tk.DISABLED)

                    # Esperar a que se cierre la ventana
                    self.master.wait_window(discusion_window)

                    # Si se canceló la discusión, salir del bucle
                    if not continue_reevaluation[0]:
                        self.add_result("\nDiscusión cancelada. Finalizando evaluación.")
                        break

                    # Re-evaluación después de la discusión
                    self.add_result(f"\n=== Re-evaluación de jugadores (Ronda {ronda_actual}/{max_rondas}) ===")
                    self.add_result("Los agentes volverán a evaluar a los jugadores basándose en la discusión anterior.")

                    # Re-evaluación con el agente Qwen
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

                    El agente Qwen dio estas calificaciones:
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

                    El agente Qwen dio estas calificaciones:
                    {calificaciones_qwen_str}

                    El agente Gemini dio estas calificaciones:
                    {calificaciones_gemini_str}

                    Y el usuario dio estas calificaciones:
                    {calificaciones_usuario_str}

                    Proporciona tu nueva evaluación en el mismo formato CSV que usaste anteriormente.
                    """

                    max_intentos_reevaluacion = 3

                    # Re-evaluación con el agente Qwen
                    self.add_result(f"\n=== Re-evaluación con el Agente Qwen (Ronda {ronda_actual}/{max_rondas}) ===")
                    matriz_agente_qwen_nueva, output_reevaluacion_qwen = evaluar_con_agente(
                        self.agente_qwen, prompt_reevaluacion_qwen, jugadores, criterios, self.valores_linguisticos, "Qwen", max_intentos_reevaluacion)

                    self.add_result("\n=== Nueva evaluación del agente Qwen ===")
                    self.add_result(output_reevaluacion_qwen)

                    # Re-evaluación con el agente Gemini
                    self.add_result(f"\n=== Re-evaluación con el Agente Gemini (Ronda {ronda_actual}/{max_rondas}) ===")
                    matriz_agente_gemini_nueva, output_reevaluacion_gemini = evaluar_con_agente(
                        self.agente_gemini, prompt_reevaluacion_gemini, jugadores, criterios, self.valores_linguisticos, "Gemini", max_intentos_reevaluacion)

                    self.add_result("\n=== Nueva evaluación del agente Gemini ===")
                    self.add_result(output_reevaluacion_gemini)

                    # Re-evaluación con el agente Groq
                    self.add_result(f"\n=== Re-evaluación con el Agente Groq (Ronda {ronda_actual}/{max_rondas}) ===")
                    matriz_agente_groq_nueva, output_reevaluacion_groq = evaluar_con_agente(
                        self.agente_groq, prompt_reevaluacion_groq, jugadores, criterios, self.valores_linguisticos, "Groq", max_intentos_reevaluacion)

                    self.add_result("\n=== Nueva evaluación del agente Groq ===")
                    self.add_result(output_reevaluacion_groq)

                    # Re-evaluación del usuario
                    self.add_result(f"\n=== Re-evaluación del usuario (Ronda {ronda_actual}/{max_rondas}) ===")
                    self.add_result("Ahora es tu turno de volver a evaluar a los jugadores después de la discusión.")

                    matriz_usuario_nueva = self.get_user_evaluation(jugadores, criterios)
                    if matriz_usuario_nueva is None:
                        self.add_result("❌ Re-evaluación del usuario cancelada. Finalizando evaluación.")
                        break

                    # Calcular nuevas matrices FLPR
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

                    self.add_result(f"\n=== Matriz FLPR Final del Usuario (Después de la ronda {ronda_actual} de discusión) ===")

                    # Calcular matriz FLPR colectiva entre los agentes después de la reevaluación
                    flpr_agentes_qwen_gemini_nueva = calcular_flpr_comun(flpr_agente_qwen_nueva, flpr_agente_gemini_nueva)
                    flpr_agentes_nueva = calcular_flpr_comun(flpr_agentes_qwen_gemini_nueva, flpr_agente_groq_nueva)
                    self.add_result(f"\n=== Matriz FLPR Colectiva (Agentes) (Después de la ronda {ronda_actual} de discusión) ===")

                    # Calcular matriz FLPR colectiva después de la reevaluación
                    flpr_colectiva_nueva = calcular_flpr_comun(flpr_agentes_nueva, flpr_usuario_nueva)
                    self.add_result(f"\n=== Matriz FLPR Colectiva (Usuario y Agentes) (Después de la ronda {ronda_actual} de discusión) ===")

                    # Calcular matrices de similitud después de la discusión
                    matrices_similitud_nuevas = []
                    if flpr_usuario_nueva is not None and flpr_agente_qwen_nueva is not None: matrices_similitud_nuevas.append(calcular_matriz_similitud(flpr_usuario_nueva, flpr_agente_qwen_nueva))
                    if flpr_usuario_nueva is not None and flpr_agente_gemini_nueva is not None: matrices_similitud_nuevas.append(calcular_matriz_similitud(flpr_usuario_nueva, flpr_agente_gemini_nueva))
                    if flpr_usuario_nueva is not None and flpr_agente_groq_nueva is not None: matrices_similitud_nuevas.append(calcular_matriz_similitud(flpr_usuario_nueva, flpr_agente_groq_nueva))
                    if flpr_agente_qwen_nueva is not None and flpr_agente_gemini_nueva is not None: matrices_similitud_nuevas.append(calcular_matriz_similitud(flpr_agente_qwen_nueva, flpr_agente_gemini_nueva))
                    if flpr_agente_qwen_nueva is not None and flpr_agente_groq_nueva is not None: matrices_similitud_nuevas.append(calcular_matriz_similitud(flpr_agente_qwen_nueva, flpr_agente_groq_nueva))
                    if flpr_agente_gemini_nueva is not None and flpr_agente_groq_nueva is not None: matrices_similitud_nuevas.append(calcular_matriz_similitud(flpr_agente_gemini_nueva, flpr_agente_groq_nueva))

                    # Calcular nivel de consenso después de la discusión
                    if not matrices_similitud_nuevas:
                        self.add_result("ERROR: No se pudieron calcular matrices de similitud nuevas. No se puede determinar el consenso.")
                        cr_nuevo, consenso_alcanzado_nuevo = 0, False
                    else:
                        cr_nuevo, consenso_alcanzado_nuevo = calcular_cr(matrices_similitud_nuevas, consenso_minimo)

                    self.add_result(f"\n=== Nivel de Consenso (Después de la ronda {ronda_actual} de discusión) ===")
                    self.add_result(f"Nivel de consenso (CR): {cr_nuevo:.3f}")
                    self.add_result(f"Consenso mínimo requerido: {consenso_minimo}")

                    if consenso_alcanzado_nuevo:
                        self.add_result("✅ Se ha alcanzado el nivel mínimo de consenso.")
                    else:
                        self.add_result("❌ No se ha alcanzado el nivel mínimo de consenso.")

                    # Comparar el nivel de consenso antes y después de la discusión
                    if cr_nuevo > cr:
                        self.add_result(f"\nEl nivel de consenso ha mejorado después de la discusión: {cr:.3f} → {cr_nuevo:.3f}")
                    elif cr_nuevo < cr:
                        self.add_result(f"\nEl nivel de consenso ha disminuido después de la discusión: {cr:.3f} → {cr_nuevo:.3f}")
                    else:
                        self.add_result(f"\nEl nivel de consenso se ha mantenido igual después de la discusión: {cr:.3f}")

                    # Actualizar las variables para la siguiente ronda
                    flpr_usuario_actual = flpr_usuario_nueva
                    flpr_agente_qwen_actual = flpr_agente_qwen_nueva
                    flpr_agente_gemini_actual = flpr_agente_gemini_nueva
                    flpr_agente_groq_actual = flpr_agente_groq_nueva
                    flpr_colectiva_actual = flpr_colectiva_nueva
                    matriz_usuario_actual = matriz_usuario_nueva
                    matriz_agente_qwen_actual = matriz_agente_qwen_nueva
                    matriz_agente_gemini_actual = matriz_agente_gemini_nueva
                    matriz_agente_groq_actual = matriz_agente_groq_nueva

                    # Incrementar el contador de rondas
                    ronda_actual += 1

                    # Si se alcanzó el consenso o se llegó al máximo de rondas, mostrar el ranking de jugadores
                    if consenso_alcanzado_nuevo or ronda_actual > max_rondas:
                        self.add_result("\n=== Ranking de Jugadores (Después de la discusión) ===")
                        ranking = calcular_ranking_jugadores(flpr_colectiva_nueva, jugadores)

                        self.add_result("TOP JUGADORES (de mejor a peor):")
                        for posicion, (jugador, puntuacion) in enumerate(ranking, 1):
                            self.add_result(f"{posicion}. {jugador} - Puntuación: {puntuacion:.3f}")

                        # Si se alcanzó el máximo de rondas sin consenso, dar una última oportunidad para modificar matrices
                        if not consenso_alcanzado_nuevo and ronda_actual > max_rondas:
                            self.add_result(f"\n⚠️ Se ha alcanzado el número máximo de rondas de discusión ({max_rondas}) sin llegar al consenso mínimo requerido.")
                            self.add_result(f"Nivel de consenso actual: {cr_nuevo:.3f}")

                            # Ofrecer una última oportunidad para modificar matrices
                            self.add_result("\n=== Última oportunidad para corregir sesgos ===")
                            self.add_result("Puedes revisar y modificar las matrices de términos lingüísticos una última vez antes de calcular el ranking final.")

                            # Mostrar diálogo para revisar matrices
                            matrices_finales = {
                                "Usuario": matriz_usuario_actual,
                                "Agente Qwen": matriz_agente_qwen_actual,
                                "Agente Gemini": matriz_agente_gemini_actual,
                                "Agente Groq": matriz_agente_groq_actual
                            }

                            matrices_revisadas_final = self.review_agent_matrices(jugadores, criterios, matrices_finales)

                            if matrices_revisadas_final is not None:
                                # Recalcular matrices FLPR
                                flpr_matrices_final = calcular_matrices_flpr(matrices_revisadas_final, criterios)

                                flpr_usuario_final = flpr_matrices_final["Usuario"]
                                flpr_agente_qwen_final = flpr_matrices_final["Agente Qwen"]
                                flpr_agente_gemini_final = flpr_matrices_final["Agente Gemini"]
                                flpr_agente_groq_final = flpr_matrices_final["Agente Groq"]

                                # Recalcular matriz FLPR colectiva
                                flpr_agentes_qwen_gemini_final = calcular_flpr_comun(flpr_agente_qwen_final, flpr_agente_gemini_final)
                                flpr_agentes_final = calcular_flpr_comun(flpr_agentes_qwen_gemini_final, flpr_agente_groq_final)
                                flpr_colectiva_final = calcular_flpr_comun(flpr_agentes_final, flpr_usuario_final)

                                # Recalcular matrices de similitud
                                matrices_similitud_final = []
                                if flpr_usuario_final is not None and flpr_agente_qwen_final is not None: matrices_similitud_final.append(calcular_matriz_similitud(flpr_usuario_final, flpr_agente_qwen_final))
                                if flpr_usuario_final is not None and flpr_agente_gemini_final is not None: matrices_similitud_final.append(calcular_matriz_similitud(flpr_usuario_final, flpr_agente_gemini_final))
                                if flpr_usuario_final is not None and flpr_agente_groq_final is not None: matrices_similitud_final.append(calcular_matriz_similitud(flpr_usuario_final, flpr_agente_groq_final))
                                if flpr_agente_qwen_final is not None and flpr_agente_gemini_final is not None: matrices_similitud_final.append(calcular_matriz_similitud(flpr_agente_qwen_final, flpr_agente_gemini_final))
                                if flpr_agente_qwen_final is not None and flpr_agente_groq_final is not None: matrices_similitud_final.append(calcular_matriz_similitud(flpr_agente_qwen_final, flpr_agente_groq_final))
                                if flpr_agente_gemini_final is not None and flpr_agente_groq_final is not None: matrices_similitud_final.append(calcular_matriz_similitud(flpr_agente_gemini_final, flpr_agente_groq_final))

                                # Recalcular nivel de consenso
                                if not matrices_similitud_final:
                                    self.add_result("ERROR: No se pudieron calcular matrices de similitud finales. No se puede determinar el consenso.")
                                    cr_final, consenso_alcanzado_final = 0, False
                                else:
                                    cr_final, consenso_alcanzado_final = calcular_cr(matrices_similitud_final, consenso_minimo)

                                self.add_result(f"\n=== Nivel de Consenso (Después de modificaciones finales) ===")
                                self.add_result(f"Nivel de consenso (CR): {cr_final:.3f}")
                                self.add_result(f"Consenso mínimo requerido: {consenso_minimo}")

                                if consenso_alcanzado_final:
                                    self.add_result("✅ Se ha alcanzado el nivel mínimo de consenso.")
                                else:
                                    self.add_result("❌ No se ha alcanzado el nivel mínimo de consenso.")

                                # Recalcular el ranking con las matrices actualizadas
                                self.add_result("\n=== Ranking de Jugadores (Actualizado) ===")
                                ranking_final = calcular_ranking_jugadores(flpr_colectiva_final, jugadores)

                                self.add_result("TOP JUGADORES (de mejor a peor):")
                                for posicion, (jugador, puntuacion) in enumerate(ranking_final, 1):
                                    self.add_result(f"{posicion}. {jugador} - Puntuación: {puntuacion:.3f}")

                                self.add_result(f"\nSe muestra el ranking con el nivel de consenso actual: {cr_final:.3f}")
                            else:
                                self.add_result(f"\nSe muestra el ranking con el nivel de consenso actual: {cr_nuevo:.3f}")

                # Si se alcanzó el consenso inicialmente, mostrar el ranking
                if consenso_alcanzado:
                    self.add_result("\nSe ha alcanzado el nivel mínimo de consenso. No es necesario realizar la discusión y re-evaluación.")


            self.add_result("\nEvaluación completada.")

        except Exception as e:
            self.add_result(f"Error durante la evaluación: {str(e)}")
            import traceback
            self.add_result(f"Traceback: {traceback.format_exc()}") # Añadir traceback para más detalles
        finally:
            # Habilitar el botón de evaluación
            if hasattr(self, 'evaluate_button') and self.evaluate_button.winfo_exists():
                 self.evaluate_button.config(state=tk.NORMAL)


    def get_user_evaluation(self, jugadores, criterios):
        """
        Muestra una ventana emergente para que el usuario evalúe a los jugadores.
        Retorna la matriz de evaluación del usuario.
        """
        # Crear ventana emergente
        eval_window = tk.Toplevel(self.master) # Usar self.master (la instancia principal de Tk) o self
        eval_window.configure(background=self.colors["bg_dark_widget"])
        eval_window.title("Evaluación de Jugadores")
        eval_window.geometry("700x450") # Tamaño ajustado
        eval_window.transient(self.master) # O self
        eval_window.grab_set()

        # Matriz para almacenar las evaluaciones
        user_matrix_vars = [] # Nombre diferente para la lista de StringVar
        for _ in jugadores:
            user_matrix_vars.append([StringVar(value="Medio") for _ in criterios])

        # Frame principal
        main_frame_eval = ttk.Frame(eval_window, padding=10) # Usar main_frame_eval
        main_frame_eval.pack(fill=tk.BOTH, expand=True)

        # Instrucciones
        ttk.Label(main_frame_eval, text="Evalúa a cada jugador según los criterios:", font=("Arial", 11, "bold")).pack(pady=(0, 15))

        # Frame para la tabla de evaluación
        table_frame = ttk.Frame(main_frame_eval)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Encabezados de columnas (criterios)
        header_font = ("Arial", 10, "bold")
        ttk.Label(table_frame, text="Jugador", font=header_font).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        for i, criterio_item in enumerate(criterios): # Renombrar criterio a criterio_item
            ttk.Label(table_frame, text=criterio_item, font=header_font).grid(row=0, column=i+1, padx=5, pady=5, sticky=tk.W)

        # Filas para cada jugador
        for i, jugador in enumerate(jugadores):
            ttk.Label(table_frame, text=jugador, font=("Arial", 10)).grid(row=i+1, column=0, padx=5, pady=5, sticky=tk.W)

            for j in range(len(criterios)):
                combo = ttk.Combobox(table_frame, textvariable=user_matrix_vars[i][j],
                                    values=self.valores_linguisticos, state="readonly", width=12, font=("Arial", 9))
                combo.grid(row=i+1, column=j+1, padx=5, pady=5, sticky=tk.EW) # Usar sticky EW para Combobox
                combo.current(2)  # Valor por defecto: "Medio" (índice 2)

        # Hacer columnas redimensionables para criterios
        table_frame.grid_columnconfigure(0, weight=1) # Columna de jugador
        for j in range(len(criterios)):
            table_frame.grid_columnconfigure(j+1, weight=1) # Columnas de criterios


        # Botones
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

        # Esperar a que se cierre la ventana
        self.master.wait_window(eval_window) # O self.wait_window

        return result_matrix[0]

    def review_agent_matrices(self, jugadores, criterios, matrices):
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
        self.add_result("\n=== Revisión de Matrices de Agentes ===")
        self.add_result("Puedes revisar las matrices de términos lingüísticos para identificar posibles sesgos.")

        # Crear ventana emergente
        review_window = tk.Toplevel(self.master)
        review_window.configure(background=self.colors["bg_dark_widget"])
        review_window.title("Revisión de Matrices de Agentes")
        review_window.geometry("800x600")
        review_window.transient(self.master)
        review_window.grab_set()

        # Frame principal
        main_frame = ttk.Frame(review_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Instrucciones
        ttk.Label(main_frame, text="Revisa las matrices de los agentes y modifica valores si detectas sesgos:", 
                 font=("Arial", 11, "bold")).pack(pady=(0, 15))

        # Frame para selección de matriz
        selection_frame = ttk.Frame(main_frame)
        selection_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(selection_frame, text="Selecciona una matriz:").pack(side=tk.LEFT, padx=(0, 10))

        # Variable para la matriz seleccionada
        selected_matrix = StringVar(value=list(matrices.keys())[0])

        # Combobox para seleccionar matriz
        matrix_selector = ttk.Combobox(selection_frame, textvariable=selected_matrix, 
                                      values=list(matrices.keys()), state="readonly", width=15)
        matrix_selector.pack(side=tk.LEFT)

        # Frame para la tabla de la matriz
        table_container = ttk.Frame(main_frame)
        table_container.pack(fill=tk.BOTH, expand=True, pady=10)

        # Scrollbar para la tabla
        scrollbar_y = ttk.Scrollbar(table_container)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        scrollbar_x = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Canvas para la tabla (para permitir scroll)
        canvas = tk.Canvas(table_container, yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set,
                          background=self.colors["bg_dark_widget"])
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar_y.config(command=canvas.yview)
        scrollbar_x.config(command=canvas.xview)

        # Frame dentro del canvas para la tabla
        table_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=table_frame, anchor=tk.NW)

        # Diccionario para almacenar las variables de las matrices
        matrix_vars = {}

        # Función para mostrar la matriz seleccionada
        def show_selected_matrix():
            # Limpiar tabla actual
            for widget in table_frame.winfo_children():
                widget.destroy()

            matrix_name = selected_matrix.get()
            matrix = matrices[matrix_name]

            # Si no existe en matrix_vars, crear las variables
            if matrix_name not in matrix_vars:
                matrix_vars[matrix_name] = []
                for i in range(len(jugadores)):
                    row_vars = []
                    for j in range(len(criterios)):
                        row_vars.append(StringVar(value=matrix[i][j]))
                    matrix_vars[matrix_name].append(row_vars)

            # Encabezados de columnas (criterios)
            header_font = ("Arial", 10, "bold")
            ttk.Label(table_frame, text="Jugador", font=header_font).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            for j, criterio in enumerate(criterios):
                ttk.Label(table_frame, text=criterio, font=header_font).grid(row=0, column=j+1, padx=5, pady=5, sticky=tk.W)

            # Filas para cada jugador
            for i, jugador in enumerate(jugadores):
                ttk.Label(table_frame, text=jugador, font=("Arial", 10)).grid(row=i+1, column=0, padx=5, pady=5, sticky=tk.W)

                for j in range(len(criterios)):
                    combo = ttk.Combobox(table_frame, textvariable=matrix_vars[matrix_name][i][j],
                                        values=self.valores_linguisticos, state="readonly", width=12, font=("Arial", 9))
                    combo.grid(row=i+1, column=j+1, padx=5, pady=5, sticky=tk.EW)

                    # Establecer el valor actual
                    current_value = matrix_vars[matrix_name][i][j].get()
                    if current_value in self.valores_linguisticos:
                        combo.current(self.valores_linguisticos.index(current_value))

            # Hacer columnas redimensionables
            table_frame.grid_columnconfigure(0, weight=1)
            for j in range(len(criterios)):
                table_frame.grid_columnconfigure(j+1, weight=1)

            # Actualizar el tamaño del canvas
            table_frame.update_idletasks()
            canvas.config(scrollregion=canvas.bbox("all"))

        # Asociar el cambio de selección con la función
        matrix_selector.bind("<<ComboboxSelected>>", lambda e: show_selected_matrix())

        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))

        result_matrices = [None]

        def on_cancel():
            result_matrices[0] = None
            review_window.destroy()

        def on_submit():
            # Actualizar las matrices con los valores modificados
            modified_matrices = {}
            for matrix_name, vars_matrix in matrix_vars.items():
                modified_matrix = []
                for i in range(len(jugadores)):
                    row = [vars_matrix[i][j].get() for j in range(len(criterios))]
                    modified_matrix.append(row)
                modified_matrices[matrix_name] = modified_matrix

            result_matrices[0] = modified_matrices
            review_window.destroy()

        cancel_button = ttk.Button(button_frame, text="Cancelar", command=on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=5, expand=True)

        submit_button = ttk.Button(button_frame, text="Guardar Cambios", command=on_submit)
        submit_button.pack(side=tk.RIGHT, padx=5, expand=True)

        # Mostrar la primera matriz
        show_selected_matrix()

        # Esperar a que se cierre la ventana
        self.master.wait_window(review_window)

        if result_matrices[0] is not None:
            self.add_result("✅ Matrices revisadas y modificadas correctamente.")
            return result_matrices[0]
        else:
            self.add_result("❌ Revisión de matrices cancelada.")
            return matrices


class DatabaseTab(ttk.Frame):
    """
    Pestaña para la consulta de la base de datos de jugadores.
    Permite al usuario seleccionar un jugador y temporada para ver sus estadísticas.
    """
    def __init__(self, parent, colors):
        super().__init__(parent)
        self.colors = colors

        self.positions = {
            "GK": "Portero",
            "Defender": "Defensa",
            "Defensive-Midfielders": "Mediocentro defensivo",
            "Central Midfielders": "Mediocentro",
            "Attacking Midfielders": "Mediapunta",
            "Wing-Back": "Carrilero",
            "Forwards": "Delantero"
        }

        self.seasons = ["2022-2023", "2023-2024", "2024-2025"]
        self.selected_season = StringVar(value=self.seasons[-1])

        self.tooltip_window = None

        self.compare_players = []
        self.current_player_info = None

        self.load_player_data()

        self.create_widgets()

    def load_player_data(self):
        """Carga los datos de jugadores desde la base de datos"""
        try:
            # Cargar datos para la temporada seleccionada
            season = self.selected_season.get()
            self.df_players = cargar_estadisticas_jugadores(season)
            if isinstance(self.df_players, str):  # Si hay un error
                messagebox.showerror("Error", f"Error al cargar datos de jugadores: {self.df_players}")
                self.df_players = None
            elif self.df_players is not None and 'Player' in self.df_players.columns:
                # Crear 'normalized_name' para búsquedas insensibles a mayúsculas
                self.df_players['normalized_name'] = self.df_players['Player'].fillna('').astype(str).str.lower()

        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar datos de jugadores: {str(e)}")
            self.df_players = None

    def create_widgets(self):
        """Crea los widgets para la pestaña de consulta de base de datos"""
        # Frame principal con dos columnas
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame izquierdo para selección y lista de jugadores
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10)) # Espaciado aumentado

        # Frame derecho para detalles y gráfico
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10,0)) # Espaciado aumentado

        # Frame para selección de posición y temporada
        selection_frame = ttk.Frame(left_frame)
        selection_frame.pack(fill=tk.X, padx=5, pady=5)

        # Frame para selección de posición
        position_frame = ttk.Frame(selection_frame)
        position_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))

        ttk.Label(position_frame, text="Posición:").pack(side=tk.LEFT, padx=(0,5))
        self.position_var = StringVar()
        self.position_combo = ttk.Combobox(position_frame, textvariable=self.position_var,
                                          values=list(self.positions.values()), state="readonly", width=20)
        self.position_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.position_combo.bind("<<ComboboxSelected>>", self.on_position_selected)

        # Frame para selección de temporada
        season_frame = ttk.Frame(selection_frame)
        season_frame.pack(side=tk.RIGHT, fill=tk.X, padx=(5,0))

        ttk.Label(season_frame, text="Temporada:").pack(side=tk.LEFT, padx=(0,5))
        self.season_combo = ttk.Combobox(season_frame, textvariable=self.selected_season,
                                        values=self.seasons, state="readonly", width=8)
        self.season_combo.pack(side=tk.LEFT, padx=5)
        self.season_combo.bind("<<ComboboxSelected>>", self.on_season_selected)


        # Frame para búsqueda de jugadores
        search_frame_db = ttk.LabelFrame(left_frame, text="Buscar Jugador")
        search_frame_db.pack(fill=tk.X, padx=5, pady=10, ipady=5)

        # Entrada para buscar jugador
        self.search_var_db = StringVar() # Renombrar para evitar conflicto
        self.search_entry_db = ttk.Entry(search_frame_db, textvariable=self.search_var_db) # Renombrar
        self.search_entry_db.pack(fill=tk.X, padx=10, pady=10) # Padding dentro del LabelFrame
        self.search_entry_db.bind("<KeyRelease>", self.on_search_key_release)


        # Listbox para mostrar jugadores encontrados
        self.players_frame = ttk.LabelFrame(left_frame, text="Jugadores")
        self.players_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, ipady=5)

        # Listbox con scrollbar
        players_list_frame = ttk.Frame(self.players_frame) # Frame interno para el listbox y scrollbar
        players_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5) # Padding dentro del LabelFrame

        self.players_listbox_db = tk.Listbox(players_list_frame, # Renombrar para evitar conflicto
                                         bg=self.colors["bg_dark_entry"], fg=self.colors["fg_light"],
                                         selectbackground=self.colors["accent_color"],
                                         selectforeground=self.colors["fg_white"],
                                         borderwidth=0, highlightthickness=0, font=("Arial",10))
        self.players_listbox_db.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        players_scrollbar_db = ttk.Scrollbar(players_list_frame, command=self.players_listbox_db.yview) # Renombrar
        players_scrollbar_db.pack(side=tk.RIGHT, fill=tk.Y)
        self.players_listbox_db.config(yscrollcommand=players_scrollbar_db.set)

        self.players_listbox_db.bind("<<ListboxSelect>>", self.on_player_selected)


        # Frame para comparación de jugadores
        self.compare_frame = ttk.LabelFrame(left_frame, text="Comparar Jugadores")
        self.compare_frame.pack(fill=tk.X, padx=5, pady=10, ipady=5)

        # Listbox para jugadores a comparar
        self.compare_listbox = tk.Listbox(self.compare_frame, height=3,
                                          bg=self.colors["bg_dark_entry"], fg=self.colors["fg_light"],
                                          selectbackground=self.colors["accent_color"],
                                          selectforeground=self.colors["fg_white"],
                                          borderwidth=0, highlightthickness=0, font=("Arial",10))
        self.compare_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=10) # Padding dentro del LabelFrame

        # Botones para añadir/quitar jugadores para comparar
        compare_buttons_frame = ttk.Frame(self.compare_frame)
        compare_buttons_frame.pack(side=tk.RIGHT, padx=10, pady=10) # Padding dentro del LabelFrame

        self.add_compare_btn = ttk.Button(compare_buttons_frame, text="Añadir",
                                         command=self.add_player_to_compare)
        self.add_compare_btn.pack(fill=tk.X, pady=2)

        self.remove_compare_btn = ttk.Button(compare_buttons_frame, text="Quitar",
                                           command=self.remove_player_from_compare)
        self.remove_compare_btn.pack(fill=tk.X, pady=2)


        # Frame para detalles del jugador
        self.details_frame = ttk.LabelFrame(right_frame, text="Detalles del Jugador")
        self.details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, ipady=5, ipadx=5) # ipady, ipadx para padding interno

        # Texto para mostrar detalles
        self.details_text = tk.Text(self.details_frame, wrap=tk.WORD, state=tk.DISABLED,
                                   bg=self.colors["bg_dark_entry"], fg=self.colors["fg_light"],
                                   insertbackground=self.colors["fg_white"], # Cursor más brillante
                                   borderwidth=0, highlightthickness=0, font=("Arial", 10), relief=tk.FLAT, padx=5, pady=5) # Padding
        self.details_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5) # Padding dentro del LabelFrame

        details_scrollbar = ttk.Scrollbar(self.details_frame, command=self.details_text.yview)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.config(yscrollcommand=details_scrollbar.set)


        # Frame para el gráfico de radar
        self.chart_frame = ttk.LabelFrame(right_frame, text="Gráfico Comparativo")
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, ipady=5, ipadx=5) # ipady, ipadx para padding interno

        # Placeholder para el gráfico
        self.chart_placeholder = ttk.Label(self.chart_frame, text="Seleccione un jugador para ver el gráfico", anchor="center")
        self.chart_placeholder.pack(fill=tk.BOTH, expand=True, padx=5, pady=5) # Padding dentro del LabelFrame

    def on_position_selected(self, event):
        """Maneja la selección de una posición"""
        selected_position_name = self.position_var.get()

        # Encontrar la clave de la posición seleccionada
        selected_position_key = None
        for key, value in self.positions.items():
            if value == selected_position_name:
                selected_position_key = key
                break

        if selected_position_key:
            # Actualizar la lista de jugadores
            self.update_players_list(selected_position_key)

    def add_player_to_compare(self):
        """Añade el jugador seleccionado a la lista de comparación"""
        selection = self.players_listbox_db.curselection() # Usar el listbox correcto
        if not selection:
            return

        player_name = self.players_listbox_db.get(selection[0])

        # Verificar si el jugador ya está en la lista de comparación (por nombre)
        if player_name not in [self.compare_listbox.get(i) for i in range(self.compare_listbox.size())]:
            # Añadir a la lista de comparación (máximo 3 jugadores para comparar + 1 principal)
            if self.compare_listbox.size() < 3: # Limitar a 3 en la lista de comparación
                self.compare_listbox.insert(tk.END, player_name)

                # Buscar datos del jugador
                if self.df_players is not None:
                    player_data_series = self.df_players[self.df_players['Player'] == player_name]
                    if not player_data_series.empty:
                        # Añadir el Series (o dict) a self.compare_players
                        self.compare_players.append(player_data_series.iloc[0])

                        # Actualizar el gráfico si hay un jugador principal seleccionado
                        if self.current_player_info is not None:
                            self.update_radar_chart()
            else:
                messagebox.showinfo("Límite alcanzado", "Solo puede comparar hasta 3 jugadores adicionales.")


    def remove_player_from_compare(self):
        """Elimina el jugador seleccionado de la lista de comparación"""
        selection = self.compare_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        # player_name_to_remove = self.compare_listbox.get(index) # Obtener nombre si es necesario para lógica más compleja
        self.compare_listbox.delete(index)

        # Eliminar de la lista de datos (self.compare_players)
        if 0 <= index < len(self.compare_players):
            self.compare_players.pop(index)

            # Actualizar el gráfico
            if self.current_player_info is not None:
                self.update_radar_chart()


    def on_season_selected(self, event):
        """Maneja la selección de una temporada"""
        # Actualizar la lista de jugadores con la nueva temporada
        selected_position_name = self.position_var.get()
        if selected_position_name:
            # Encontrar la clave de la posición seleccionada
            selected_position_key = None
            for key, value in self.positions.items():
                if value == selected_position_name:
                    selected_position_key = key
                    break

            if selected_position_key:
                # Recargar los datos con la nueva temporada
                self.load_player_data()
                # Actualizar la lista de jugadores
                self.update_players_list(selected_position_key)
        else: # Si no hay posición seleccionada, aún recargar datos y limpiar lista
            self.load_player_data()
            self.players_listbox_db.delete(0, tk.END) # Usar el listbox correcto


    def update_players_list(self, position_key):
        """Actualiza la lista de jugadores según la posición seleccionada"""
        if self.df_players is None:
            return

        # Limpiar la lista actual
        self.players_listbox_db.delete(0, tk.END) # Usar el listbox correcto

        try:
            # Filtrar jugadores por posición
            filtered_players = self.df_players[self.df_players['position_group'] == position_key]

            # Ordenar por algún criterio relevante (por ejemplo, valor de mercado)
            if 'market_value_in_eur' in filtered_players.columns:
                filtered_players = filtered_players.sort_values(by='market_value_in_eur', ascending=False)

            # Añadir jugadores a la listbox
            for _, player_row in filtered_players.iterrows(): # Renombrar player a player_row
                player_name = player_row.get('Player', 'Desconocido')
                self.players_listbox_db.insert(tk.END, player_name) # Usar el listbox correcto
        except Exception as e:
            messagebox.showerror("Error", f"Error al actualizar la lista de jugadores: {str(e)}")

    def on_search_key_release(self, event):
        """Maneja la búsqueda de jugadores mientras se escribe"""
        search_text = self.search_var_db.get().lower() # Usar la variable de búsqueda correcta

        if not search_text:
            # Si no hay texto de búsqueda, restaurar la lista según la posición seleccionada
            selected_position_name = self.position_var.get()
            if selected_position_name: # Solo actualizar si hay una posición seleccionada
                selected_position_key = next((key for key, value in self.positions.items() if value == selected_position_name), None)
                if selected_position_key:
                    self.update_players_list(selected_position_key)
            else: # Si no hay posición Y no hay búsqueda, limpiar la lista
                 self.players_listbox_db.delete(0, tk.END) # Usar el listbox correcto
            return

        # Limpiar la lista actual
        self.players_listbox_db.delete(0, tk.END) # Usar el listbox correcto

        if self.df_players is None:
            return

        try:
            # Filtrar jugadores que coincidan con la búsqueda (usando 'normalized_name')
            mask = self.df_players['normalized_name'].astype(str).str.contains(search_text, na=False)
            filtered_players = self.df_players[mask]


            # Añadir jugadores a la listbox
            for _, player_row in filtered_players.iterrows(): # Renombrar player a player_row
                player_name = player_row.get('Player', 'Desconocido')
                self.players_listbox_db.insert(tk.END, player_name) # Usar el listbox correcto
        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar jugadores: {str(e)}")

    def on_player_selected(self, event):
        """Maneja la selección de un jugador de la lista"""
        selection = self.players_listbox_db.curselection() # Usar el listbox correcto
        if not selection:
            return

        player_name = self.players_listbox_db.get(selection[0])

        if self.df_players is None:
            return

        try:
            # Buscar el jugador en el DataFrame
            player_data_series = self.df_players[self.df_players['Player'] == player_name] # Renombrar player_data a player_data_series

            if player_data_series.empty:
                return

            # Obtener los datos del jugador (es un Series)
            self.current_player_info = player_data_series.iloc[0] # Guardar como current_player_info

            # Mostrar los detalles del jugador
            self.show_player_details(self.current_player_info)
        except Exception as e:
            messagebox.showerror("Error", f"Error al mostrar detalles del jugador: {str(e)}")

    def show_player_details(self, player_info_series): # Renombrar player_info a player_info_series
        """Muestra los detalles del jugador seleccionado"""
        # Guardar referencia al jugador actual para comparaciones
        self.current_player_info = player_info_series # Ya se hace en on_player_selected, pero redundancia no daña

        # Habilitar el texto para edición
        self.details_text.config(state=tk.NORMAL)

        # Limpiar el texto actual
        self.details_text.delete("1.0", tk.END)

        # Función auxiliar para añadir detalles con estilo
        def add_detail(label, value, bold_label=False, is_score=False):
            if bold_label:
                self.details_text.insert(tk.END, label + ": ", ("bold_detail",))
            else:
                 self.details_text.insert(tk.END, label + ": ")

            if is_score: # Formato especial para la puntuación
                self.details_text.insert(tk.END, f"{value:.2f}/10\n", ("score_detail",))
            else:
                self.details_text.insert(tk.END, f"{value}\n")

        # Definir tags para el estilo del texto
        self.details_text.tag_configure("bold_detail", font=("Arial", 10, "bold"), foreground=self.colors["fg_white"])
        self.details_text.tag_configure("category_header", font=("Arial", 11, "bold"), foreground=self.colors["accent_color"], spacing1=5, spacing3=5) # spacing1 arriba, spacing3 abajo
        self.details_text.tag_configure("stat_label", font=("Arial", 9), foreground=self.colors["fg_light"]) # Para nombres de estadísticas
        self.details_text.tag_configure("stat_value", font=("Arial", 9, "bold"), foreground=self.colors["fg_white"]) # Para valores de estadísticas
        self.details_text.tag_configure("score_detail", font=("Arial", 10, "bold"), foreground=self.colors["green_accent"])


        add_detail("Nombre", player_info_series.get('Player', 'Desconocido'), bold_label=True)
        add_detail("Posición", player_info_series.get('position_group', 'Desconocida'))
        add_detail("Equipo", player_info_series.get('Squad', 'Desconocido'))
        add_detail("Liga", player_info_series.get('Comp', 'Desconocida'))
        add_detail("Temporada", player_info_series.get('Season', 'Desconocida'))


        if 'market_value_in_eur' in player_info_series and pd.notna(player_info_series['market_value_in_eur']):
            value_in_millions = player_info_series['market_value_in_eur'] / 1000000
            add_detail("Valor de mercado", f"{value_in_millions:.2f} millones €")

        puntuacion = calcular_ponderacion_estadisticas(player_info_series)/10
        add_detail("Puntuación", puntuacion, is_score=True)

        self.details_text.insert(tk.END, "\nEstadísticas completas:\n", ("category_header",))

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
            current_script_dir = os.path.dirname(__file__)
            project_root_dir = os.path.abspath(os.path.join(current_script_dir, "..", ".."))
            explanation_file_path = os.path.join(project_root_dir, "data", "fbref_stats_explained.json")

            with open(explanation_file_path, 'r', encoding='utf-8') as f:
                self.explicaciones_stats = json.load(f)
        except FileNotFoundError:
            self.explicaciones_stats = {}
            print(f"Advertencia: No se pudo cargar el archivo de explicaciones: {explanation_file_path}")
        except json.JSONDecodeError:
            self.explicaciones_stats = {}
            print(f"Advertencia: Error al decodificar el archivo JSON de explicaciones: {explanation_file_path}")
        except Exception as e:
            self.explicaciones_stats = {}
            print(f"Error inesperado al cargar explicaciones: {e} desde {explanation_file_path if 'explanation_file_path' in locals() else 'ruta desconocida'}")

            with open(explanation_file_path, 'r', encoding='utf-8') as f:
                self.explicaciones_stats = json.load(f)
        except Exception as e:
            self.explicaciones_stats = {}
            print(f"Error al cargar explicaciones: {e} desde {explanation_file_path if 'explanation_file_path' in locals() else 'ruta desconocida'}")

        for categoria, stats_list in categorias.items(): # Renombrar stats a stats_list
            self.details_text.insert(tk.END, f"\n{categoria.upper()}:\n", ("category_header",))
            for stat_key in stats_list: # Renombrar stat a stat_key
                if stat_key in player_info_series and not pd.isna(player_info_series[stat_key]):
                    valor = player_info_series[stat_key]
                    # Formatear valores numéricos
                    if isinstance(valor, (int, float)):
                        if stat_key.endswith('%'):
                            valor_str = f"{valor:.1f}%"
                        else: # Otros números, formatear a 2 decimales si es float
                            valor_str = f"{valor:.2f}" if isinstance(valor, float) else f"{valor}"
                    else:
                        valor_str = str(valor)

                    safe_stat_key = re.sub(r'\W+', '_', stat_key)
                    tag_name = f"stat_{safe_stat_key}"

                    self.details_text.insert(tk.END, f"  • {stat_key}: ", (tag_name, "stat_label")) # Usar "stat_label"
                    self.details_text.insert(tk.END, f"{valor_str}\n", ("stat_value",)) # Usar "stat_value"

                    if stat_key in self.explicaciones_stats:
                        self.details_text.tag_bind(tag_name, "<Enter>",
                                                lambda event, s=stat_key: self.show_stat_tooltip(event, s))
                        self.details_text.tag_bind(tag_name, "<Leave>", self.hide_stat_tooltip)

        self.details_text.config(state=tk.DISABLED)

        self.update_radar_chart()


    def show_stat_tooltip(self, event, stat_key_tooltip): # Renombrar stat a stat_key_tooltip
        """Muestra un tooltip con la explicación de la estadística"""
        # Destruir tooltip existente si hay uno
        self.hide_stat_tooltip(None)

        # Obtener la explicación de la estadística
        if stat_key_tooltip in self.explicaciones_stats:
            explicacion = self.explicaciones_stats[stat_key_tooltip]

            # Crear ventana para el tooltip
            # Obtener coordenadas relativas al widget Text
            bbox = self.details_text.bbox(tk.CURRENT)
            if not bbox: return # No hay nada bajo el cursor

            x_rel, y_rel, _, _ = bbox
            # Convertir a coordenadas de pantalla
            x_root = self.details_text.winfo_rootx()
            y_root = self.details_text.winfo_rooty()


            self.tooltip_window = tk.Toplevel(self.master) # Asegurar que es hijo de la ventana principal
            self.tooltip_window.wm_overrideredirect(True) # Sin decoraciones de ventana
            # Posicionar tooltip cuidadosamente, asegurar que está en pantalla
            final_x = x_root + x_rel + 20 # Offset del cursor
            final_y = y_root + y_rel + 20


            # Crear una etiqueta temporal para obtener dimensiones aproximadas del tooltip
            # Esto ayuda a posicionarlo para que no se salga de la pantalla
            dummy_label = tk.Label(self.tooltip_window, text=explicacion, wraplength=300, font=("Arial", 9))
            dummy_label.pack()
            self.tooltip_window.update_idletasks() # Procesar geometría
            tip_width = self.tooltip_window.winfo_width()
            tip_height = self.tooltip_window.winfo_height()
            dummy_label.destroy() # Eliminar la etiqueta temporal


            # Ajustar posición si se sale de la pantalla
            screen_width = self.master.winfo_screenwidth()
            screen_height = self.master.winfo_screenheight()

            if final_x + tip_width > screen_width:
                final_x = screen_width - tip_width - 10 # Mover a la izquierda
            if final_x < 0 : final_x = 10 # Evitar que se salga por la izquierda

            if final_y + tip_height > screen_height:
                final_y = y_root + y_rel - tip_height - 10 # Mostrar arriba si está muy abajo
            if final_y < 0 : final_y = 10 # Evitar que se salga por arriba


            self.tooltip_window.wm_geometry(f"+{int(final_x)}+{int(final_y)}") # Usar int para geometría
            self.tooltip_window.configure(background=self.colors["tooltip_bg"])


            # Crear etiqueta con la explicación
            label = tk.Label(self.tooltip_window, text=explicacion, justify=tk.LEFT,
                           background=self.colors["tooltip_bg"], foreground=self.colors["fg_light"],
                           relief=tk.SOLID, # Usar SOLID para el borde principal
                           borderwidth=1, # Grosor del borde principal
                           wraplength=300, font=("Arial", 9),
                           # Usar highlightbackground/color para el borde en algunos temas de Tk
                           highlightbackground=self.colors["tooltip_border"],
                           highlightcolor=self.colors["tooltip_border"],
                           highlightthickness=1, # Esto podría ser el borde que se ve
                           padx=5, pady=5)
            label.pack()


    def hide_stat_tooltip(self, event):
        """Oculta el tooltip"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def update_radar_chart(self):
        """Actualiza el gráfico de radar para comparar jugadores"""
        # Limpiar el frame del gráfico, excepto el placeholder si existe
        for widget in self.chart_frame.winfo_children():
            if widget != self.chart_placeholder:
                widget.destroy()


        # Si no hay jugador seleccionado, mostrar mensaje y asegurarse que el placeholder está visible
        if self.current_player_info is None:
            if not self.chart_placeholder.winfo_ismapped(): # Mostrar placeholder si no está visible
                 self.chart_placeholder.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            return

        # Ocultar placeholder si vamos a dibujar un gráfico
        if self.chart_placeholder.winfo_ismapped():
            self.chart_placeholder.pack_forget()


        # Definir estadísticas para el gráfico según la posición
        position = self.current_player_info.get('position_group', '')

        stats_by_position = {
            "GK": {"Save%": "% Paradas", "CS%": "% Porterías 0", "PSxG/SoT": "Calidad Paradas", "Stp%": "% Salidas Exitosas", "Total - Cmp%": "Precisión Pases", "Long - Cmp%": "Prec. Pases Largos"},
            "Defender": {"Tkl%": "% Entradas Exitosas", "Won%": "% Duelos Aéreos Gan.", "Total - Cmp%": "Precisión Pases", "Long - Cmp%": "Prec. Pases Largos", "Succ%": "% Regates Exitosos", "Blocks": "Bloqueos Tot."},
            "Defensive-Midfielders": {"Tkl%": "% Entradas Exitosas", "Total - Cmp%": "Precisión Pases", "Won%": "% Duelos Aéreos Gan.", "Succ%": "% Regates Exitosos", "Medium - Cmp%": "Prec. Pases Medios", "Int_y": "Intercepciones"},
            "Central Midfielders": {"Total - Cmp%": "Precisión Pases", "Medium - Cmp%": "Prec. Pases Medios", "Long - Cmp%": "Prec. Pases Largos", "Succ%": "% Regates Exitosos", "KP": "Pases Clave", "SoT%": "% Tiros Puerta"},
            "Attacking Midfielders": {"SoT%": "% Tiros Puerta", "G/Sh": "Efic. Tiro", "Succ%": "% Regates Exitosos", "Total - Cmp%": "Precisión Pases", "KP": "Pases Clave", "Ast": "Asistencias"},
            "Wing-Back": {"Total - Cmp%": "Precisión Pases", "Succ%": "% Regates Exitosos", "Tkl%": "% Entradas Exitosas", "CrsPA": "Centros", "Won%": "% Duelos Aéreos Gan.", "Carries - PrgC": "Progresión Conducción"},
            "Forwards": {"G/Sh": "Efic. Tiro", "SoT%": "% Tiros Puerta", "G/SoT": "Goles/Tiro Puerta", "Succ%": "% Regates Exitosos", "Won%": "% Duelos Aéreos Gan.", "npxG": "xG (sin penaltis)"}
        }

        stats_to_use = stats_by_position.get(position, {
            "SoT%": "% Tiros Puerta", "G/Sh": "Efic. Tiro", "Total - Cmp%": "Precisión Pases",
            "Succ%": "% Regates Exitosos", "Won%": "% Duelos Aéreos Gan.", "Tkl%": "% Entradas Exitosas"
        })

        stats_keys = list(stats_to_use.keys())
        stats_labels = list(stats_to_use.values())

        all_players_data_for_chart = [self.current_player_info] + self.compare_players
        all_values_for_norm = {stat: [] for stat in stats_keys} # Renombrar all_values a all_values_for_norm

        for player_data_series in all_players_data_for_chart: # Renombrar player a player_data_series
            for stat_key_chart in stats_keys: # Renombrar stat a stat_key_chart
                if stat_key_chart in player_data_series and pd.notna(player_data_series[stat_key_chart]):
                    try:
                        all_values_for_norm[stat_key_chart].append(float(player_data_series[stat_key_chart]))
                    except ValueError:
                        all_values_for_norm[stat_key_chart].append(0.0) # Si no se puede convertir a float
                        print(f"Advertencia: No se pudo convertir {player_data_series[stat_key_chart]} a float para {stat_key_chart}")
                else:
                    all_values_for_norm[stat_key_chart].append(0.0) # Valor por defecto si falta o es NaN


        # Crear figura
        fig = Figure(figsize=(6, 5.5), facecolor=self.colors["bg_dark_widget"], dpi=100) # Tamaño y dpi ajustados
        ax = fig.add_subplot(111, polar=True, facecolor=self.colors["bg_dark_entry"]) # Color de fondo del área polar


        # Número de variables
        N = len(stats_keys)

        # Ángulos para el gráfico (en radianes)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # Cerrar el polígono

        # Configurar el gráfico
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(stats_labels, color=self.colors["fg_light"], fontdict={'fontsize': 9}) # Fuente más pequeña para etiquetas
        ax.tick_params(axis='x', pad=10) # Separar etiquetas del eje

        ax.set_ylim(0, 100) # Rango de normalización
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels([f"{val}%" for val in [20, 40, 60, 80, 100]], color=self.colors["fg_light"], fontsize=8) # Etiquetas de Y más pequeñas
        ax.grid(True, color=self.colors["fg_light"], linestyle='--', linewidth=0.5, alpha=0.3) # Rejilla más sutil
        ax.spines['polar'].set_color(self.colors["fg_light"]) # Color del círculo exterior
        ax.spines['polar'].set_linewidth(0.5)


        # Añadir jugadores
        # Colores para los gráficos de radar (principal + comparaciones)
        plot_colors = [self.colors["accent_color"]] + ['#FFCA28', '#66BB6A', '#EF5350'][:len(self.compare_players)]


        for i, player_data_series in enumerate(all_players_data_for_chart): # Iterar sobre todos los jugadores para el gráfico
            if i > 3 : break # Limitar a principal + 3 comparaciones (total 4 líneas)

            player_values_normalized = [] # Renombrar main_player_values a player_values_normalized
            for stat_key_chart in stats_keys: # Renombrar stat a stat_key_chart
                value = 0.0
                if stat_key_chart in player_data_series and pd.notna(player_data_series[stat_key_chart]):
                    try:
                        value = float(player_data_series[stat_key_chart])
                    except ValueError:
                        pass # value permanece 0.0

                # Lógica de normalización (puede necesitar ajuste específico por estadística)
                # Aquí asumimos que los % ya están en escala 0-100. Otros se normalizan relativos al máximo.
                normalized_value = 0.0
                if stat_key_chart.endswith('%'): # Si es un porcentaje, usar directamente (asumiendo 0-100)
                    normalized_value = value
                elif stat_key_chart in ["G/Sh", "G/SoT", "PSxG/SoT"]: # Ratios que pueden ser < 1 o > 1
                    # Escalar estos ratios. Ej: si G/Sh máx esperado es 0.3, entonces (value / 0.3) * 100
                    # Esto es una simplificación, idealmente se usarían percentiles o una escala fija.
                    # Para este ejemplo, multiplicamos por 100 y limitamos a 100.
                    normalized_value = min(100, value * 100 if stat_key_chart in ["G/Sh", "G/SoT"] else value + 50 if stat_key_chart == "PSxG/SoT" else value) # PSxG/SoT puede ser negativo
                else: # Para valores absolutos, normalizar respecto al máximo del grupo
                    max_val_for_stat = max(all_values_for_norm[stat_key_chart]) if all_values_for_norm[stat_key_chart] else 1
                    normalized_value = (value / max_val_for_stat) * 100 if max_val_for_stat > 0 else 0

                player_values_normalized.append(min(100, max(0, normalized_value))) # Asegurar que está entre 0 y 100


            player_values_normalized += player_values_normalized[:1]  # Cerrar el polígono
            ax.plot(angles, player_values_normalized, linewidth=1.5, linestyle='solid', label=player_data_series['Player'], color=plot_colors[i % len(plot_colors)]) # Usar módulo para colores si hay más jugadores que colores
            ax.fill(angles, player_values_normalized, alpha=0.25, color=plot_colors[i % len(plot_colors)])


        ax.set_title("Comparación de Jugadores (Valores Normalizados %)", color=self.colors["fg_light"], fontsize=12, pad=20) # Padding aumentado para el título

        # Leyenda debajo del gráfico
        legend = ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.25), ncol=min(len(all_players_data_for_chart), 4), frameon=False)
        for text in legend.get_texts():
            text.set_color(self.colors["fg_light"])
            text.set_fontsize(9) # Fuente de leyenda más pequeña

        fig.tight_layout(pad=1.5) # Ajustar layout para evitar superposiciones

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.configure(background=self.colors["bg_dark_widget"]) # Fondo del widget canvas
        canvas_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)


        # Estilo de la barra de herramientas
        toolbar_frame = ttk.Frame(self.chart_frame) # Usar un ttk.Frame para la barra de herramientas
        toolbar_frame.pack(fill=tk.X)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        toolbar.configure(background=self.colors["bg_dark_widget"]) # Fondo de la barra de herramientas
        # Estilizar los botones de la barra de herramientas (puede ser complicado debido a cómo se crean internamente)
        for child in toolbar.winfo_children():
            child.configure(background=self.colors["bg_dark_widget"]) # Fondo para todos los hijos
            if isinstance(child, (tk.Button, ttk.Button)): # Estilizar botones tk y ttk
                 if isinstance(child, tk.Button): # Específico para tk.Button
                     child.configure(foreground=self.colors["fg_light"], relief=tk.FLAT, borderwidth=1, highlightthickness=0,
                                     activebackground=self.colors["accent_secondary"], activeforeground=self.colors["fg_white"])
