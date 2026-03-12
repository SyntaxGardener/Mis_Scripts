#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
import os
import subprocess
import sys

# ============================================
# CLASE PERSONALIZADA DEL TOOLBAR
# ============================================
class ToolbarMinimo(NavigationToolbar2Tk):
    """Toolbar de matplotlib - versión mínima"""
    
    def __init__(self, canvas, window, nombre_base, app):
        self.nombre_base = nombre_base
        self.app = app
        super().__init__(canvas, window)
    
    def save_figure(self, *args):
        """Sobrescribe el método de guardado"""
        from matplotlib.backends._backend_tk import SaveFigureTk
        
        filetypes = self.canvas.get_supported_filetypes_grouped()
        tk_filetypes = [
            (name, "*.%s" % ext) for name, exts in sorted(filetypes.items()) for ext in exts
        ]
        
        nombre_sugerido = f"{self.nombre_base}.png"
        
        filename = filedialog.asksaveasfilename(
            title="Guardar gráfico como",
            initialfile=nombre_sugerido,
            filetypes=tk_filetypes + [("Todos los archivos", "*.*")]
        )
        
        if filename:
            try:
                self.canvas.figure.savefig(filename)
                self.canvas.draw_idle()
                
                respuesta = tk.messagebox.askyesno(
                    "Guardado correcto", 
                    f"✅ Gráfico guardado como:\n{filename}\n\n¿Quieres abrir la carpeta?"
                )
                
                if respuesta:
                    carpeta = os.path.dirname(filename)
                    if os.name == 'nt':
                        os.startfile(carpeta)
                    elif os.name == 'posix':
                        subprocess.Popen(['open', carpeta] if sys.platform == 'darwin' else ['xdg-open', carpeta])
                        
            except Exception as e:
                tk.messagebox.showerror("Error", f"Error al guardar:\n{str(e)}")

