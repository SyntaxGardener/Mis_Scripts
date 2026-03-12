#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
import os

# ============================================
# CLASE PARA TOOLBAR 
# ============================================
class ToolbarConNombre(NavigationToolbar2Tk):
    """Toolbar que guarda con el nombre de la ventana"""
    
    def __init__(self, canvas, window, nombre_base, nombre_ventana):
        self.nombre_base = nombre_base
        self.nombre_ventana = nombre_ventana
        super().__init__(canvas, window)
    
    def save_figure(self, *args):
        """Guarda la figura con el nombre de la ventana"""
        from matplotlib.backends._backend_tk import SaveFigureTk
        
        filetypes = self.canvas.get_supported_filetypes_grouped()
        tk_filetypes = [
            (name, "*.%s" % ext) for name, exts in sorted(filetypes.items()) for ext in exts
        ]
        
        # Nombre sugerido: nombre_base_nombre_ventana.png
        nombre_sugerido = f"{self.nombre_base}_{self.nombre_ventana}.png"
        
        filename = filedialog.asksaveasfilename(
            title="Guardar gráfico como",
            initialfile=nombre_sugerido,
            filetypes=tk_filetypes + [("Todos los archivos", "*.*")]
        )
        
        if filename:
            try:
                self.canvas.figure.savefig(filename)
                self.canvas.draw_idle()
                tk.messagebox.showinfo("Éxito", f"✅ Gráfico guardado como:\n{filename}")
            except Exception as e:
                tk.messagebox.showerror("Error", f"Error al guardar:\n{str(e)}")

# ============================================
# CONFIGURACIÓN
# ============================================
COLORES = {
    'ingresos': '#2E86C1',      # Azul
    'gastos': '#E74C3C',         # Rojo
    'saldo': '#27AE60',          # Verde
    'consejeria': '#2E86C1',     # Azul
    'proyectos': '#F39C12',       # Naranja
    'erasmus': '#27AE60',         # Verde
    'seguro': '#E74C3C',          # Rojo
    'mentor': '#8E44AD',          # Morado
    'otros_ing': '#7F8C8D',       # Gris
}

