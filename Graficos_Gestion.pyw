#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Graficos_Gestion.pyw  –  Generador de gráficos de gestión económica
Script unificado · versión 2
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
import os, subprocess, sys

# ──────────────────────────────────────────────────────────────
#  PALETA DE COLORES
# ──────────────────────────────────────────────────────────────
C = {
    'ingresos':  '#2E86C1',
    'gastos':    '#E74C3C',
    'saldo_pos': '#27AE60',
    'saldo_neg': '#E74C3C',
    'saldo_ini': '#3498DB',
    'saldo_fin': '#2ECC71',
    'ctrl_bg':   '#F0F2F5',
}
PAL_ING = ['#2E86C1','#F39C12','#27AE60','#E74C3C','#8E44AD',
           '#7F8C8D','#1ABC9C','#D35400','#2980B9','#16A085']
PAL_GAS = matplotlib.cm.RdYlGn_r


def fmt_eur(x, _=None):
    return f"{x:,.0f}€"


# ──────────────────────────────────────────────────────────────
#  TOOLBAR PERSONALIZADO (solo botón Guardar)
# ──────────────────────────────────────────────────────────────
class ToolbarGuardar(NavigationToolbar2Tk):
    def __init__(self, canvas, parent, nombre_base="grafico"):
        self.toolitems = [i for i in NavigationToolbar2Tk.toolitems if i[0] == 'Save']
        self._nombre_base = nombre_base
        super().__init__(canvas, parent)

    def save_figure(self, *args):
        fn = filedialog.asksaveasfilename(
            title="Guardar gráfico",
            initialfile=f"{self._nombre_base}.png",
            filetypes=[("PNG", "*.png"), ("Todos", "*.*")])
        if not fn:
            return
        try:
            self.canvas.figure.savefig(fn, dpi=150, bbox_inches='tight')
            if messagebox.askyesno("Guardado", f"✅ Guardado:\n{fn}\n\n¿Abrir carpeta?"):
                carpeta = os.path.dirname(fn)
                if   os.name == 'nt':          os.startfile(carpeta)
                elif sys.platform == 'darwin':  subprocess.Popen(['open', carpeta])
                else:                           subprocess.Popen(['xdg-open', carpeta])
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))


