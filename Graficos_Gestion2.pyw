#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
# --- CAMBIO PARA EVITAR VENTANA FANTASMA ---
import matplotlib
matplotlib.use('Agg') 
from matplotlib.figure import Figure
# -------------------------------------------
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
import os

# ============================================
# CLASE PARA TOOLBAR (SOLO BOTÓN GUARDAR)
# ============================================
class ToolbarConNombre(NavigationToolbar2Tk):
    """Toolbar que solo muestra el botón de guardar con nombre personalizado"""
    
    def __init__(self, canvas, window, nombre_base, nombre_ventana):
        # Filtramos para dejar solo el botón de Guardar ('Save')
        self.toolitems = [item for item in NavigationToolbar2Tk.toolitems if item[0] == 'Save']
        self.nombre_base = nombre_base
        self.nombre_ventana = nombre_ventana
        super().__init__(canvas, window)
    
    def save_figure(self, *args):
        """Guarda la figura con el nombre de la ventana"""
        filetypes = self.canvas.get_supported_filetypes_grouped()
        tk_filetypes = [
            (name, "*.%s" % ext) for name, exts in sorted(filetypes.items()) for ext in exts
        ]
        
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
                messagebox.showinfo("Éxito", f"✅ Gráfico guardado como:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar:\n{str(e)}")

# ============================================
# CONFIGURACIÓN
# ============================================
COLORES = {
    'ingresos': '#2E86C1',
    'gastos': '#E74C3C',
    'saldo': '#27AE60',
    'consejeria': '#2E86C1',
    'proyectos': '#F39C12',
    'erasmus': '#27AE60',
    'seguro': '#E74C3C',
    'mentor': '#8E44AD',
    'otros_ing': '#7F8C8D',
}