class AplicacionGraficos:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Generador de Gráficos")
        self.root.configure(bg='#f0f0f0')
        
        # Centrar la ventana principal
        self.centrar_ventana(self.root, 600, 500)
        
        # Variables
        self.df_evolucion = None
        self.df_ingresos = None
        self.df_gastos = None
        self.archivo_actual = None
        self.nombre_base = "datos"
        
        self.setup_ui()
    
    def centrar_ventana(self, ventana, ancho, alto):
        """Centra una ventana en la pantalla y la alinea arriba"""
        ventana.update_idletasks()
        ancho_pantalla = ventana.winfo_screenwidth()
        posicion_x = (ancho_pantalla // 2) - (ancho // 2)
        posicion_y = 0  # Pegado arriba
        ventana.geometry(f"{ancho}x{alto}+{posicion_x}+{posicion_y}")
    
    def centrar_ventana_grafico(self, ventana, ancho=1000, alto=700):
        """Centra una ventana de gráfico y la alinea arriba"""
        ventana.update_idletasks()
        ancho_pantalla = ventana.winfo_screenwidth()
        posicion_x = (ancho_pantalla // 2) - (ancho // 2)
        posicion_y = 0  # Pegado arriba
        ventana.geometry(f"{ancho}x{alto}+{posicion_x}+{posicion_y}")
    
    def setup_ui(self):
        """Configura la interfaz principal"""
        
        # ========== TÍTULO ==========
        titulo = tk.Label(self.root, 
                         text="📊 GENERADOR DE GRÁFICOS",
                         font=('Arial', 18, 'bold'),
                         bg='#f0f0f0',
                         fg='#2c3e50')
        titulo.pack(pady=30)
        
        # ========== SUBTÍTULO ==========
        subtitulo = tk.Label(self.root,
                            text="Centro Escolar - Cuenta de Gestión",
                            font=('Arial', 11),
                            bg='#f0f0f0',
                            fg='#7f8c8d')
        subtitulo.pack(pady=5)
        
        # ========== BOTÓN CARGAR EXCEL ==========
        btn_cargar = tk.Button(self.root,
                              text="📂 1. CARGAR ARCHIVO EXCEL",
                              command=self.cargar_excel,
                              font=('Arial', 12, 'bold'),
                              bg='#3498db',
                              fg='white',
                              padx=40,
                              pady=12,
                              cursor='hand2',
                              relief='raised',
                              bd=2)
        btn_cargar.pack(pady=20)
        
        # ========== INFO ARCHIVO ==========
        self.lbl_archivo = tk.Label(self.root,
                                   text="📁 Ningún archivo cargado",
                                   font=('Arial', 10, 'italic'),
                                   bg='#f0f0f0',
                                   fg='#7f8c8d')
        self.lbl_archivo.pack(pady=5)
        
        # ========== MARCO DE GRÁFICOS ==========
        marco_graficos = tk.LabelFrame(self.root,
                                       text="2. SELECCIONA GRÁFICO",
                                       font=('Arial', 11, 'bold'),
                                       bg='#f0f0f0',
                                       fg='#2c3e50',
                                       padx=30,
                                       pady=15,
                                       relief='groove',
                                       bd=2)
        marco_graficos.pack(pady=20, padx=50, fill='both')
        
        # Botones para cada gráfico (inicialmente deshabilitados)
        self.btn_evolucion = tk.Button(marco_graficos,
                                      text="📈 Evolución Anual",
                                      command=self.mostrar_evolucion,
                                      state='disabled',
                                      font=('Arial', 10),
                                      bg='#95a5a6',
                                      fg='white',
                                      width=30,
                                      pady=8,
                                      cursor='hand2',
                                      relief='raised')
        self.btn_evolucion.pack(pady=5)
        
        self.btn_ingresos = tk.Button(marco_graficos,
                                     text="💰 Ingresos por Fuente",
                                     command=self.mostrar_ingresos,
                                     state='disabled',
                                     font=('Arial', 10),
                                     bg='#95a5a6',
                                     fg='white',
                                     width=30,
                                     pady=8,
                                     cursor='hand2',
                                     relief='raised')
        self.btn_ingresos.pack(pady=5)
        
        self.btn_gastos = tk.Button(marco_graficos,
                                   text="💸 Gastos por Partida",
                                   command=self.mostrar_gastos,
                                   state='disabled',
                                   font=('Arial', 10),
                                   bg='#95a5a6',
                                   fg='white',
                                   width=30,
                                   pady=8,
                                   cursor='hand2',
                                   relief='raised')
        self.btn_gastos.pack(pady=5)
        
        self.btn_comparativa = tk.Button(marco_graficos,
                                        text="⚖️ Comparativa Saldos",
                                        command=self.mostrar_comparativa,
                                        state='disabled',
                                        font=('Arial', 10),
                                        bg='#95a5a6',
                                        fg='white',
                                        width=30,
                                        pady=8,
                                        cursor='hand2',
                                        relief='raised')
        self.btn_comparativa.pack(pady=5)
        
        # ========== BARRA DE ESTADO ==========
        self.status_bar = tk.Label(self.root,
                                   text="✅ Carga un archivo Excel para comenzar",
                                   bd=1,
                                   relief='sunken',
                                   anchor='w',
                                   bg='#ecf0f1',
                                   fg='#2c3e50',
                                   font=('Arial', 9))
        self.status_bar.pack(fill='x', side='bottom', padx=10, pady=5)
        
        # ========== PIE DE PÁGINA ==========
        pie = tk.Label(self.root,
                      text="© 2026 - Generador de Gráficos v2.0",
                      font=('Arial', 8),
                      bg='#f0f0f0',
                      fg='#bdc3c7')
        pie.pack(side='bottom', pady=5)
    
    def cargar_excel(self):
        """Carga el archivo Excel - SIN VENTANA EMERGENTE"""
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo Excel",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("Todos", "*.*")]
        )
        
        if archivo:
            self.archivo_actual = archivo
            nombre_completo = os.path.basename(archivo)
            self.nombre_base = os.path.splitext(nombre_completo)[0]
            
            self.lbl_archivo.config(text=f"📁 {nombre_completo}", fg='#27ae60')
            self.status_bar.config(text=f"📂 Cargando: {nombre_completo}...")
            self.root.update()
            
            try:
                self.procesar_excel(archivo)
                self.status_bar.config(text=f"✅ {nombre_completo} cargado correctamente")
                
                # Habilitar botones (cambian a verde)
                self.btn_evolucion.config(state='normal', bg='#27ae60', activebackground='#2ecc71')
                self.btn_ingresos.config(state='normal', bg='#27ae60', activebackground='#2ecc71')
                self.btn_gastos.config(state='normal', bg='#27ae60', activebackground='#2ecc71')
                self.btn_comparativa.config(state='normal', bg='#27ae60', activebackground='#2ecc71')
                
                # SIN VENTANA EMERGENTE - solo actualizamos la barra de estado
                
            except Exception as e:
                # Solo mostramos error si algo falla realmente
                messagebox.showerror("❌ Error", f"Error al cargar:\n{str(e)}")
                self.status_bar.config(text="❌ Error al cargar archivo")
    
    def procesar_excel(self, archivo):
        """Procesa el Excel y carga los datos"""
        xl = pd.ExcelFile(archivo)
        
        self.df_evolucion = None
        self.df_ingresos = None
        self.df_gastos = None
        
        for hoja in xl.sheet_names:
            if any(p in hoja.lower() for p in ['resumen', 'evolucion', 'anual']):
                df = pd.read_excel(archivo, sheet_name=hoja)
                self.df_evolucion = self.procesar_evolucion(df)
            
            if any(p in hoja.lower() for p in ['ingreso', 'fuentes']):
                df = pd.read_excel(archivo, sheet_name=hoja)
                self.df_ingresos = self.procesar_ingresos(df)
            
            if any(p in hoja.lower() for p in ['gasto', 'partidas']):
                df = pd.read_excel(archivo, sheet_name=hoja)
                self.df_gastos = self.procesar_gastos(df)
    
    def procesar_evolucion(self, df):
        """Procesa hoja de evolución"""
        try:
            años = []
            for col in df.columns:
                try:
                    if str(col).isdigit() or (isinstance(col, (int, float)) and 2000 < col < 2100):
                        años.append(col)
                except:
                    pass
            
            if not años:
                return None
            
            fila_ingresos = df[df.iloc[:, 0].astype(str).str.contains('ingreso', case=False, na=False)]
            fila_gastos = df[df.iloc[:, 0].astype(str).str.contains('gasto', case=False, na=False)]
            fila_saldo = df[df.iloc[:, 0].astype(str).str.contains('saldo', case=False, na=False)]
            
            datos = []
            for año in años:
                ing = float(fila_ingresos[año].values[0]) if not fila_ingresos.empty else 0
                gas = float(fila_gastos[año].values[0]) if not fila_gastos.empty else 0
                saldo = float(fila_saldo[año].values[0]) if not fila_saldo.empty else 0
                
                datos.append({
                    'Año': int(año),
                    'Ingresos': ing,
                    'Gastos': gas,
                    'Saldo': saldo
                })
            
            return pd.DataFrame(datos)
        except:
            return None
    
    def procesar_ingresos(self, df):
        """Procesa hoja de ingresos"""
        try:
            df_proc = df.iloc[:, :2].copy()
            df_proc.columns = ['Fuente', 'Importe']
            df_proc = df_proc.dropna()
            df_proc['Importe'] = pd.to_numeric(df_proc['Importe'], errors='coerce')
            df_proc = df_proc[df_proc['Importe'] > 0]
            return df_proc
        except:
            return None
    
    def procesar_gastos(self, df):
        """Procesa hoja de gastos"""
        try:
            df_proc = df.iloc[:, :2].copy()
            df_proc.columns = ['Partida', 'Importe']
            df_proc = df_proc.dropna()
            df_proc['Importe'] = pd.to_numeric(df_proc['Importe'], errors='coerce')
            df_proc = df_proc[df_proc['Importe'] > 0]
            df_proc = df_proc.sort_values('Importe', ascending=False)
            return df_proc
        except:
            return None
    
    def crear_ventana_grafico(self, titulo):
        """Crea una ventana nueva para el gráfico"""
        ventana = tk.Toplevel(self.root)
        ventana.title(f"📊 {titulo} - {self.nombre_base}")
        
        # Centrar y alinear arriba
        self.centrar_ventana_grafico(ventana, 1000, 700)
        
        return ventana
    
    def mostrar_evolucion(self):
        """Muestra gráfico de evolución anual - TEXTOS MEJORADOS"""
        if self.df_evolucion is None or len(self.df_evolucion) == 0:
            messagebox.showwarning("Aviso", "No hay datos de evolución")
            return
        
        ventana = self.crear_ventana_grafico("Evolucion_Anual")
        
        fig, ax = plt.subplots(figsize=(11, 7))
        x = np.arange(len(self.df_evolucion))
        ancho = 0.35
        
        # Barras
        barras_ing = ax.bar(x - ancho/2, self.df_evolucion['Ingresos'], ancho, 
                           label='Ingresos', color='#2E86C1', alpha=0.8)
        barras_gas = ax.bar(x + ancho/2, self.df_evolucion['Gastos'], ancho, 
                           label='Gastos', color='#E74C3C', alpha=0.8)
        
        # Línea de saldo
        ax2 = ax.twinx()
        linea_saldo = ax2.plot(x, self.df_evolucion['Saldo'], '-^', linewidth=3, markersize=10,
                              label='Saldo', color='#27AE60', markerfacecolor='white')
        
        # TEXTOS MEJORADOS
        max_val = max(self.df_evolucion['Ingresos'].max(), self.df_evolucion['Gastos'].max())
        
        # Textos para ingresos (sobre azul) - en BLANCO con borde negro
        for i, ing in enumerate(self.df_evolucion['Ingresos']):
            ax.text(i - ancho/2, ing/2, f'{ing:,.0f}€', 
                   ha='center', va='center',
                   fontsize=9, fontweight='bold', color='white',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='none', edgecolor='black', linewidth=0.5))
        
        # Textos para gastos (sobre rojo) - en BLANCO con borde negro
        for i, gas in enumerate(self.df_evolucion['Gastos']):
            ax.text(i + ancho/2, gas/2, f'{gas:,.0f}€', 
                   ha='center', va='center',
                   fontsize=9, fontweight='bold', color='white',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='none', edgecolor='black', linewidth=0.5))
        
        # Textos para saldo (sobre línea verde) - en VERDE OSCURO con fondo blanco
        for i, saldo in enumerate(self.df_evolucion['Saldo']):
            ax2.text(i, saldo + max_val*0.05, f'{saldo:,.0f}€', 
                    ha='center', va='bottom',
                    fontsize=10, fontweight='bold', color='#1e8449',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#27AE60', alpha=0.9))
        
        ax.set_xlabel('Año', fontsize=11)
        ax.set_ylabel('Ingresos / Gastos (€)', fontsize=11)
        ax2.set_ylabel('Saldo (€)', fontsize=11)
        ax.set_title('Evolución Anual', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(self.df_evolucion['Año'])
        ax.grid(True, alpha=0.3)
        
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, ventana)
        toolbar = ToolbarConNombre(canvas, ventana, self.nombre_base, "Evolucion_Anual")
        toolbar.update()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def mostrar_ingresos(self):
        """Muestra gráfico de ingresos"""
        if self.df_ingresos is None or len(self.df_ingresos) == 0:
            messagebox.showwarning("Aviso", "No hay datos de ingresos")
            return
        
        ventana = self.crear_ventana_grafico("Ingresos")
        
        fig, ax = plt.subplots(figsize=(11, 7))
        df_ord = self.df_ingresos.sort_values('Importe', ascending=True)
        total = df_ord['Importe'].sum()
        
        y_pos = np.arange(len(df_ord))
        colores = [COLORES['consejeria'], COLORES['proyectos'], COLORES['erasmus'],
                   COLORES['seguro'], COLORES['mentor'], COLORES['otros_ing']]
        
        barras = ax.barh(y_pos, df_ord['Importe'], color=colores[:len(df_ord)])
        
        max_val = df_ord['Importe'].max()
        for i, (barra, valor, fuente) in enumerate(zip(barras, df_ord['Importe'], df_ord['Fuente'])):
            porcentaje = (valor / total) * 100
            texto = f'{valor:,.0f}€ ({porcentaje:.1f}%)'
            if valor > max_val * 0.15:
                ax.text(valor/2, i, texto, ha='center', va='center',
                       fontsize=9, fontweight='bold', color='white')
            else:
                ax.text(valor + max_val*0.02, i, texto, va='center',
                       fontsize=9, fontweight='bold', color='black')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df_ord['Fuente'], fontsize=10)
        ax.set_xlabel('Importe (€)', fontsize=11)
        ax.set_title(f'Ingresos por Fuente - Total: {total:,.0f}€', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        ax.set_xlim(0, max_val * 1.35)
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, ventana)
        toolbar = ToolbarConNombre(canvas, ventana, self.nombre_base, "Ingresos")
        toolbar.update()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def mostrar_gastos(self):
        """Muestra gráfico de gastos"""
        if self.df_gastos is None or len(self.df_gastos) == 0:
            messagebox.showwarning("Aviso", "No hay datos de gastos")
            return
        
        ventana = self.crear_ventana_grafico("Gastos")
        
        fig, ax = plt.subplots(figsize=(12, max(7, len(self.df_gastos) * 0.25)))
        df_ord = self.df_gastos.sort_values('Importe', ascending=True)
        total = df_ord['Importe'].sum()
        
        y_pos = np.arange(len(df_ord))
        colores = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(df_ord)))
        
        barras = ax.barh(y_pos, df_ord['Importe'], color=colores)
        
        max_val = df_ord['Importe'].max()
        for i, (barra, valor, partida) in enumerate(zip(barras, df_ord['Importe'], df_ord['Partida'])):
            porcentaje = (valor / total) * 100
            ax.text(valor + max_val*0.02, i, f'{valor:,.0f}€ ({porcentaje:.1f}%)', 
                   va='center', fontsize=9, fontweight='bold')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df_ord['Partida'], fontsize=9)
        ax.set_xlabel('Importe (€)', fontsize=11)
        ax.set_title(f'Todas las partidas de gasto - Total: {total:,.0f}€', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        ax.set_xlim(0, max_val * 1.4)
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, ventana)
        toolbar = ToolbarConNombre(canvas, ventana, self.nombre_base, "Gastos")
        toolbar.update()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def mostrar_comparativa(self):
        """Muestra gráfico comparativo de saldos"""
        if self.df_evolucion is None or len(self.df_evolucion) == 0:
            messagebox.showwarning("Aviso", "No hay datos de saldos")
            return
        
        ventana = self.crear_ventana_grafico("Comparativa_Saldos")
        
        fig, ax = plt.subplots(figsize=(11, 7))
        x = np.arange(len(self.df_evolucion))
        ancho = 0.35
        
        ax.bar(x - ancho/2, self.df_evolucion['Saldo'], ancho, 
               label='Saldo', color='#3498db', alpha=0.7)
        
        # Línea base cero
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
        
        # Valores
        max_saldo = max(abs(self.df_evolucion['Saldo'].min()), self.df_evolucion['Saldo'].max())
        for i, saldo in enumerate(self.df_evolucion['Saldo']):
            color = '#27ae60' if saldo >= 0 else '#e74c3c'
            ax.text(i, saldo + max_saldo*0.03 if saldo >= 0 else saldo - max_saldo*0.08,
                   f'{saldo:+,.0f}€', ha='center', fontsize=10, fontweight='bold',
                   color=color,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=color, alpha=0.9))
        
        ax.set_xlabel('Año', fontsize=11)
        ax.set_ylabel('Saldo (€)', fontsize=11)
        ax.set_title('Saldo por Año', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(self.df_evolucion['Año'])
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, ventana)
        toolbar = ToolbarConNombre(canvas, ventana, self.nombre_base, "Comparativa_Saldos")
        toolbar.update()
        canvas.get_tk_widget().pack(fill='both', expand=True)

# ============================================
# EJECUTAR
# ============================================
if __name__ == "__main__":
    root = tk.Tk()
    app = AplicacionGraficos(root)
    root.mainloop()