class AplicacionGraficos:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Generador de Gráficos")
        
        # Variables
        self.df_evolucion = None
        self.df_ingresos = None
        self.df_gastos = None
        self.archivo_actual = None
        self.nombre_base = None
        
        self.setup_ui()
        self.mostrar_pantalla_bienvenida()
        self.centrar_ventana()
    
    def centrar_ventana(self):
        """Centra la ventana en la pantalla"""
        self.root.update_idletasks()
        ancho_ventana = 1200
        alto_ventana = 750
        ancho_pantalla = self.root.winfo_screenwidth()
        
        posicion_x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        posicion_y = 0
        
        self.root.geometry(f"{ancho_ventana}x{alto_ventana}+{posicion_x}+{posicion_y}")
    
    def setup_ui(self):
        """Configura la interfaz"""
        
        # ========== BARRA SUPERIOR ==========
        toolbar = tk.Frame(self.root, bg='#3498db', height=60)
        toolbar.pack(fill='x')
        toolbar.pack_propagate(False)
        
        self.btn_cargar = tk.Button(toolbar, 
                                    text="📂 CARGAR ARCHIVO EXCEL",
                                    command=self.abrir_excel,
                                    font=('Arial', 12, 'bold'),
                                    bg='white',
                                    fg='#3498db',
                                    padx=20,
                                    pady=8,
                                    cursor='hand2')
        self.btn_cargar.pack(side='left', padx=20, pady=10)
        
        self.lbl_archivo = tk.Label(toolbar, 
                                    text="📁 Ningún archivo cargado", 
                                    bg='#3498db',
                                    fg='white',
                                    font=('Arial', 11))
        self.lbl_archivo.pack(side='left', padx=10)
        
        btn_ayuda = tk.Button(toolbar,
                             text="❓ Ayuda",
                             command=self.mostrar_ayuda_botones,
                             bg='#f39c12',
                             fg='white',
                             font=('Arial', 10),
                             padx=10,
                             cursor='hand2')
        btn_ayuda.pack(side='right', padx=10)
        
        # ========== NOTEBOOK (PESTAÑAS) ==========
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Crear pestañas
        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)
        self.tab3 = ttk.Frame(self.notebook)
        self.tab4 = ttk.Frame(self.notebook)
        self.tab5 = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab1, text="📈 Evolución Anual")
        self.notebook.add(self.tab2, text="💰 Ingresos")
        self.notebook.add(self.tab3, text="💸 Gastos")
        self.notebook.add(self.tab4, text="⚖️ Comparativa Saldos")
        self.notebook.add(self.tab5, text="📋 Datos")
        
        # ========== BARRA DE ESTADO ==========
        self.status_bar = tk.Label(self.root, text="✅ Esperando archivo Excel...", 
                                   bd=1, relief='sunken', anchor='w')
        self.status_bar.pack(fill='x', side='bottom', padx=10, pady=5)
    
    def mostrar_ayuda_botones(self):
        """Muestra explicación de los botones"""
        ayuda = """🔍 EXPLICACIÓN DE LOS BOTONES:

🏠 Home - Vista original
⬅️ ➡️ Back/Forward - Navegar entre vistas (solo si has hecho zoom)
🔍 Zoom - Selecciona un área para ampliar
🔧 Pan - Mueve el gráfico
⚙️ Subplots - Configurar (no usado)
💾 Guardar - Guarda el gráfico como PNG

✅ El único botón que necesitas es GUARDAR
Los demás son opcionales para explorar los datos
"""
        messagebox.showinfo("Ayuda - Botones", ayuda)
    
    def mostrar_pantalla_bienvenida(self):
        """Muestra mensaje de bienvenida"""
        mensaje = "📂 Carga un archivo Excel para comenzar\n\nHaz clic en el botón azul 'CARGAR ARCHIVO EXCEL'"
        
        for tab in [self.tab1, self.tab2, self.tab3, self.tab4, self.tab5]:
            for widget in tab.winfo_children():
                widget.destroy()
            
            label = tk.Label(tab, text=mensaje, font=('Arial', 16), fg='#7f8c8d')
            label.pack(expand=True)
    
    def abrir_excel(self):
        """Abre un archivo Excel"""
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo Excel",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("Todos", "*.*")]
        )
        
        if archivo:
            self.archivo_actual = archivo
            nombre_completo = os.path.basename(archivo)
            self.nombre_base = os.path.splitext(nombre_completo)[0]
            
            self.lbl_archivo.config(text=f"📁 {nombre_completo}")
            self.status_bar.config(text=f"📂 Cargando: {nombre_completo}...")
            self.btn_cargar.config(text="⏳ CARGANDO...", state='disabled')
            self.root.update()
            
            try:
                self.cargar_datos_excel(archivo)
                self.status_bar.config(text=f"✅ {nombre_completo} cargado correctamente")
                self.btn_cargar.config(text="📂 CARGAR OTRO ARCHIVO", state='normal')
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar:\n{str(e)}")
                self.status_bar.config(text="❌ Error al cargar archivo")
                self.btn_cargar.config(text="📂 CARGAR ARCHIVO EXCEL", state='normal')
                self.mostrar_pantalla_bienvenida()
    
    def cargar_datos_excel(self, archivo):
        """Carga datos del Excel"""
        xl = pd.ExcelFile(archivo)
        
        hojas_encontradas = []
        
        self.df_evolucion = None
        self.df_ingresos = None
        self.df_gastos = None
        
        for hoja in xl.sheet_names:
            if any(p in hoja.lower() for p in ['resumen', 'evolucion', 'anual']):
                df = pd.read_excel(archivo, sheet_name=hoja)
                self.procesar_evolucion(df)
                hojas_encontradas.append(f"Evolución: {hoja}")
            
            if any(p in hoja.lower() for p in ['ingreso', 'fuentes']):
                df = pd.read_excel(archivo, sheet_name=hoja)
                self.procesar_ingresos(df)
                hojas_encontradas.append(f"Ingresos: {hoja}")
            
            if any(p in hoja.lower() for p in ['gasto', 'partidas']):
                df = pd.read_excel(archivo, sheet_name=hoja)
                self.procesar_gastos(df)
                hojas_encontradas.append(f"Gastos: {hoja}")
        
        if self.df_evolucion is None and self.df_ingresos is None and self.df_gastos is None:
            messagebox.showerror("Error", 
                "No se encontraron hojas con los formatos esperados.\n\n"
                "El Excel debe contener hojas llamadas:\n"
                "- 'Resumen', 'Evolución' o 'Anual'\n"
                "- 'Ingresos' o 'Fuentes'\n"
                "- 'Gastos' o 'Partidas'")
            self.mostrar_pantalla_bienvenida()
            return
        
        mensaje = "Hojas cargadas:\n" + "\n".join(hojas_encontradas)
        
        if self.df_gastos is not None:
            mensaje += f"\n\n✅ {len(self.df_gastos)} partidas de gasto cargadas"
        
        messagebox.showinfo("Carga completada", mensaje)
        
        if self.df_evolucion is None:
            self.df_evolucion = pd.DataFrame(columns=['Año', 'Ingresos', 'Gastos', 'Saldo_Inicial', 'Saldo_Final'])
            messagebox.showwarning("Aviso", "No se encontró hoja de evolución. Algunos gráficos pueden estar vacíos.")
        
        if self.df_ingresos is None:
            self.df_ingresos = pd.DataFrame(columns=['Fuente', 'Importe'])
            messagebox.showwarning("Aviso", "No se encontró hoja de ingresos. Algunos gráficos pueden estar vacíos.")
        
        if self.df_gastos is None:
            self.df_gastos = pd.DataFrame(columns=['Partida', 'Importe'])
            messagebox.showwarning("Aviso", "No se encontró hoja de gastos. Algunos gráficos pueden estar vacíos.")
        
        self.actualizar_todos_graficos()
    
    def procesar_evolucion(self, df):
        """Procesa evolución"""
        try:
            años = []
            for col in df.columns:
                try:
                    if str(col).isdigit() or (isinstance(col, (int, float)) and col > 2000):
                        años.append(col)
                except:
                    pass
            
            if años:
                datos = []
                for año in años:
                    ing = df[df.iloc[:, 0].astype(str).str.contains('ingreso', case=False, na=False)]
                    gas = df[df.iloc[:, 0].astype(str).str.contains('gasto', case=False, na=False)]
                    s_ini = df[df.iloc[:, 0].astype(str).str.contains('saldo.*inicial', case=False, na=False)]
                    s_fin = df[df.iloc[:, 0].astype(str).str.contains('saldo.*final', case=False, na=False)]
                    
                    datos.append({
                        'Año': int(año),
                        'Ingresos': float(ing[año].values[0]) if not ing.empty else 0,
                        'Gastos': float(gas[año].values[0]) if not gas.empty else 0,
                        'Saldo_Inicial': float(s_ini[año].values[0]) if not s_ini.empty else 0,
                        'Saldo_Final': float(s_fin[año].values[0]) if not s_fin.empty else 0
                    })
                self.df_evolucion = pd.DataFrame(datos)
        except Exception as e:
            print(f"Error en evolución: {e}")
    
    def procesar_ingresos(self, df):
        """Procesa ingresos"""
        try:
            self.df_ingresos = df.iloc[:, :2].copy()
            self.df_ingresos.columns = ['Fuente', 'Importe']
            self.df_ingresos = self.df_ingresos.dropna()
            self.df_ingresos['Importe'] = pd.to_numeric(self.df_ingresos['Importe'], errors='coerce')
            self.df_ingresos = self.df_ingresos[self.df_ingresos['Importe'] > 0]
        except Exception as e:
            print(f"Error en ingresos: {e}")
    
    def procesar_gastos(self, df):
        """Procesa gastos"""
        try:
            self.df_gastos = df.iloc[:, :2].copy()
            self.df_gastos.columns = ['Partida', 'Importe']
            self.df_gastos = self.df_gastos.dropna()
            self.df_gastos['Importe'] = pd.to_numeric(self.df_gastos['Importe'], errors='coerce')
            self.df_gastos = self.df_gastos[self.df_gastos['Importe'] > 0]
            self.df_gastos = self.df_gastos.sort_values('Importe', ascending=False)
        except Exception as e:
            print(f"Error en gastos: {e}")
    
    def actualizar_todos_graficos(self):
        """Actualiza todos los gráficos"""
        self.grafico_evolucion()
        self.grafico_ingresos()
        self.grafico_gastos()
        self.grafico_comparativo()
        self.mostrar_datos_tabla()
    
    def grafico_evolucion(self):
        """Gráfico de evolución anual"""
        for widget in self.tab1.winfo_children():
            widget.destroy()
        
        if self.df_evolucion is None or len(self.df_evolucion) == 0:
            tk.Label(self.tab1, text="No hay datos de evolución", font=('Arial', 14)).pack(expand=True)
            return
        
        fig, ax = plt.subplots(figsize=(11, 6.5))
        x = np.arange(len(self.df_evolucion))
        ancho = 0.35
        
        barras_ing = ax.bar(x - ancho/2, self.df_evolucion['Ingresos'], ancho, 
                            label='Ingresos', color='#2E86C1', alpha=0.8)
        barras_gas = ax.bar(x + ancho/2, self.df_evolucion['Gastos'], ancho, 
                            label='Gastos', color='#E74C3C', alpha=0.8)
        
        # Cantidades en barras
        for i, (barra, valor) in enumerate(zip(barras_ing, self.df_evolucion['Ingresos'])):
            if valor > 0:
                ax.text(barra.get_x() + barra.get_width()/2, valor/2,
                       f'{valor:,.0f}€', ha='center', va='center',
                       fontsize=9, fontweight='bold', color='white', rotation=90)
        
        for i, (barra, valor) in enumerate(zip(barras_gas, self.df_evolucion['Gastos'])):
            if valor > 0:
                ax.text(barra.get_x() + barra.get_width()/2, valor/2,
                       f'{valor:,.0f}€', ha='center', va='center',
                       fontsize=9, fontweight='bold', color='white', rotation=90)
        
        ax2 = ax.twinx()
        puntos_saldo = ax2.plot(x, self.df_evolucion['Saldo_Final'], 'g-^', 
                               linewidth=3, markersize=10, label='Saldo final')
        
        for i, valor in enumerate(self.df_evolucion['Saldo_Final']):
            if valor > 0:
                ax2.text(i, valor + max(self.df_evolucion['Saldo_Final'])*0.03,
                        f'{valor:,.0f}€', ha='center', va='bottom',
                        fontsize=9, fontweight='bold', color='darkgreen')
        
        ax.set_xlabel('Año', fontsize=11)
        ax.set_ylabel('Ingresos / Gastos (€)', fontsize=11)
        ax2.set_ylabel('Saldo (€)', fontsize=11)
        ax.set_title('Evolución Anual de la Cuenta', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(self.df_evolucion['Año'])
        ax.grid(True, alpha=0.3)
        
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.tab1)
        toolbar = ToolbarMinimo(canvas, self.tab1, self.nombre_base, self)
        toolbar.update()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def grafico_ingresos(self):
        """Gráfico de ingresos - TODAS las cantidades con porcentaje"""
        for widget in self.tab2.winfo_children():
            widget.destroy()
        
        if self.df_ingresos is None or len(self.df_ingresos) == 0:
            tk.Label(self.tab2, text="No hay datos de ingresos", font=('Arial', 14)).pack(expand=True)
            return
        
        fig, ax = plt.subplots(figsize=(11, 6.5))
        df_ord = self.df_ingresos.sort_values('Importe', ascending=True)
        total = df_ord['Importe'].sum()
        
        y_pos = np.arange(len(df_ord))
        colores = plt.cm.Blues(np.linspace(0.3, 0.9, len(df_ord)))
        
        barras = ax.barh(y_pos, df_ord['Importe'], color=colores)
        
        # AÑADIR CANTIDADES CON PORCENTAJE EN TODAS LAS BARRAS
        max_val = df_ord['Importe'].max()
        for i, (barra, valor, fuente) in enumerate(zip(barras, df_ord['Importe'], df_ord['Fuente'])):
            porcentaje = (valor / total) * 100
            texto = f'{valor:,.0f}€ ({porcentaje:.1f}%)'
            
            if valor > max_val * 0.15:  # Barra grande - texto dentro en blanco
                ax.text(valor/2, i, texto, 
                       ha='center', va='center', fontsize=9, fontweight='bold', color='white')
            else:  # Barra pequeña - texto fuera en negro
                ax.text(valor + max_val*0.02, i, texto, 
                       va='center', fontsize=9, fontweight='bold', color='black')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df_ord['Fuente'], fontsize=10)
        ax.set_xlabel('Importe (€)', fontsize=11)
        ax.set_title(f'Ingresos por Fuente - Total: {total:,.0f}€', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        ax.set_xlim(0, max_val * 1.35)  # Más espacio para textos largos
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.tab2)
        toolbar = ToolbarMinimo(canvas, self.tab2, self.nombre_base, self)
        toolbar.update()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def grafico_gastos(self):
        """Gráfico de gastos"""
        for widget in self.tab3.winfo_children():
            widget.destroy()
        
        if self.df_gastos is None or len(self.df_gastos) == 0:
            tk.Label(self.tab3, text="No hay datos de gastos", font=('Arial', 14)).pack(expand=True)
            return
        
        canvas_frame = tk.Frame(self.tab3)
        canvas_frame.pack(fill='both', expand=True)
        
        canvas_scroll = tk.Canvas(canvas_frame)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas_scroll.yview)
        scrollable_frame = tk.Frame(canvas_scroll)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all")))
        canvas_scroll.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)
        
        fig, ax = plt.subplots(figsize=(12, max(5.5, len(self.df_gastos) * 0.28)))
        df_ord = self.df_gastos.sort_values('Importe', ascending=True)
        total = df_ord['Importe'].sum()
        
        y_pos = np.arange(len(df_ord))
        colores = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(df_ord)))
        
        barras = ax.barh(y_pos, df_ord['Importe'], color=colores)
        
        max_val = df_ord['Importe'].max()
        for i, (barra, valor, partida) in enumerate(zip(barras, df_ord['Importe'], df_ord['Partida'])):
            porcentaje = (valor / total) * 100
            ax.text(valor + max_val*0.02, i, f'{valor:,.0f}€ ({porcentaje:.1f}%)', 
                   va='center', fontsize=9, fontweight='bold', color='black')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df_ord['Partida'], fontsize=9)
        ax.set_xlabel('Importe (€)', fontsize=11)
        ax.set_title(f'Todas las partidas de gasto - Total: {total:,.0f}€', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        ax.set_xlim(0, max_val * 1.35)
        
        plt.tight_layout()
        
        canvas_plot = FigureCanvasTkAgg(fig, scrollable_frame)
        toolbar = ToolbarMinimo(canvas_plot, scrollable_frame, self.nombre_base, self)
        toolbar.update()
        canvas_plot.get_tk_widget().pack()
        
        canvas_scroll.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def grafico_comparativo(self):
        """Gráfico comparativo de saldos"""
        for widget in self.tab4.winfo_children():
            widget.destroy()
        
        if self.df_evolucion is None or len(self.df_evolucion) == 0:
            tk.Label(self.tab4, text="No hay datos de saldos", font=('Arial', 14)).pack(expand=True)
            return
        
        fig, ax = plt.subplots(figsize=(11, 6.5))
        x = np.arange(len(self.df_evolucion))
        ancho = 0.35
        
        barras_ini = ax.bar(x - ancho/2, self.df_evolucion['Saldo_Inicial'], ancho, 
                           label='Saldo Inicial', color='#3498db', alpha=0.7)
        barras_fin = ax.bar(x + ancho/2, self.df_evolucion['Saldo_Final'], ancho, 
                           label='Saldo Final', color='#2ecc71', alpha=0.7)
        
        # Cantidades en barras
        for i, (barra, valor) in enumerate(zip(barras_ini, self.df_evolucion['Saldo_Inicial'])):
            if valor > 0:
                ax.text(barra.get_x() + barra.get_width()/2, valor/2,
                       f'{valor:,.0f}€', ha='center', va='center',
                       fontsize=9, fontweight='bold', color='white', rotation=90)
        
        for i, (barra, valor) in enumerate(zip(barras_fin, self.df_evolucion['Saldo_Final'])):
            if valor > 0:
                ax.text(barra.get_x() + barra.get_width()/2, valor/2,
                       f'{valor:,.0f}€', ha='center', va='center',
                       fontsize=9, fontweight='bold', color='white', rotation=90)
        
        max_saldo = max(self.df_evolucion['Saldo_Final'].max(), self.df_evolucion['Saldo_Inicial'].max())
        for i, (ini, fin) in enumerate(zip(self.df_evolucion['Saldo_Inicial'], 
                                           self.df_evolucion['Saldo_Final'])):
            ax.plot([i - ancho/2, i + ancho/2], [ini, fin], 'k--', alpha=0.5)
            diff = fin - ini
            color = '#27ae60' if diff > 0 else '#e74c3c'
            ax.text(i, max(ini, fin) + max_saldo*0.03,
                   f'{diff:+,.0f}€', ha='center', fontsize=10, fontweight='bold',
                   color=color, bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        ax.set_xlabel('Año', fontsize=11)
        ax.set_ylabel('Saldo (€)', fontsize=11)
        ax.set_title('Comparativa: Saldo Inicial vs Saldo Final', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(self.df_evolucion['Año'])
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, self.tab4)
        toolbar = ToolbarMinimo(canvas, self.tab4, self.nombre_base, self)
        toolbar.update()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def mostrar_datos_tabla(self):
        """Muestra datos en tabla"""
        for widget in self.tab5.winfo_children():
            widget.destroy()
        
        inner = ttk.Notebook(self.tab5)
        inner.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Pestaña Gastos
        tab_gas = ttk.Frame(inner)
        inner.add(tab_gas, text=f"Gastos ({len(self.df_gastos) if self.df_gastos is not None else 0} partidas)")
        
        if self.df_gastos is not None and len(self.df_gastos) > 0:
            frame = tk.Frame(tab_gas)
            frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            tree = ttk.Treeview(frame, columns=['Partida', 'Importe'], show='headings', height=20)
            vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            
            tree.heading('Partida', text='Partida')
            tree.heading('Importe', text='Importe (€)')
            tree.column('Partida', width=500)
            tree.column('Importe', width=150, anchor='e')
            
            for _, row in self.df_gastos.iterrows():
                tree.insert('', 'end', values=[row['Partida'], f"{row['Importe']:,.0f}€"])
            
            tree.grid(row=0, column=0, sticky='nsew')
            vsb.grid(row=0, column=1, sticky='ns')
            hsb.grid(row=1, column=0, sticky='ew')
            
            frame.grid_rowconfigure(0, weight=1)
            frame.grid_columnconfigure(0, weight=1)
            
            total = self.df_gastos['Importe'].sum()
            tk.Label(tab_gas, text=f"TOTAL GASTOS: {total:,.0f}€", 
                    font=('Arial', 12, 'bold'), fg='#27ae60').pack(pady=5)
        else:
            tk.Label(tab_gas, text="No hay datos de gastos", font=('Arial', 12)).pack(expand=True)
        
        # Pestaña Evolución
        tab_evo = ttk.Frame(inner)
        inner.add(tab_evo, text="Evolución")
        if self.df_evolucion is not None and len(self.df_evolucion) > 0:
            self.crear_tabla_simple(tab_evo, self.df_evolucion)
        else:
            tk.Label(tab_evo, text="No hay datos de evolución", font=('Arial', 12)).pack(expand=True)
        
        # Pestaña Ingresos
        tab_ing = ttk.Frame(inner)
        inner.add(tab_ing, text="Ingresos")
        if self.df_ingresos is not None and len(self.df_ingresos) > 0:
            self.crear_tabla_simple(tab_ing, self.df_ingresos)
        else:
            tk.Label(tab_ing, text="No hay datos de ingresos", font=('Arial', 12)).pack(expand=True)
    
    def crear_tabla_simple(self, parent, df):
        """Crea tabla simple"""
        frame = tk.Frame(parent)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        tree = ttk.Treeview(frame, columns=list(df.columns), show='headings', height=12)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        
        for col in df.columns:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor='e' if col != 'Fuente' and col != 'Partida' else 'w')
        
        for _, row in df.iterrows():
            tree.insert('', 'end', values=list(row))
        
        tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

# ============================================
# EJECUTAR
# ============================================
if __name__ == "__main__":
    root = tk.Tk()
    app = AplicacionGraficos(root)
    root.mainloop()