class AplicacionGraficos:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Generador de Gráficos")
        self.root.configure(bg='#f0f0f0')
        
        self.centrar_ventana(self.root, 500, 500) # Un poco más alta para los selectores
        
        self.df_evolucion = None
        self.df_ingresos = None
        self.df_gastos = None
        self.archivo_actual = None
        self.nombre_base = "datos"
        
        # --- NUEVO: Variables para los tipos de gráfico ---
        self.tipo_ingresos = tk.StringVar(value="Barras")
        self.tipo_gastos = tk.StringVar(value="Barras")
        self.tipo_evolucion = tk.StringVar(value="Barras + Línea")
        
        self.setup_ui()
    
    def centrar_ventana(self, ventana, ancho, alto):
        ventana.update_idletasks()
        ancho_pantalla = ventana.winfo_screenwidth()
        posicion_x = (ancho_pantalla // 2) - (ancho // 2)
        posicion_y = 0
        ventana.geometry(f"{ancho}x{alto}+{posicion_x}+{posicion_y}")
    
    def centrar_ventana_grafico(self, ventana, ancho=1000, alto=700):
        ventana.update_idletasks()
        ancho_pantalla = ventana.winfo_screenwidth()
        posicion_x = (ancho_pantalla // 2) - (ancho // 2)
        posicion_y = 0
        ventana.geometry(f"{ancho}x{alto}+{posicion_x}+{posicion_y}")
    
    def setup_ui(self):
        titulo = tk.Label(self.root, text="📊 GENERADOR DE GRÁFICOS", font=('Arial', 18, 'bold'), bg='#f0f0f0', fg='#2c3e50')
        titulo.pack(pady=20)
        
        btn_cargar = tk.Button(self.root, text="📂 1. CARGAR ARCHIVO EXCEL", command=self.cargar_excel, font=('Arial', 12, 'bold'), bg='#3498db', fg='white', padx=40, pady=12, cursor='hand2', relief='raised', bd=2)
        btn_cargar.pack(pady=10)
        
        self.lbl_archivo = tk.Label(self.root, text="📁 Ningún archivo cargado", font=('Arial', 10, 'italic'), bg='#f0f0f0', fg='#7f8c8d')
        self.lbl_archivo.pack(pady=5)
        
        marco_graficos = tk.LabelFrame(self.root, text="2. CONFIGURA Y GENERA", font=('Arial', 11, 'bold'), bg='#f0f0f0', fg='#2c3e50', padx=20, pady=15)
        marco_graficos.pack(pady=10, padx=40, fill='both')

        # --- FILA EVOLUCIÓN ---
        f1 = tk.Frame(marco_graficos, bg='#f0f0f0')
        f1.pack(fill='x', pady=5)
        self.btn_evolucion = tk.Button(f1, text="📈 Evolución Anual", command=self.mostrar_evolucion, state='disabled', font=('Arial', 10), bg='#95a5a6', fg='white', width=22, pady=5)
        self.btn_evolucion.pack(side='left', padx=5)
        # tk.OptionMenu(f1, self.tipo_evolucion, "Barras + Línea", "Solo Barras").pack(side='right')

        # --- FILA INGRESOS ---
        f2 = tk.Frame(marco_graficos, bg='#f0f0f0')
        f2.pack(fill='x', pady=5)
        self.btn_ingresos = tk.Button(f2, text="💰 Ingresos por Fuente", command=self.mostrar_ingresos, state='disabled', font=('Arial', 10), bg='#95a5a6', fg='white', width=22, pady=5)
        self.btn_ingresos.pack(side='left', padx=(5, 15)) # 15 de margen a la derecha del botón
        
        tk.Label(f2, text="Estilo:", bg='#f0f0f0').pack(side='left', padx=5)
        
        # Quitamos el side='right' y usamos 'left' para que se pegue al texto
        menu_ing = tk.OptionMenu(f2, self.tipo_ingresos, "Barras", "Tarta")
        menu_ing.config(width=8) # Forzamos un ancho para que los menús midan lo mismo
        menu_ing.pack(side='left', padx=5)

        # --- FILA GASTOS ---
        f3 = tk.Frame(marco_graficos, bg='#f0f0f0')
        f3.pack(fill='x', pady=5)
        self.btn_gastos = tk.Button(f3, text="💸 Gastos por Partida", command=self.mostrar_gastos, state='disabled', font=('Arial', 10), bg='#95a5a6', fg='white', width=22, pady=5)
        self.btn_gastos.pack(side='left', padx=(5, 15))
        
        tk.Label(f3, text="Estilo:", bg='#f0f0f0').pack(side='left', padx=5)
        
        menu_gas = tk.OptionMenu(f3, self.tipo_gastos, "Barras", "Tarta")
        menu_gas.config(width=8)
        menu_gas.pack(side='left', padx=5)

        # --- FILA COMPARATIVA ---
        f4 = tk.Frame(marco_graficos, bg='#f0f0f0')
        f4.pack(fill='x', pady=5)
        self.btn_comparativa = tk.Button(f4, text="⚖️ Comparativa Saldos", command=self.mostrar_comparativa, state='disabled', font=('Arial', 10), bg='#95a5a6', fg='white', width=22, pady=5)
        self.btn_comparativa.pack(side='left', padx=5)
        
        self.status_bar = tk.Label(self.root, text="✅ Carga un archivo Excel para comenzar", bd=1, relief='sunken', anchor='w', bg='#ecf0f1')
        self.status_bar.pack(fill='x', side='bottom', padx=10, pady=5)
    
    def cargar_excel(self):
        archivo = filedialog.askopenfilename(title="Seleccionar archivo Excel", filetypes=[("Excel files", "*.xlsx *.xls"), ("Todos", "*.*")])
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
                self.btn_evolucion.config(state='normal', bg='#27ae60', activebackground='#2ecc71')
                self.btn_ingresos.config(state='normal', bg='#27ae60', activebackground='#2ecc71')
                self.btn_gastos.config(state='normal', bg='#27ae60', activebackground='#2ecc71')
                self.btn_comparativa.config(state='normal', bg='#27ae60', activebackground='#2ecc71')
            except Exception as e:
                messagebox.showerror("❌ Error", f"Error al cargar:\n{str(e)}")
                self.status_bar.config(text="❌ Error al cargar archivo")
    
    def procesar_excel(self, archivo):
        xl = pd.ExcelFile(archivo)
        self.df_evolucion = self.df_ingresos = self.df_gastos = None
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
        try:
            años = [col for col in df.columns if str(col).isdigit() or (isinstance(col, (int, float)) and 2000 < col < 2100)]
            if not años: return None
            fila_ingresos = df[df.iloc[:, 0].astype(str).str.contains('ingreso', case=False, na=False)]
            fila_gastos = df[df.iloc[:, 0].astype(str).str.contains('gasto', case=False, na=False)]
            fila_saldo = df[df.iloc[:, 0].astype(str).str.contains('saldo', case=False, na=False)]
            datos = []
            for año in años:
                ing = float(fila_ingresos[año].values[0]) if not fila_ingresos.empty else 0
                gas = float(fila_gastos[año].values[0]) if not fila_gastos.empty else 0
                saldo = float(fila_saldo[año].values[0]) if not fila_saldo.empty else 0
                datos.append({'Año': int(año), 'Ingresos': ing, 'Gastos': gas, 'Saldo': saldo})
            return pd.DataFrame(datos)
        except: return None
    
    def procesar_ingresos(self, df):
        try:
            df_proc = df.iloc[:, :2].copy()
            df_proc.columns = ['Fuente', 'Importe']
            df_proc = df_proc.dropna()
            df_proc['Importe'] = pd.to_numeric(df_proc['Importe'], errors='coerce')
            return df_proc[df_proc['Importe'] > 0]
        except: return None
    
    def procesar_gastos(self, df):
        try:
            df_proc = df.iloc[:, :2].copy()
            df_proc.columns = ['Partida', 'Importe']
            df_proc = df_proc.dropna()
            df_proc['Importe'] = pd.to_numeric(df_proc['Importe'], errors='coerce')
            return df_proc[df_proc['Importe'] > 0].sort_values('Importe', ascending=False)
        except: return None
    
    def crear_ventana_grafico(self, titulo):
        ventana = tk.Toplevel(self.root)
        ventana.title(f"📊 {titulo} - {self.nombre_base}")
        self.centrar_ventana_grafico(ventana, 1000, 700)
        return ventana
    
    def mostrar_evolucion(self):
        if self.df_evolucion is None or len(self.df_evolucion) == 0:
            messagebox.showwarning("Aviso", "No hay datos de evolución")
            return
        ventana = self.crear_ventana_grafico("Evolucion_Anual")
        # --- USANDO FIGURE DIRECTAMENTE ---
        fig = Figure(figsize=(11, 7))
        ax = fig.add_subplot(111)
        
        x = np.arange(len(self.df_evolucion))
        ancho = 0.35
        ax.bar(x - ancho/2, self.df_evolucion['Ingresos'], ancho, label='Ingresos', color='#2E86C1', alpha=0.8)
        ax.bar(x + ancho/2, self.df_evolucion['Gastos'], ancho, label='Gastos', color='#E74C3C', alpha=0.8)
        
        ax2 = ax.twinx()
        ax2.plot(x, self.df_evolucion['Saldo'], '-^', linewidth=3, markersize=10, label='Saldo', color='#27AE60', markerfacecolor='white')
        
        max_val = max(self.df_evolucion['Ingresos'].max(), self.df_evolucion['Gastos'].max())
        for i, ing in enumerate(self.df_evolucion['Ingresos']):
            ax.text(i - ancho/2, ing/2, f'{ing:,.0f}€', ha='center', va='center', fontsize=9, fontweight='bold', color='white', bbox=dict(boxstyle='round,pad=0.2', facecolor='none', edgecolor='black', linewidth=0.5))
        for i, gas in enumerate(self.df_evolucion['Gastos']):
            ax.text(i + ancho/2, gas/2, f'{gas:,.0f}€', ha='center', va='center', fontsize=9, fontweight='bold', color='white', bbox=dict(boxstyle='round,pad=0.2', facecolor='none', edgecolor='black', linewidth=0.5))
        for i, saldo in enumerate(self.df_evolucion['Saldo']):
            ax2.text(i, saldo + max_val*0.05, f'{saldo:,.0f}€', ha='center', va='bottom', fontsize=10, fontweight='bold', color='#1e8449', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#27AE60', alpha=0.9))
            
        ax.set_title('Evolución Anual', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(self.df_evolucion['Año'])
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        ax2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, ventana)
        toolbar = ToolbarConNombre(canvas, ventana, self.nombre_base, "Evolucion_Anual")
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def mostrar_ingresos(self):
        if self.df_ingresos is None or len(self.df_ingresos) == 0:
            messagebox.showwarning("Aviso", "No hay datos de ingresos")
            return
        
        estilo = self.tipo_ingresos.get()
        ventana = self.crear_ventana_grafico(f"Ingresos_{estilo}")
        fig = Figure(figsize=(11, 7))
        ax = fig.add_subplot(111)
        
        df_ord = self.df_ingresos.sort_values('Importe', ascending=True)
        total = df_ord['Importe'].sum()
        
        # --- CORRECCIÓN DE COLORES ---
        lista_colores_base = [
            COLORES.get('consejeria', '#2E86C1'), 
            COLORES.get('proyectos', '#F39C12'), 
            COLORES.get('erasmus', '#27AE60'), 
            COLORES.get('seguro', '#E74C3C'), 
            COLORES.get('mentor', '#8E44AD'), 
            COLORES.get('otros_ing', '#7F8C8D')
        ]
        
        # Si hay más datos que colores, generamos una paleta adicional para que no falle
        if len(df_ord) > len(lista_colores_base):
            extra = matplotlib.cm.tab20(np.linspace(0, 1, len(df_ord)))
            colores_finales = extra
        else:
            colores_finales = lista_colores_base[:len(df_ord)]
        # -----------------------------

        if estilo == "Tarta":
            # Usamos wedgeprops para que se vea más moderno
            ax.pie(df_ord['Importe'], labels=df_ord['Fuente'], autopct='%1.1f%%', 
                   startangle=140, colors=colores_finales, 
                   wedgeprops={'edgecolor': 'white', 'linewidth': 2})
            ax.set_title(f'Distribución de Ingresos - Total: {total:,.0f}€', fontsize=14, fontweight='bold')
        else:
            y_pos = np.arange(len(df_ord))
            barras = ax.barh(y_pos, df_ord['Importe'], color=colores_finales)
            max_val = df_ord['Importe'].max()
            for i, valor in enumerate(df_ord['Importe']):
                porcentaje = (valor / total) * 100
                ax.text(valor + max_val*0.02, i, f'{valor:,.0f}€ ({porcentaje:.1f}%)', va='center', fontweight='bold')
            ax.set_yticks(y_pos)
            ax.set_yticklabels(df_ord['Fuente'])
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
            ax.set_xlim(0, max_val * 1.35)
            ax.set_title(f'Ingresos por Fuente - Total: {total:,.0f}€', fontsize=14, fontweight='bold')

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, ventana)
        ToolbarConNombre(canvas, ventana, self.nombre_base, f"Ingresos_{estilo}")
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def mostrar_gastos(self):
        if self.df_gastos is None or len(self.df_gastos) == 0:
            messagebox.showwarning("Aviso", "No hay datos de gastos")
            return
            
        estilo = self.tipo_gastos.get()
        ventana = self.crear_ventana_grafico(f"Gastos_{estilo}")
        
        # Ajustamos tamaño si es tarta o barras
        fig = Figure(figsize=(12, 7 if estilo == "Tarta" else max(7, len(self.df_gastos) * 0.25)))
        ax = fig.add_subplot(111)
        
        df_ord = self.df_gastos.sort_values('Importe', ascending=True)
        total = df_ord['Importe'].sum()

        if estilo == "Tarta":
            # Para tarta de muchos elementos, agrupamos los pequeños en "Otros" para que se vea bien
            if len(df_ord) > 8:
                otros = df_ord.iloc[:-7]
                top = df_ord.iloc[-7:]
                nueva_fila = pd.DataFrame([{'Partida': 'Otros', 'Importe': otros['Importe'].sum()}])
                df_plot = pd.concat([nueva_fila, top])
            else:
                df_plot = df_ord

            ax.pie(df_plot['Importe'], labels=df_plot['Partida'], autopct='%1.1f%%', startangle=140, 
                   colors=matplotlib.cm.Paired(np.linspace(0, 1, len(df_plot))))
            ax.set_title(f'Distribución de Gastos (Top Artículos)', fontsize=14, fontweight='bold')
        else:
            y_pos = np.arange(len(df_ord))
            colores = matplotlib.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(df_ord)))
            ax.barh(y_pos, df_ord['Importe'], color=colores)
            max_val = df_ord['Importe'].max()
            for i, valor in enumerate(df_ord['Importe']):
                porcentaje = (valor / total) * 100
                ax.text(valor + max_val*0.02, i, f'{valor:,.0f}€ ({porcentaje:.1f}%)', va='center', fontsize=9, fontweight='bold')
            ax.set_yticks(y_pos)
            ax.set_yticklabels(df_ord['Partida'], fontsize=9)
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
            ax.set_xlim(0, max_val * 1.4)
            ax.set_title(f'Partidas de Gasto - Total: {total:,.0f}€', fontsize=14, fontweight='bold')

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, ventana)
        ToolbarConNombre(canvas, ventana, self.nombre_base, f"Gastos_{estilo}")
        canvas.get_tk_widget().pack(fill='both', expand=True)
        
    def mostrar_comparativa(self):
        if self.df_evolucion is None or len(self.df_evolucion) == 0:
            messagebox.showwarning("Aviso", "No hay datos de saldos")
            return
        ventana = self.crear_ventana_grafico("Comparativa_Saldos")
        fig = Figure(figsize=(11, 7))
        ax = fig.add_subplot(111)
        x = np.arange(len(self.df_evolucion))
        ancho = 0.35
        ax.bar(x, self.df_evolucion['Saldo'], ancho, label='Saldo', color='#3498db', alpha=0.7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
        
        max_saldo = max(abs(self.df_evolucion['Saldo'].min()), self.df_evolucion['Saldo'].max())
        for i, saldo in enumerate(self.df_evolucion['Saldo']):
            color = '#27ae60' if saldo >= 0 else '#e74c3c'
            ax.text(i, saldo + max_saldo*0.03 if saldo >= 0 else saldo - max_saldo*0.08, 
                    f'{saldo:+,.0f}€', ha='center', fontsize=10, fontweight='bold', 
                    color=color, bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=color, alpha=0.9))
        
        ax.set_title('Saldo por Año', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(self.df_evolucion['Año'])
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: f'{x:,.0f}€'))
        
        # --- ESTO ES LO QUE FALTABA ---
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, ventana)
        ToolbarConNombre(canvas, ventana, self.nombre_base, "Comparativa_Saldos")
        canvas.get_tk_widget().pack(fill='both', expand=True)
if __name__ == "__main__":
    root = tk.Tk()
    app = AplicacionGraficos(root)
    root.mainloop()