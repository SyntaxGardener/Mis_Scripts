import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import subprocess
import sys
import os

# ── Dependencias opcionales (se instalan si faltan) ──────────────────────────
def _ensure(pkg, import_as=None):
    name = import_as or pkg
    try:
        __import__(name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for p, i in [("pandas", None), ("openpyxl", None), ("matplotlib", None), ("numpy", None)]:
    _ensure(p, i)

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Normalización de movimientos ──────────────────────────────────────────────
MOVIMIENTO_MAP = {
    'romanticismo': 'ROMANTICISMO',
    'realismo': 'REALISMO',
    'naturalismo': 'NATURALISMO',
    'modernismo': 'MODERNISMO',
    'generacion del 98': 'GENERACION DEL 98',
    'generación del 98': 'GENERACION DEL 98',
    'generacion del 27': 'GENERACION DEL 27',
    'generación del 27': 'GENERACION DEL 27',
    'generacion del 36': 'GENERACION DEL 36',
    'generación del 36': 'GENERACION DEL 36',
    'posguerra': 'POSGUERRA',
    'siglo de oro': 'SIGLO DE ORO',
    'barroco': 'BARROCO',
    'ilustracion': 'ILUSTRACION',
    'ilustración': 'ILUSTRACION',
    'costumbrismo': 'COSTUMBRISMO',
    'surrealismo': 'SURREALISMO',
    'existencialismo': 'EXISTENCIALISMO',
    'posromanticismo': 'ROMANTICISMO',
    'novecentismo': 'NOVECENTISMO',
    'vanguardismo': 'VANGUARDISMO',
}

def normalizar_movimiento(mov):
    if pd.isna(mov):
        return 'SIN CLASIFICAR'
    key = str(mov).strip().lower()
    for k, v in MOVIMIENTO_MAP.items():
        if k in key:
            return v
    return 'SIN CLASIFICAR'


# ── Función principal: carga datos y genera el gráfico ───────────────────────
def generar_timeline(excel_path, carpeta_salida):
    """Lee el Excel, limpia los datos y guarda el gráfico PNG."""

    # ── Carga ──────────────────────────────────────────────────────────────
    df = pd.read_excel(excel_path)

    # Normaliza nombres de columnas (acepta variantes con tildes, mayúsculas…)
    df.columns = [c.strip() for c in df.columns]
    col_map = {}
    for c in df.columns:
        cl = c.lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        if 'nombre' in cl or 'autor' in cl or 'escritor' in cl:
            col_map[c] = 'Nombre'
        elif 'nac' in cl:
            col_map[c] = 'Nacimiento'
        elif 'fall' in cl or 'muerte' in cl or 'defun' in cl:
            col_map[c] = 'Fallecimiento'
        elif 'movim' in cl or 'corriente' in cl or 'periodo' in cl:
            col_map[c] = 'Movimiento'
    df = df.rename(columns=col_map)

    columnas_req = ['Nombre', 'Nacimiento', 'Fallecimiento']
    for c in columnas_req:
        if c not in df.columns:
            raise ValueError(f"No se encontró la columna '{c}' en el Excel.\n"
                             f"Columnas disponibles: {list(df.columns)}")

    if 'Movimiento' not in df.columns:
        df['Movimiento'] = 'SIN CLASIFICAR'

    # ── Limpieza ───────────────────────────────────────────────────────────
    df['Nacimiento']    = pd.to_numeric(df['Nacimiento'],    errors='coerce')
    df['Fallecimiento'] = pd.to_numeric(df['Fallecimiento'], errors='coerce')
    df = df.dropna(subset=['Nacimiento', 'Fallecimiento'])
    df = df[df['Fallecimiento'] > df['Nacimiento']]
    df['Movimiento_Normalizado'] = df['Movimiento'].apply(normalizar_movimiento)
    df = df.sort_values('Nacimiento').reset_index(drop=True)

    if df.empty:
        raise ValueError("El archivo Excel no contiene filas válidas con fechas de nacimiento y fallecimiento.")

    # ── Gráfico ────────────────────────────────────────────────────────────
    colores_movimientos = {
        'ROMANTICISMO':      '#FADADD',
        'REALISMO':          '#C9E4DE',
        'NATURALISMO':       '#C9E4DE',
        'MODERNISMO':        '#E0BBE4',
        'GENERACION DEL 98': '#FFE5B4',
        'GENERACION DEL 27': '#B5EAD7',
        'GENERACION DEL 36': '#FFD1DC',
        'POSGUERRA':         '#C7E9C0',
        'SIGLO DE ORO':      '#FFE5B4',
        'BARROCO':           '#FBC8B5',
        'ILUSTRACION':       '#D4F1F9',
        'COSTUMBRISMO':      '#FDE2C4',
        'SURREALISMO':       '#E6CCE6',
        'EXISTENCIALISMO':   '#C9E9C9',
        'NOVECENTISMO':      '#A8D4B0',
        'VANGUARDISMO':      '#F4AEBA',
        'SIN CLASIFICAR':    '#E8E8E8',
    }
    colores_auto  = ['#FBC8B5', '#D4F1F9', '#E6CCE6', '#FDE2C4', '#C9E9C9', '#FFE5B4']
    color_idx     = 0
    colores_extra = {}

    num_escritores  = len(df)
    alto_figura     = max(8, num_escritores * 0.45)
    fig, ax         = plt.subplots(figsize=(16, alto_figura), facecolor='white')

    ax.invert_yaxis()
    ax.set_yticks([])
    ax.set_facecolor('#FAFAFA')

    for i, (_, row) in enumerate(df.iterrows()):
        nombre     = str(row['Nombre'])
        nac        = float(row['Nacimiento'])
        fall       = float(row['Fallecimiento'])
        movimiento = row['Movimiento_Normalizado']
        duracion   = fall - nac

        if movimiento in colores_movimientos:
            color = colores_movimientos[movimiento]
        else:
            if movimiento not in colores_extra:
                colores_extra[movimiento] = colores_auto[color_idx % len(colores_auto)]
                color_idx += 1
            color = colores_extra[movimiento]

        ax.barh(i, duracion, left=nac, color=color, edgecolor='#AAAAAA',
                linewidth=0.8, height=0.7, alpha=0.85)

        # Etiqueta del nombre dentro o fuera de la barra
        umbral_chars = max(len(nombre) * 0.55, 8)
        if duracion > umbral_chars:
            ax.text(nac + duracion / 2, i, nombre,
                    va='center', ha='center', fontsize=8.5, fontweight='bold',
                    color='#2C3E50',
                    bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.6))
        else:
            ax.text(fall + 2, i, nombre,
                    va='center', ha='left', fontsize=8.5, fontweight='bold',
                    color='#2C3E50')

        ax.text(nac - 2, i, str(int(nac)), va='center', ha='right',
                fontsize=7.5, color='#666666')
        ax.text(fall + 2 if duracion <= umbral_chars else fall + 1,
                i, str(int(fall)), va='center',
                ha='left' if duracion <= umbral_chars else 'right',
                fontsize=7.5, color='#666666')

    ax.set_xlabel('AÑO', fontsize=11, fontweight='bold', color='#2C3E50')
    ax.set_title('LÍNEA DE TIEMPO DE ESCRITORES\n(Nacimiento → Fallecimiento)',
                 fontsize=15, fontweight='bold', pad=18, color='#2C3E50')
    ax.grid(axis='x', linestyle='--', alpha=0.3, color='#CCCCCC')

    x_min = max(0, df['Nacimiento'].min() - 15)
    x_max = df['Fallecimiento'].max() + 20
    ax.set_xlim(x_min, x_max)

    span     = x_max - x_min
    intervalo = 10 if span <= 150 else (20 if span <= 400 else 50)
    x_ticks  = np.arange(np.floor(x_min / intervalo) * intervalo,
                         x_max + intervalo, intervalo)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels([str(int(t)) for t in x_ticks], fontsize=8)

    if x_min <= 1900 <= x_max:
        ax.axvline(x=1900, color='#D32F2F', linewidth=2, alpha=0.65, zorder=5)
        ax.text(1900, ax.get_ylim()[0] * 0.98, '1900',
                ha='center', va='top', fontsize=8,
                color='#D32F2F', fontweight='bold')

    # Leyenda
    todos_movs   = list(df['Movimiento_Normalizado'].unique())
    leyenda_pats = []
    for mov in sorted(todos_movs):
        c    = colores_movimientos.get(mov, colores_extra.get(mov, '#E8E8E8'))
        etiq = df[df['Movimiento_Normalizado'] == mov]['Movimiento'].iloc[0]
        leyenda_pats.append(mpatches.Patch(color=c, label=str(etiq), edgecolor='#AAAAAA'))

    if leyenda_pats:
        ax.legend(handles=leyenda_pats, title="MOVIMIENTOS LITERARIOS",
                  loc='center left', bbox_to_anchor=(1.01, 0.5),
                  fontsize=8.5, title_fontsize=9.5,
                  frameon=True, fancybox=True, shadow=True)

    plt.tight_layout()

    nombre_archivo = "timeline_escritores.png"
    ruta_salida    = os.path.join(carpeta_salida, nombre_archivo)
    fig.savefig(ruta_salida, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    return ruta_salida


# ── Interfaz gráfica ──────────────────────────────────────────────────────────
class App(tk.Tk):
    FONDO       = "#F5F7FA"
    PANEL       = "#FFFFFF"
    ACENTO      = "#1565C0"
    TEXTO       = "#212121"
    TEXTO_DIM   = "#607D8B"
    BORDE       = "#CFD8DC"
    BTN_NORMAL  = "#E3EAF6"
    BTN_HOVER   = "#C5D5EF"
    BTN_RUN     = "#1565C0"
    BTN_RUN_HOV = "#1976D2"
    FUENTE      = ("Segoe UI", 10)
    FUENTE_T    = ("Segoe UI", 13, "bold")

    def __init__(self):
        super().__init__()
        self.title("Timeline · Escritores")
        self.resizable(False, False)
        self.configure(bg=self.FONDO)
        self._excel_var         = tk.StringVar()
        self._carpeta_var       = tk.StringVar()
        self._abrir_img_var     = tk.BooleanVar(value=True)
        self._abrir_carpeta_var = tk.BooleanVar(value=False)
        self._build_ui()
        self._center_top()

    def _build_ui(self):
        tk.Frame(self, bg=self.ACENTO, height=4).pack(fill="x")

        header = tk.Frame(self, bg=self.FONDO)
        header.pack(fill="x", padx=24, pady=(18, 6))
        tk.Label(header, text="📊", font=("Segoe UI Emoji", 24),
                 bg=self.FONDO, fg=self.ACENTO).pack(side="left", padx=(0, 10))
        tb = tk.Frame(header, bg=self.FONDO)
        tb.pack(side="left")
        tk.Label(tb, text="Timeline de escritores",
                 font=self.FUENTE_T, bg=self.FONDO, fg=self.TEXTO).pack(anchor="w")
        tk.Label(tb, text="Genera un gráfico de barras desde un Excel",
                 font=("Segoe UI", 8), bg=self.FONDO, fg=self.TEXTO_DIM).pack(anchor="w")

        tk.Frame(self, bg=self.BORDE, height=1).pack(fill="x", padx=24, pady=(10, 16))

        card = tk.Frame(self, bg=self.PANEL,
                        highlightthickness=1, highlightbackground=self.BORDE)
        card.pack(fill="x", padx=24, pady=(0, 12))
        inner = tk.Frame(card, bg=self.PANEL)
        inner.pack(fill="x", padx=16, pady=14)
        self._fila(inner, "Archivo Excel:",     self._excel_var,   self._elegir_excel,   0)
        self._fila(inner, "Carpeta de salida:", self._carpeta_var, self._elegir_carpeta, 1)

        chk_f  = tk.Frame(self, bg=self.FONDO)
        chk_f.pack(fill="x", padx=28, pady=(2, 6))
        chk_kw = dict(bg=self.FONDO, fg=self.TEXTO, selectcolor=self.PANEL,
                      activebackground=self.FONDO, activeforeground=self.TEXTO,
                      font=self.FUENTE, relief="flat", bd=0, cursor="hand2", anchor="w")
        tk.Checkbutton(chk_f, text="Abrir imagen al finalizar",
                       variable=self._abrir_img_var, **chk_kw
                       ).grid(row=0, column=0, sticky="w", pady=2)
        tk.Checkbutton(chk_f, text="Abrir carpeta de destino al finalizar",
                       variable=self._abrir_carpeta_var, **chk_kw
                       ).grid(row=1, column=0, sticky="w", pady=2)

        tk.Frame(self, bg=self.BORDE, height=1).pack(fill="x", padx=24, pady=(8, 14))

        btn_f = tk.Frame(self, bg=self.FONDO)
        btn_f.pack(padx=24, pady=(0, 6))
        self._btn_run = tk.Button(
            btn_f, text="  Generar timeline  ",
            font=("Segoe UI", 11, "bold"),
            bg=self.BTN_RUN, fg="white",
            activebackground=self.BTN_RUN_HOV, activeforeground="white",
            relief="flat", bd=0, cursor="hand2",
            padx=22, pady=10, command=self._run)
        self._btn_run.pack()
        self._btn_run.bind("<Enter>", lambda e: self._btn_run.config(bg=self.BTN_RUN_HOV))
        self._btn_run.bind("<Leave>", lambda e: self._btn_run.config(bg=self.BTN_RUN))

        self._status = tk.Label(self, text="", font=("Segoe UI", 9, "italic"),
                                bg=self.FONDO, fg=self.TEXTO_DIM)
        self._status.pack(pady=(4, 14))

    def _fila(self, parent, label, var, cmd, fila):
        tk.Label(parent, text=label, font=("Segoe UI", 9),
                 bg=self.PANEL, fg=self.TEXTO_DIM, anchor="w"
                 ).grid(row=fila*2, column=0, columnspan=2,
                        sticky="w", pady=(0, 3))
        e = tk.Entry(parent, textvariable=var, width=46,
                     bg="#F0F4F8", fg=self.TEXTO,
                     insertbackground=self.ACENTO,
                     relief="flat", bd=0, font=("Consolas", 9),
                     highlightthickness=1,
                     highlightcolor=self.ACENTO,
                     highlightbackground=self.BORDE)
        e.grid(row=fila*2+1, column=0, sticky="ew",
               ipady=6, padx=(0, 8), pady=(0, 12))
        b = tk.Button(parent, text="Examinar…", font=("Segoe UI", 9),
                      bg=self.BTN_NORMAL, fg=self.ACENTO,
                      activebackground=self.BTN_HOVER, activeforeground=self.ACENTO,
                      relief="flat", bd=0, cursor="hand2",
                      padx=10, pady=5, command=cmd)
        b.grid(row=fila*2+1, column=1, pady=(0, 12))
        b.bind("<Enter>", lambda e, btn=b: btn.config(bg=self.BTN_HOVER))
        b.bind("<Leave>", lambda e, btn=b: btn.config(bg=self.BTN_NORMAL))
        parent.columnconfigure(0, weight=1)

    def _center_top(self):
        self.update_idletasks()
        w  = self.winfo_reqwidth()
        sw = self.winfo_screenwidth()
        self.geometry(f"+{(sw - w) // 2}+5")

    def _elegir_excel(self):
        p = filedialog.askopenfilename(
            title="Selecciona el archivo Excel",
            filetypes=[("Excel", "*.xlsx *.xls *.xlsm"), ("Todos", "*.*")])
        if p:
            self._excel_var.set(p)
            if not self._carpeta_var.get():
                self._carpeta_var.set(os.path.dirname(p))

    def _elegir_carpeta(self):
        p = filedialog.askdirectory(title="Carpeta de destino")
        if p:
            self._carpeta_var.set(p)

    def _run(self):
        excel   = self._excel_var.get().strip()
        carpeta = self._carpeta_var.get().strip()
        if not excel or not os.path.isfile(excel):
            messagebox.showwarning("Falta el Excel", "Selecciona un archivo Excel válido.")
            return
        if not carpeta or not os.path.isdir(carpeta):
            messagebox.showwarning("Falta la carpeta", "Selecciona una carpeta de destino.")
            return
        self._btn_run.config(state="disabled", text="  Generando…  ")
        self._status.config(text="Procesando datos y renderizando el gráfico…",
                            fg=self.TEXTO_DIM)
        self.update()
        threading.Thread(target=self._tarea, args=(excel, carpeta), daemon=True).start()

    def _tarea(self, excel, carpeta):
        try:
            ruta = generar_timeline(excel, carpeta)
            self.after(0, self._ok, ruta)
        except Exception as exc:
            self.after(0, self._error, str(exc))

    def _ok(self, ruta):
        carpeta = os.path.dirname(ruta)
        self._btn_run.config(state="normal", text="  Generar timeline  ")
        self._status.config(text=f"✓ Guardado en: {os.path.basename(ruta)}", fg="#2E7D32")

        def _abrir(path, es_carpeta=False):
            if sys.platform == "win32":
                if es_carpeta:
                    subprocess.Popen(["explorer", os.path.normpath(path)])
                else:
                    os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])

        if self._abrir_img_var.get():
            _abrir(ruta)
        if self._abrir_carpeta_var.get():
            _abrir(carpeta, es_carpeta=True)

        messagebox.showinfo("¡Listo!", f"Timeline generado correctamente:\n{ruta}")

    def _error(self, msg):
        self._btn_run.config(state="normal", text="  Generar timeline  ")
        self._status.config(text="✗ Error al generar el gráfico.", fg="#C62828")
        messagebox.showerror("Error", f"No se pudo generar el timeline:\n\n{msg}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