# ──────────────────────────────────────────────────────────────
#  APLICACIÓN
# ──────────────────────────────────────────────────────────────
class AplicacionGraficos:

    # ── Init ──────────────────────────────────────────────────
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Generador de Gráficos de Gestión")

        self.df_evolucion = self.df_ingresos = self.df_gastos = None
        self.nombre_base  = "grafico"

        self.tipo_ingresos = tk.StringVar(value="Barras")
        self.tipo_gastos   = tk.StringVar(value="Barras")

        self._construir_ui()
        self._pantalla_bienvenida()
        self._centrar(1260, 790)

    def _centrar(self, w, h):
        self.root.update_idletasks()
        px = (self.root.winfo_screenwidth() // 2) - (w // 2)
        self.root.geometry(f"{w}x{h}+{px}+0")

    # ── Construcción UI ───────────────────────────────────────
    def _construir_ui(self):
        # ── Barra superior ──────────────────────────────────────
        bar = tk.Frame(self.root, bg='#2C3E50', height=64)
        bar.pack(fill='x')
        bar.pack_propagate(False)

        self.btn_cargar = tk.Button(bar, text="📂  CARGAR EXCEL",
            command=self._abrir_excel, font=('Arial', 11, 'bold'),
            bg='#3498DB', fg='white', activebackground='#2980B9',
            activeforeground='white', relief='flat', padx=18, pady=6, cursor='hand2')
        self.btn_cargar.pack(side='left', padx=14, pady=12)

        self.btn_exportar = tk.Button(bar, text="💾  EXPORTAR TODO",
            command=self._exportar_todos, font=('Arial', 11, 'bold'),
            bg='#27AE60', fg='white', activebackground='#1E8449',
            activeforeground='white', relief='flat', padx=18, pady=6,
            cursor='hand2', state='disabled')
        self.btn_exportar.pack(side='left', padx=4, pady=12)

        self.lbl_archivo = tk.Label(bar, text="📁 Ningún archivo cargado",
            bg='#2C3E50', fg='#BDC3C7', font=('Arial', 10, 'italic'))
        self.lbl_archivo.pack(side='left', padx=10)

        # ── Notebook ───────────────────────────────────────────
        style = ttk.Style()
        style.configure('TNotebook.Tab', font=('Arial', 10, 'bold'), padding=[10, 4])
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill='both', expand=True, padx=8, pady=(4, 0))

        # Pestaña Evolución
        self.tab_evo = ttk.Frame(self.nb)
        self.nb.add(self.tab_evo, text="📈  Evolución Anual")
        self.canvas_evo = tk.Frame(self.tab_evo)
        self.canvas_evo.pack(fill='both', expand=True)

        # Pestaña Ingresos  –  controles FIJOS arriba, canvas variable abajo
        self.tab_ing = ttk.Frame(self.nb)
        self.nb.add(self.tab_ing, text="💰  Ingresos")
        self.ctrl_ing = tk.Frame(self.tab_ing, bg=C['ctrl_bg'], pady=6)
        self.ctrl_ing.pack(fill='x', side='top')
        tk.Label(self.ctrl_ing, text="Tipo de gráfico:", bg=C['ctrl_bg'],
                 font=('Arial', 9, 'bold')).pack(side='left', padx=12)
        for op in ("Barras", "Tarta"):
            tk.Radiobutton(self.ctrl_ing, text=op, variable=self.tipo_ingresos,
                value=op, bg=C['ctrl_bg'], font=('Arial', 10),
                command=self._redibujar_ing).pack(side='left', padx=8)
        self.canvas_ing = tk.Frame(self.tab_ing)
        self.canvas_ing.pack(fill='both', expand=True)

        # Pestaña Gastos  –  controles FIJOS arriba, canvas variable abajo
        self.tab_gas = ttk.Frame(self.nb)
        self.nb.add(self.tab_gas, text="💸  Gastos")
        self.ctrl_gas = tk.Frame(self.tab_gas, bg=C['ctrl_bg'], pady=6)
        self.ctrl_gas.pack(fill='x', side='top')
        tk.Label(self.ctrl_gas, text="Tipo de gráfico:", bg=C['ctrl_bg'],
                 font=('Arial', 9, 'bold')).pack(side='left', padx=12)
        for op in ("Barras", "Tarta"):
            tk.Radiobutton(self.ctrl_gas, text=op, variable=self.tipo_gastos,
                value=op, bg=C['ctrl_bg'], font=('Arial', 10),
                command=self._redibujar_gas).pack(side='left', padx=8)
        self.canvas_gas = tk.Frame(self.tab_gas)
        self.canvas_gas.pack(fill='both', expand=True)

        # Pestaña Comparativa
        self.tab_comp = ttk.Frame(self.nb)
        self.nb.add(self.tab_comp, text="⚖️  Comparativa Saldos")
        self.canvas_comp = tk.Frame(self.tab_comp)
        self.canvas_comp.pack(fill='both', expand=True)

        # Pestaña Datos
        self.tab_data = ttk.Frame(self.nb)
        self.nb.add(self.tab_data, text="📋  Datos")

        # Barra de estado
        self.status = tk.Label(self.root, text="✅ Esperando archivo Excel...",
            bd=1, relief='sunken', anchor='w', font=('Arial', 9), bg='#ECF0F1')
        self.status.pack(fill='x', side='bottom', padx=8, pady=3)

    # ── Helpers ───────────────────────────────────────────────
    def _limpiar(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    def _embed(self, fig, frame, sufijo=""):
        """Incrusta figura en frame con UN SOLO toolbar de guardado."""
        self._limpiar(frame)
        nombre = f"{self.nombre_base}_{sufijo}" if sufijo else self.nombre_base
        canvas = FigureCanvasTkAgg(fig, frame)
        tb = ToolbarGuardar(canvas, frame, nombre_base=nombre)
        tb.update()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        try:
            fig.tight_layout(pad=1.5)
        except Exception:
            pass
        canvas.draw()

    def _sin_datos(self, frame, txt):
        self._limpiar(frame)
        tk.Label(frame, text=txt, font=('Arial', 13), fg='#95A5A6').pack(expand=True)

    def _pantalla_bienvenida(self):
        msg = "📂  Carga un archivo Excel para comenzar\n\nHaz clic en  CARGAR EXCEL  en la barra superior."
        for fr in [self.canvas_evo, self.canvas_ing, self.canvas_gas,
                   self.canvas_comp, self.tab_data]:
            self._limpiar(fr)
            tk.Label(fr, text=msg, font=('Arial', 14), fg='#95A5A6').pack(expand=True)

    # ── Carga Excel ───────────────────────────────────────────
    def _abrir_excel(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo Excel",
            filetypes=[("Excel", "*.xlsx *.xls"), ("Todos", "*.*")])
        if not ruta:
            return
        self.nombre_base = os.path.splitext(os.path.basename(ruta))[0]
        self.lbl_archivo.config(text=f"📁 {os.path.basename(ruta)}", fg='#F0F0F0')
        self.status.config(text="⏳ Cargando…")
        self.btn_cargar.config(state='disabled', text="⏳ Cargando…")
        self.root.update()
        try:
            self._procesar_excel(ruta)
            self.status.config(text=f"✅ {os.path.basename(ruta)} cargado")
            self.btn_cargar.config(state='normal', text="📂  CARGAR EXCEL")
            self.btn_exportar.config(state='normal')
        except Exception as e:
            messagebox.showerror("Error al cargar", str(e))
            self.status.config(text="❌ Error al cargar")
            self.btn_cargar.config(state='normal', text="📂  CARGAR EXCEL")
            self._pantalla_bienvenida()

    def _procesar_excel(self, ruta):
        xl = pd.ExcelFile(ruta)
        self.df_evolucion = self.df_ingresos = self.df_gastos = None
        for hoja in xl.sheet_names:
            hn = hoja.lower()
            df = pd.read_excel(ruta, sheet_name=hoja)
            if any(p in hn for p in ['resumen','evolucion','evolución','anual']):
                self.df_evolucion = self._parse_evolucion(df)
            if any(p in hn for p in ['ingreso','fuentes']):
                self.df_ingresos = self._parse_2col(df, ['Fuente','Importe'])
            if any(p in hn for p in ['gasto','partidas']):
                self.df_gastos = self._parse_2col(df, ['Partida','Importe'])

        if all(x is None for x in [self.df_evolucion, self.df_ingresos, self.df_gastos]):
            raise ValueError(
                "No se encontraron hojas reconocibles.\n"
                "El Excel debe tener hojas:\n"
                "  • 'Resumen', 'Evolución' o 'Anual'\n"
                "  • 'Ingresos' o 'Fuentes'\n"
                "  • 'Gastos' o 'Partidas'")

        if self.df_evolucion is None:
            self.df_evolucion = pd.DataFrame(
                columns=['Año','Ingresos','Gastos','Saldo_Inicial','Saldo_Final'])
        if self.df_ingresos is None:
            self.df_ingresos = pd.DataFrame(columns=['Fuente','Importe'])
        if self.df_gastos is None:
            self.df_gastos = pd.DataFrame(columns=['Partida','Importe'])

        self._dibujar_todo()

    def _parse_evolucion(self, df):
        try:
            años = [c for c in df.columns
                    if str(c).isdigit() or
                    (isinstance(c, (int, float)) and 2000 < c < 2100)]
            if not años:
                return None
            filas = {
                'ing':  df[df.iloc[:,0].astype(str).str.contains('ingreso',        case=False, na=False)],
                'gas':  df[df.iloc[:,0].astype(str).str.contains('gasto',          case=False, na=False)],
                'si':   df[df.iloc[:,0].astype(str).str.contains('saldo.*inicial', case=False, na=False)],
                'sf':   df[df.iloc[:,0].astype(str).str.contains('saldo.*final',   case=False, na=False)],
                'sg':   df[df.iloc[:,0].astype(str).str.contains(r'^saldo$',       case=False, na=False)],
            }
            def _v(k, a):
                f = filas[k]
                return float(f[a].values[0]) if not f.empty else 0.0
            datos = []
            for a in años:
                si = _v('si', a); sf = _v('sf', a)
                if si == 0 and sf == 0:
                    sf = _v('sg', a)
                datos.append({'Año': int(a),
                              'Ingresos':     _v('ing', a),
                              'Gastos':       _v('gas', a),
                              'Saldo_Inicial': si,
                              'Saldo_Final':   sf})
            return pd.DataFrame(datos)
        except Exception as e:
            print(f"[parse_evolucion] {e}"); return None

    def _parse_2col(self, df, cols):
        try:
            out = df.iloc[:,:2].copy()
            out.columns = cols
            out = out.dropna()
            out[cols[1]] = pd.to_numeric(out[cols[1]], errors='coerce')
            out = out[out[cols[1]] > 0].reset_index(drop=True)
            return out if not out.empty else None
        except Exception as e:
            print(f"[parse_2col] {e}"); return None

    def _df_evo(self):
        return self.df_evolucion

    # ── Dibujar / redibujar ───────────────────────────────────
    def _dibujar_todo(self):
        self._dibujar_evolucion()
        self._dibujar_ingresos()
        self._dibujar_gastos()
        self._dibujar_comparativa()
        self._dibujar_tabla()

    def _redibujar_evo_comp(self):
        self._dibujar_evolucion()
        self._dibujar_comparativa()

    def _redibujar_ing(self):
        self._dibujar_ingresos()

    def _redibujar_gas(self):
        self._dibujar_gastos()

    # ═══════════════════════════════════════════════════════════
    #  GRÁFICO 1 – EVOLUCIÓN ANUAL
    # ═══════════════════════════════════════════════════════════
    def _dibujar_evolucion(self):
        df = self._df_evo()
        if df is None or df.empty:
            self._sin_datos(self.canvas_evo, "Sin datos de evolución"); return
        fig = self._fig_evolucion(df)
        self._embed(fig, self.canvas_evo, "Evolucion_Anual")
        plt.close(fig)

    def _fig_evolucion(self, df):
        fig, ax = plt.subplots(figsize=(11, 6))
        x = np.arange(len(df)); w = 0.35
        bi = ax.bar(x-w/2, df['Ingresos'], w, label='Ingresos', color=C['ingresos'], alpha=0.85)
        bg = ax.bar(x+w/2, df['Gastos'],   w, label='Gastos',   color=C['gastos'],   alpha=0.85)
        for b, v in zip(bi, df['Ingresos']):
            if v > 0:
                ax.text(b.get_x()+b.get_width()/2, v/2, f'{v:,.0f}€',
                        ha='center', va='center', fontsize=8, fontweight='bold',
                        color='white', rotation=90)
        for b, v in zip(bg, df['Gastos']):
            if v > 0:
                ax.text(b.get_x()+b.get_width()/2, v/2, f'{v:,.0f}€',
                        ha='center', va='center', fontsize=8, fontweight='bold',
                        color='white', rotation=90)
        ax2 = ax.twinx()
        sc = 'Saldo_Final' if 'Saldo_Final' in df.columns else 'Saldo'
        ax2.plot(x, df[sc], '-^', lw=2.5, ms=9, color=C['saldo_pos'],
                 label='Saldo final', markerfacecolor='white', markeredgewidth=2)
        ms = df[sc].abs().max() if len(df) else 1
        for i, v in enumerate(df[sc]):
            col = C['saldo_pos'] if v >= 0 else C['saldo_neg']
            ax2.text(i, v+ms*0.04, f'{v:,.0f}€', ha='center', va='bottom',
                     fontsize=8, fontweight='bold', color=col,
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                               edgecolor='none', alpha=0.75))
        ax.set_xticks(x); ax.set_xticklabels(df['Año'])
        ax.set_xlabel('Año', fontsize=10)
        ax.set_ylabel('Ingresos / Gastos (€)', fontsize=10)
        ax2.set_ylabel('Saldo Final (€)', fontsize=10)
        ax.set_title('Evolución Anual de la Cuenta', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.25, axis='y')
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_eur))
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_eur))
        l1,lb1 = ax.get_legend_handles_labels()
        l2,lb2 = ax2.get_legend_handles_labels()
        ax.legend(l1+l2, lb1+lb2, loc='upper left', fontsize=9)
        fig.tight_layout()
        return fig

    # ═══════════════════════════════════════════════════════════
    #  GRÁFICO 2 – INGRESOS
    # ═══════════════════════════════════════════════════════════
    def _dibujar_ingresos(self):
        df = self.df_ingresos
        if df is None or df.empty:
            self._sin_datos(self.canvas_ing, "Sin datos de ingresos"); return
        estilo = self.tipo_ingresos.get()
        fig = self._fig_ingresos(df, estilo)
        self._embed(fig, self.canvas_ing, f"Ingresos_{estilo}")
        plt.close(fig)

    def _fig_ingresos(self, df, estilo):
        df_ord = df.sort_values('Importe', ascending=True)
        total  = df_ord['Importe'].sum()
        n      = len(df_ord)
        colores = (PAL_ING * ((n // len(PAL_ING)) + 1))[:n]

        fig, ax = plt.subplots(figsize=(11, max(5, n * 0.42)))
        if estilo == "Tarta":
            wedges, texts, autotexts = ax.pie(
                df_ord['Importe'],
                labels=None,
                autopct='%1.1f%%',
                startangle=140,
                colors=colores,
                wedgeprops={'edgecolor': 'white', 'linewidth': 2},
                pctdistance=0.78)
            for at in autotexts:
                at.set_fontsize(8)
            # Ángulo central leído directamente del wedge → siempre correcto
            r = 1.08
            for wedge, (_, row) in zip(wedges, df_ord.iterrows()):
                ang = np.deg2rad((wedge.theta1 + wedge.theta2) / 2)
                x_lbl = r * np.cos(ang)
                y_lbl = r * np.sin(ang)
                ha = 'left' if x_lbl >= 0 else 'right'
                ax.text(x_lbl, y_lbl + 0.06, row['Fuente'],
                        ha=ha, va='center', fontsize=9, fontweight='bold',
                        color='#2C3E50')
                ax.text(x_lbl, y_lbl - 0.09, f"({row['Importe']:,.0f}€)",
                        ha=ha, va='center', fontsize=7.5, color='#777777')
            ax.set_xlim(-1.55, 1.55)
            ax.set_title(f'Distribución de Ingresos — Total: {total:,.0f}€',
                         fontsize=13, fontweight='bold')
        else:
            y = np.arange(n)
            ax.barh(y, df_ord['Importe'], color=colores)
            mv = df_ord['Importe'].max()
            for i, v in enumerate(df_ord['Importe']):
                pct = v / total * 100
                txt = f'{v:,.0f}€  ({pct:.1f}%)'
                if v > mv * 0.15:
                    ax.text(v/2, i, txt, ha='center', va='center',
                            fontsize=8, fontweight='bold', color='white')
                else:
                    ax.text(v + mv*0.02, i, txt, va='center',
                            fontsize=8, fontweight='bold', color='#2C3E50')
            # Etiquetas eje Y: solo nombre de la fuente
            ax.set_yticks(y)
            ax.set_yticklabels([])
            for i, fuente in enumerate(df_ord['Fuente']):
                ax.annotate(fuente, xy=(0, i), xycoords=('axes fraction', 'data'),
                            xytext=(-8, 0), textcoords='offset points',
                            ha='right', va='center',
                            fontsize=9, color='#2C3E50',
                            annotation_clip=False)
            ax.set_xlabel('Importe (€)', fontsize=10)
            ax.set_xlim(0, mv * 1.42)
            ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_eur))
            ax.grid(True, alpha=0.25, axis='x')
            ax.set_title(f'Ingresos por Fuente — Total: {total:,.0f}€',
                         fontsize=13, fontweight='bold')
            fig.subplots_adjust(left=0.22)
        fig.tight_layout()
        return fig

    # ═══════════════════════════════════════════════════════════
    #  GRÁFICO 3 – GASTOS
    # ═══════════════════════════════════════════════════════════
    def _dibujar_gastos(self):
        df = self.df_gastos
        if df is None or df.empty:
            self._sin_datos(self.canvas_gas, "Sin datos de gastos"); return
        estilo = self.tipo_gastos.get()
        fig = self._fig_gastos(df, estilo)
        self._embed(fig, self.canvas_gas, f"Gastos_{estilo}")
        plt.close(fig)

    def _fig_gastos(self, df, estilo):
        df_ord = df.sort_values('Importe', ascending=True)
        total  = df_ord['Importe'].sum()
        n      = len(df_ord)

        if estilo == "Tarta":
            # ── Tarta ─────────────────────────────────────────
            if n > 10:
                top   = df_ord.iloc[-10:]
                otros = df_ord.iloc[:-10]['Importe'].sum()
                df_plot = pd.concat([
                    pd.DataFrame([{'Partida':'Otros','Importe':otros}]), top
                ], ignore_index=True)
            else:
                df_plot = df_ord
            nm = len(df_plot)
            colores = PAL_GAS(np.linspace(0.15, 0.85, nm))
            fig, ax = plt.subplots(figsize=(10, 7))

            # Etiquetas: "Concepto\n(importe)" — importe en fuente más pequeña
            # Lo conseguimos con dos llamadas de texto después del pie
            wedges, texts, autotexts = ax.pie(
                df_plot['Importe'],
                labels=None,            # sin etiquetas directas del pie
                autopct='%1.1f%%',
                startangle=140,
                colors=colores,
                wedgeprops={'edgecolor':'white','linewidth':1.5},
                pctdistance=0.78)

            # Ángulo central leído directamente del wedge → siempre correcto
            r_label = 1.08
            for wedge, (_, row) in zip(wedges, df_plot.iterrows()):
                ang = np.deg2rad((wedge.theta1 + wedge.theta2) / 2)
                x_lbl = r_label * np.cos(ang)
                y_lbl = r_label * np.sin(ang)
                ha = 'left' if x_lbl >= 0 else 'right'
                ax.text(x_lbl, y_lbl, row['Partida'],
                        ha=ha, va='center', fontsize=9, fontweight='bold',
                        color='#2C3E50')
                ax.text(x_lbl, y_lbl - 0.10, f"({row['Importe']:,.0f}€)",
                        ha=ha, va='center', fontsize=7.5, color='#555555')

            for at in autotexts:
                at.set_fontsize(8)
            ax.set_title(f'Distribución de Gastos — Total: {total:,.0f}€',
                         fontsize=13, fontweight='bold')
            ax.set_xlim(-1.55, 1.55)

        else:
            # ── Barras ────────────────────────────────────────
            colores = PAL_GAS(np.linspace(0.15, 0.85, n))
            fig, ax = plt.subplots(figsize=(12, max(6, n * 0.38)))
            y = np.arange(n)
            ax.barh(y, df_ord['Importe'], color=colores)
            mv = df_ord['Importe'].max()
            for i, v in enumerate(df_ord['Importe']):
                pct = v / total * 100
                ax.text(v + mv*0.02, i, f'{v:,.0f}€  ({pct:.1f}%)',
                        va='center', fontsize=8, fontweight='bold', color='#2C3E50')

            etiquetas = [f"{p}\n({v:,.0f}€)"
                         for p, v in zip(df_ord['Partida'], df_ord['Importe'])]
            ax.set_yticks(y)
            ax.set_yticklabels(etiquetas, fontsize=8, ha='right', multialignment='right')
            ax.tick_params(axis='y', pad=6)
            ax.set_xlabel('Importe (€)', fontsize=10)
            ax.set_xlim(0, mv * 1.30)
            ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_eur))
            ax.grid(True, alpha=0.25, axis='x')
            ax.set_title(f'Partidas de Gasto — Total: {total:,.0f}€',
                         fontsize=13, fontweight='bold')
            # tight_layout con pad extra para que los tick labels no queden cortados
            fig.tight_layout(pad=1.5)
            return fig

        fig.tight_layout()
        return fig

    # ═══════════════════════════════════════════════════════════
    #  GRÁFICO 4 – COMPARATIVA SALDOS
    # ═══════════════════════════════════════════════════════════
    def _dibujar_comparativa(self):
        df = self._df_evo()
        if df is None or df.empty:
            self._sin_datos(self.canvas_comp, "Sin datos de saldos"); return
        fig = self._fig_comparativa(df)
        self._embed(fig, self.canvas_comp, "Comparativa_Saldos")
        plt.close(fig)

    def _fig_comparativa(self, df):
        tiene_ini_fin = ('Saldo_Inicial' in df.columns and
                         df['Saldo_Inicial'].sum() != 0)
        fig, ax = plt.subplots(figsize=(11, 6))
        x = np.arange(len(df)); w = 0.35

        if tiene_ini_fin:
            bi = ax.bar(x-w/2, df['Saldo_Inicial'], w, label='Saldo Inicial',
                        color=C['saldo_ini'], alpha=0.75)
            bf = ax.bar(x+w/2, df['Saldo_Final'],   w, label='Saldo Final',
                        color=C['saldo_fin'], alpha=0.75)
            for b, v in zip(bi, df['Saldo_Inicial']):
                if v > 0:
                    ax.text(b.get_x()+b.get_width()/2, v/2, f'{v:,.0f}€',
                            ha='center', va='center', fontsize=8,
                            fontweight='bold', color='white', rotation=90)
            for b, v in zip(bf, df['Saldo_Final']):
                if v > 0:
                    ax.text(b.get_x()+b.get_width()/2, v/2, f'{v:,.0f}€',
                            ha='center', va='center', fontsize=8,
                            fontweight='bold', color='white', rotation=90)
            ms = max(df['Saldo_Final'].max(), df['Saldo_Inicial'].max())
            for i, (ini, fin) in enumerate(zip(df['Saldo_Inicial'], df['Saldo_Final'])):
                diff = fin - ini
                col  = C['saldo_pos'] if diff >= 0 else C['saldo_neg']
                ax.plot([i-w/2, i+w/2], [ini, fin], 'k--', alpha=0.4)
                ax.text(i, max(ini,fin)+ms*0.04, f'{diff:+,.0f}€',
                        ha='center', fontsize=9, fontweight='bold', color=col,
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
            ax.set_title('Comparativa: Saldo Inicial vs Saldo Final',
                         fontsize=13, fontweight='bold')
            ax.legend(fontsize=9)
        else:
            sc = 'Saldo_Final' if 'Saldo_Final' in df.columns else 'Saldo'
            cols_b = [C['saldo_pos'] if v >= 0 else C['saldo_neg'] for v in df[sc]]
            ax.bar(x, df[sc], color=cols_b, alpha=0.82)
            ax.axhline(0, color='black', lw=0.6, alpha=0.4)
            ms = df[sc].abs().max() if len(df) else 1
            for i, v in enumerate(df[sc]):
                col = C['saldo_pos'] if v >= 0 else C['saldo_neg']
                off = ms*0.04 if v >= 0 else -ms*0.09
                ax.text(i, v+off, f'{v:+,.0f}€', ha='center', fontsize=9,
                        fontweight='bold', color=col,
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                  edgecolor=col, alpha=0.9))
            ax.set_title('Saldo Anual', fontsize=13, fontweight='bold')

        ax.set_xticks(x); ax.set_xticklabels(df['Año'])
        ax.set_xlabel('Año', fontsize=10)
        ax.set_ylabel('Saldo (€)', fontsize=10)
        ax.grid(True, alpha=0.25, axis='y')
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_eur))
        fig.tight_layout()
        return fig

    # ═══════════════════════════════════════════════════════════
    #  TABLA DE DATOS
    # ═══════════════════════════════════════════════════════════
    def _dibujar_tabla(self):
        self._limpiar(self.tab_data)
        nb2 = ttk.Notebook(self.tab_data)
        nb2.pack(fill='both', expand=True, padx=4, pady=4)

        for titulo, df, col_txt in [
            ("Gastos",    self.df_gastos,    'Partida'),
            ("Ingresos",  self.df_ingresos,  'Fuente'),
            ("Evolución", self.df_evolucion, None),
        ]:
            tab = ttk.Frame(nb2)
            nb2.add(tab, text=titulo)
            if df is None or df.empty:
                tk.Label(tab, text=f"Sin datos de {titulo.lower()}",
                         font=('Arial', 11)).pack(expand=True)
                continue

            # ── Cabecera total (si aplica) ──
            if 'Importe' in df.columns:
                tk.Label(tab, text=f"TOTAL: {df['Importe'].sum():,.0f}€",
                         font=('Arial', 10, 'bold'), fg='#27AE60',
                         anchor='w').pack(fill='x', padx=10, pady=(4, 0))

            # ── Contenedor con scroll ──
            outer = tk.Frame(tab)
            outer.pack(fill='both', expand=True, padx=6, pady=4)

            canvas_t = tk.Canvas(outer, highlightthickness=0)
            vsb = ttk.Scrollbar(outer, orient='vertical', command=canvas_t.yview)
            canvas_t.configure(yscrollcommand=vsb.set)
            vsb.pack(side='right', fill='y')
            canvas_t.pack(side='left', fill='both', expand=True)

            inner = tk.Frame(canvas_t, bg='white')
            win_id = canvas_t.create_window((0, 0), window=inner, anchor='nw')
            inner.bind('<Configure>',
                       lambda e, c=canvas_t: c.configure(
                           scrollregion=c.bbox('all')))
            # Ancho del inner = mínimo entre ancho del canvas y un máximo razonable
            def _sync_width(event, c=canvas_t, w=win_id):
                new_w = min(event.width, 500)
                c.itemconfig(w, width=new_w)
            canvas_t.bind('<Configure>', _sync_width)

            cols = list(df.columns)
            # Columnas numéricas (todas menos col_txt)
            cols_num = [c for c in cols if c != col_txt]

            # ── Encabezados ──
            bg_head = '#D5D8DC'
            if col_txt:
                tk.Label(inner, text=col_txt, font=('Arial', 8, 'bold'),
                         bg=bg_head, anchor='w', padx=6, pady=3,
                         relief='flat').grid(row=0, column=0, sticky='ew', padx=(0,1))
            for j, c in enumerate(cols_num):
                tk.Label(inner, text=c, font=('Arial', 8, 'bold'),
                         bg=bg_head, anchor='e', padx=6, pady=3,
                         relief='flat').grid(row=0, column=j+(1 if col_txt else 0),
                                             sticky='ew', padx=(0,1))

            # ── Filas ──
            for i, (_, row) in enumerate(df.iterrows()):
                bg = 'white' if i % 2 == 0 else '#F2F3F4'
                if col_txt:
                    tk.Label(inner, text=str(row[col_txt]),
                             font=('Arial', 8), bg=bg, anchor='w',
                             padx=6, pady=2).grid(row=i+1, column=0,
                                                  sticky='ew', padx=(0,1))
                for j, c in enumerate(cols_num):
                    v = row[c]
                    if isinstance(v, float) and c != 'Año':
                        txt = f'{v:,.0f}€'
                    else:
                        txt = '' if (isinstance(v, float) and np.isnan(v)) else str(v)
                    tk.Label(inner, text=txt, font=('Arial', 8), bg=bg,
                             anchor='e', padx=6, pady=2).grid(
                                 row=i+1, column=j+(1 if col_txt else 0),
                                 sticky='ew', padx=(0,1))

            # La columna de texto (col 0) se estira; las numéricas tienen ancho fijo
            if col_txt:
                inner.grid_columnconfigure(0, weight=1, minsize=120)
                for j in range(len(cols_num)):
                    inner.grid_columnconfigure(j+1, weight=0, minsize=80)
            else:
                for j in range(len(cols)):
                    inner.grid_columnconfigure(j, weight=1, minsize=80)

    # ═══════════════════════════════════════════════════════════
    #  EXPORTAR TODO (6 gráficos: barras + tarta para ing/gas)
    # ═══════════════════════════════════════════════════════════
    def _exportar_todos(self):
        if all(x is None for x in [self.df_evolucion, self.df_ingresos, self.df_gastos]):
            messagebox.showwarning("Sin datos", "Carga un archivo Excel primero.")
            return
        carpeta = filedialog.askdirectory(title="Carpeta de destino")
        if not carpeta:
            return

        self.status.config(text="⏳ Exportando…"); self.root.update()

        df_evo = self._df_evo()
        df_ing = self.df_ingresos
        df_gas = self.df_gastos

        tareas = []
        if df_evo is not None and not df_evo.empty:
            tareas.append(("Evolucion_Anual",    lambda: self._fig_evolucion(df_evo)))
            tareas.append(("Comparativa_Saldos", lambda: self._fig_comparativa(df_evo)))
        if df_ing is not None and not df_ing.empty:
            tareas.append(("Ingresos_Barras", lambda: self._fig_ingresos(df_ing, "Barras")))
            tareas.append(("Ingresos_Tarta",  lambda: self._fig_ingresos(df_ing, "Tarta")))
        if df_gas is not None and not df_gas.empty:
            tareas.append(("Gastos_Barras",   lambda: self._fig_gastos(df_gas, "Barras")))
            tareas.append(("Gastos_Tarta",    lambda: self._fig_gastos(df_gas, "Tarta")))

        ok, errores = [], []
        for sufijo, fn in tareas:
            ruta = os.path.join(carpeta, f"{self.nombre_base}_{sufijo}.png")
            try:
                fig = fn()
                if fig is not None:
                    fig.savefig(ruta, dpi=150, bbox_inches='tight')
                    plt.close(fig)
                    ok.append(os.path.basename(ruta))
            except Exception as e:
                errores.append(f"{sufijo}: {e}")

        self.status.config(text=f"✅ {len(ok)} gráficos exportados")
        msg = f"✅ {len(ok)} gráficos guardados en:\n{carpeta}\n\n"
        msg += "\n".join(f"  • {f}" for f in ok)
        if errores:
            msg += "\n\n⚠️ Errores:\n" + "\n".join(errores)
        if messagebox.askyesno("Exportación completa", msg + "\n\n¿Abrir carpeta?"):
            if   os.name == 'nt':          os.startfile(carpeta)
            elif sys.platform == 'darwin':  subprocess.Popen(['open', carpeta])
            else:                           subprocess.Popen(['xdg-open', carpeta])


# ──────────────────────────────────────────────────────────────
#  PUNTO DE ENTRADA
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    AplicacionGraficos(root)
    root.mainloop()
