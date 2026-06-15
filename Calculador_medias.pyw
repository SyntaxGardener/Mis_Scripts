import pdfplumber
import pandas as pd
import re
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import threading
import subprocess
import sys
from datetime import datetime

# --- LÓGICA DE EXTRACCIÓN ---
CONVERSION = {'SB': 9.5, 'NT': 8, 'BI': 6.5, 'SU': 5.5, 'IN': 4.0, 'NP': 0.0}
ANIOS_VALIDOS = [f"{anio}/{anio+1}" for anio in range(2024, 2035)]

def limpiar_nombre(nombre):
    nombre = re.sub(r'\s+Nº.*$', '', nombre)
    nombre = re.sub(r'\s+identificacion.*$', '', nombre)
    nombre = re.sub(r'\s*\(\d+\)\s*$', '', nombre)
    return nombre.strip()

def encontrar_nombre(lineas):
    for i, linea in enumerate(lineas[:20]):
        if 'Apellidos y nombre:' in linea:
            return limpiar_nombre(linea.split('Apellidos y nombre:')[-1])
    for i, linea in enumerate(lineas[:15]):
        if 'CERTIFICADO ACADÉMICO OFICIAL DEL ALUMNO:' in linea:
            return limpiar_nombre(linea.split('DEL ALUMNO:')[-1])
        if 'CERTIFICADO ACADÉMICO OFICIAL DE LA ALUMNA:' in linea:
            return limpiar_nombre(linea.split('DE LA ALUMNA:')[-1])
    return None

PATRON_LINEA = re.compile(
    r'^(ACT|AC|AS)\s+(.+?)\s+(?:\b(?:SB|NT|BI|SU|IN|NP)\b)'
)
PATRON_NOTAS = re.compile(r'\b(SB|NT|BI|SU|IN|NP)\b')

def procesar_pdf(ruta_pdf, log_func):
    alumnos = {}
    with pdfplumber.open(ruta_pdf) as pdf:
        for num_pagina, pagina in enumerate(pdf.pages, 1):
            texto = pagina.extract_text()
            if not texto:
                continue
            lineas = texto.split('\n')
            nombre = encontrar_nombre(lineas)
            if not nombre:
                continue
            if nombre not in alumnos:
                alumnos[nombre] = {'ACT': {}, 'AC': {}, 'AS': {}}
                log_func(f"  📍 Página {num_pagina}: {nombre}")
            for linea in lineas:
                if not any(anio in linea for anio in ANIOS_VALIDOS):
                    continue
                m = PATRON_LINEA.match(linea.strip())
                if not m:
                    continue
                ambito = m.group(1)
                modulo = m.group(2).strip()
                notas_linea = PATRON_NOTAS.findall(linea)
                if not notas_linea:
                    continue
                mejor_valor = max(CONVERSION[n] for n in notas_linea)
                prev = alumnos[nombre][ambito].get(modulo)
                if prev is None or mejor_valor > prev:
                    alumnos[nombre][ambito][modulo] = mejor_valor
    return alumnos


def calcular_medias(datos_alumno, exentos):
    """
    datos_alumno: dict {'ACT': {...}, 'AC': {...}, 'AS': {...}}
    exentos: set con los ámbitos a ignorar, p.ej. {'ACT'} o {'AC', 'AS'}
    Devuelve (m_act, m_ac, m_as, m_global)
    """
    def media_ambito(ambito):
        if ambito in exentos:
            return None
        vals = list(datos_alumno[ambito].values())
        return sum(vals) / len(vals) if vals else None

    m_act = media_ambito('ACT')
    m_ac  = media_ambito('AC')
    m_as  = media_ambito('AS')
    validas  = [m for m in [m_act, m_ac, m_as] if m is not None]
    m_global = sum(validas) / len(validas) if validas else None
    return m_act, m_ac, m_as, m_global


# --- INTERFAZ GRÁFICA ---

class DialogoExenciones(tk.Toplevel):
    """
    Ventana modal que muestra todos los alumnos encontrados y permite
    marcar qué ámbitos están exentos por prueba libre de la ESO.
    """
    def __init__(self, parent, alumnos_total):
        super().__init__(parent)
        self.title("Revisión de exenciones por prueba libre")
        self.resizable(False, False)
        self.grab_set()  # modal

        # Centrar sobre la ventana padre
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        w, h = 680, 520
        self.geometry(f"{w}x{h}+{px + (pw-w)//2}+{py + (ph-h)//2}")

        self.alumnos_total = alumnos_total
        self.resultado = None  # None = cancelado; dict = confirmado

        # Vars tkinter: {nombre: {'ACT': BooleanVar, 'AC': BooleanVar, 'AS': BooleanVar}}
        self.vars = {}

        # ── Cabecera ────────────────────────────────────────────────────────
        tk.Label(
            self,
            text="Exenciones por prueba libre de la ESO",
            font=("Arial", 12, "bold")
        ).pack(pady=(14, 2))
        tk.Label(
            self,
            text=(
                "Marca los ámbitos que el alumno/a superó en prueba libre.\n"
                "Esos ámbitos se excluirán del cálculo de la media."
            ),
            font=("Arial", 9),
            fg="#555"
        ).pack(pady=(0, 8))

        # ── Tabla con scroll ─────────────────────────────────────────────────
        contenedor = tk.Frame(self)
        contenedor.pack(fill="both", expand=True, padx=16)

        canvas = tk.Canvas(contenedor, borderwidth=0, highlightthickness=0)
        scroll = tk.Scrollbar(contenedor, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.frame_tabla = tk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=self.frame_tabla, anchor="nw")

        def on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        self.frame_tabla.bind("<Configure>", on_frame_configure)

        def on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)
        canvas.bind("<Configure>", on_canvas_configure)

        # Cabecera de columnas
        for col, (txt, w) in enumerate([
            ("Alumno/a", 340), ("ACT exento", 90), ("AC exento", 90), ("AS exento", 90)
        ]):
            tk.Label(
                self.frame_tabla,
                text=txt, width=w//8,
                font=("Arial", 9, "bold"),
                bg="#2E7D32", fg="white",
                anchor="w", padx=6, pady=4
            ).grid(row=0, column=col, sticky="ew", padx=1, pady=(0,2))

        # Filas por alumno
        for fila, nombre in enumerate(sorted(alumnos_total.keys()), start=1):
            self.vars[nombre] = {a: tk.BooleanVar(value=False) for a in ['ACT', 'AC', 'AS']}
            bg = "#f5f5f5" if fila % 2 == 0 else "white"

            tk.Label(
                self.frame_tabla,
                text=nombre, anchor="w",
                font=("Arial", 9), bg=bg, padx=6, pady=3
            ).grid(row=fila, column=0, sticky="ew")

            for col, ambito in enumerate(['ACT', 'AC', 'AS'], start=1):
                # Solo mostrar checkbox si el alumno tiene datos en ese ámbito
                tiene_datos = bool(alumnos_total[nombre][ambito])
                if tiene_datos:
                    tk.Checkbutton(
                        self.frame_tabla,
                        variable=self.vars[nombre][ambito],
                        bg=bg, activebackground=bg
                    ).grid(row=fila, column=col, sticky="", pady=3)
                else:
                    # Sin datos en ese ámbito: no tiene sentido exentarlo
                    tk.Label(
                        self.frame_tabla,
                        text="—", fg="#bbb",
                        font=("Arial", 9), bg=bg
                    ).grid(row=fila, column=col, sticky="", pady=3)

        # ── Botones ─────────────────────────────────────────────────────────
        frame_btns = tk.Frame(self)
        frame_btns.pack(pady=12)

        tk.Button(
            frame_btns,
            text="Ninguna exención (todos los ámbitos cuentan)",
            command=self._ninguna,
            font=("Arial", 9), padx=10, pady=5,
            bg="#888888", fg="white"
        ).pack(side="left", padx=8)

        tk.Button(
            frame_btns,
            text="✔  Confirmar y calcular",
            command=self._confirmar,
            font=("Arial", 10, "bold"), padx=14, pady=6,
            bg="#2E7D32", fg="white"
        ).pack(side="left", padx=8)

    def _ninguna(self):
        """Desmarca todo y confirma."""
        for nombre in self.vars:
            for ambito in self.vars[nombre]:
                self.vars[nombre][ambito].set(False)
        self._confirmar()

    def _confirmar(self):
        """Lee los checkboxes y construye el dict de exentos."""
        # resultado: {nombre: set_de_ambitos_exentos}
        self.resultado = {}
        for nombre, ambitos in self.vars.items():
            exentos = {a for a, var in ambitos.items() if var.get()}
            self.resultado[nombre] = exentos
        self.destroy()


class AppCalculadora:
    def __init__(self, root):
        self.root = root
        self.root.title("Calculadora de Notas Medias LOMLOE")

        ancho = 820
        alto = 715
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+10")
        self.root.resizable(False, False)

        self.archivos_seleccionados = []
        self.resultados_calculados = []
        self.alumnos_total_raw = {}   # datos brutos tras procesar PDFs
        self.exenciones = {}          # {nombre: set_ambitos_exentos}
        self.ruta_excel_guardada = None

        self.COLORES = {
            'limpiar':   {'on': ('#c0392b', 'white'), 'off': ('#e8b5b0', '#888888')},
            'calcular':  {'on': ('#2E7D32', 'white'), 'off': ('#a5c8a7', '#666666')},
            'guardar':   {'on': ('#6A1B9A', 'white'), 'off': ('#c9a8e0', '#666666')},
        }
        self._limpiar_activo  = False
        self._calcular_activo = False
        self._guardar_activo  = False

        # ── Título ──────────────────────────────────────────────────────────
        tk.Label(
            root,
            text="Calculadora de Notas Medias  ·  Expedientes ESPA(D)",
            font=("Arial", 13, "bold")
        ).pack(pady=(12, 4))

        # ── PASO 1: Cargar archivos ──────────────────────────────────────────
        frame1 = tk.LabelFrame(root, text=" Paso 1 · Cargar expedientes PDF ", padx=10, pady=8)
        frame1.pack(pady=6, padx=20, fill="x")

        fila_btn = tk.Frame(frame1)
        fila_btn.pack(fill="x")

        self.btn_cargar = tk.Button(
            fila_btn,
            text="📂  Seleccionar PDF (1 o más)",
            command=self.seleccionar_pdfs,
            bg="#1565C0", fg="white",
            font=("Arial", 10, "bold"),
            padx=14, pady=6
        )
        self.btn_cargar.pack(side="left")

        self.btn_limpiar = tk.Button(
            fila_btn,
            text="✖  Limpiar selección",
            command=self.limpiar_seleccion,
            bg=self.COLORES['limpiar']['off'][0], fg=self.COLORES['limpiar']['off'][1],
            font=("Arial", 10),
            padx=10, pady=6
        )
        self.btn_limpiar.pack(side="left", padx=(8, 0))

        self.lbl_archivos = tk.Label(
            frame1,
            text="Ningún archivo seleccionado.",
            fg="#555", font=("Arial", 9), anchor="w", justify="left"
        )
        self.lbl_archivos.pack(fill="x", pady=(6, 0))

        # ── PASO 2: Calcular ─────────────────────────────────────────────────
        frame2 = tk.LabelFrame(root, text=" Paso 2 · Calcular notas medias ", padx=10, pady=8)
        frame2.pack(pady=6, padx=20, fill="x")

        self.btn_calcular = tk.Button(
            frame2,
            text="▶  CALCULAR",
            command=self.iniciar_calculo,
            bg=self.COLORES['calcular']['off'][0], fg=self.COLORES['calcular']['off'][1],
            font=("Arial", 11, "bold"),
            padx=20, pady=8
        )
        self.btn_calcular.pack(anchor="w")

        self.console = scrolledtext.ScrolledText(
            frame2,
            state='disabled', height=18, width=90,
            bg="#1e1e1e", fg="#00FF00",
            font=("Consolas", 9)
        )
        self.console.pack(pady=(8, 0))

        # ── PASO 3: Guardar resultado ────────────────────────────────────────
        frame3 = tk.LabelFrame(root, text=" Paso 3 · Guardar resultado ", padx=10, pady=8)
        frame3.pack(pady=6, padx=20, fill="x")

        fila_dest = tk.Frame(frame3)
        fila_dest.pack(fill="x", pady=(0, 6))

        tk.Label(fila_dest, text="Carpeta de destino:", font=("Arial", 9)).pack(side="left")

        self.entry_dest = tk.Entry(fila_dest, width=58)
        self.entry_dest.pack(side="left", padx=(6, 8), expand=True, fill="x")
        self.entry_dest.insert(0, os.getcwd())

        tk.Button(
            fila_dest, text="Cambiar",
            command=self.seleccionar_destino,
            padx=8
        ).pack(side="left")

        fila_guardar = tk.Frame(frame3)
        fila_guardar.pack(fill="x")

        self.btn_guardar = tk.Button(
            fila_guardar,
            text="💾  Guardar Excel",
            command=self.guardar_excel,
            bg=self.COLORES['guardar']['off'][0], fg=self.COLORES['guardar']['off'][1],
            font=("Arial", 10, "bold"),
            padx=14, pady=6
        )
        self.btn_guardar.pack(side="left")

        self.var_abrir_carpeta = tk.BooleanVar(value=False)
        self.chk_abrir = tk.Checkbutton(
            fila_guardar,
            text="Abrir carpeta al terminar",
            variable=self.var_abrir_carpeta,
            font=("Arial", 9)
        )
        self.chk_abrir.pack(side="left", padx=(16, 0))

        self.lbl_guardado = tk.Label(
            frame3, text="", fg="#2E7D32",
            font=("Arial", 9, "italic"), anchor="w"
        )
        self.lbl_guardado.pack(fill="x", pady=(4, 0))

        # ── Pie de página ────────────────────────────────────────────────────
        tk.Label(
            root,
            text="CEPA Suroccidente",
            font=("Arial", 8, "italic"),
            fg="#999999"
        ).pack(side="bottom", pady=(0, 6))

    # ── Métodos ──────────────────────────────────────────────────────────────

    def _set_btn(self, btn, key, activo):
        estado = 'on' if activo else 'off'
        bg, fg = self.COLORES[key][estado]
        btn.config(bg=bg, fg=fg)
        btn._habilitado = activo

    def _btn_habilitado(self, btn):
        return getattr(btn, '_habilitado', False)

    def seleccionar_pdfs(self):
        archivos = filedialog.askopenfilenames(
            title="Selecciona los expedientes PDF",
            filetypes=[("Archivos PDF", "*.pdf")]
        )
        if archivos:
            self.archivos_seleccionados = list(archivos)
            n = len(archivos)
            nombres = "\n  · ".join(os.path.basename(f) for f in archivos[:10])
            extra = f"\n  ... y {n - 10} más." if n > 10 else ""
            self.lbl_archivos.config(
                text=f"{n} archivo(s) seleccionado(s):\n  · {nombres}{extra}",
                fg="#1a5276"
            )
            self._set_btn(self.btn_calcular, 'calcular', True)
            self._set_btn(self.btn_limpiar,  'limpiar',  True)
            self.resultados_calculados = []
            self.alumnos_total_raw = {}
            self.exenciones = {}
            self._set_btn(self.btn_guardar, 'guardar', False)
            self.lbl_guardado.config(text="")
            self.limpiar_consola()

    def limpiar_seleccion(self):
        if not self._btn_habilitado(self.btn_limpiar):
            return
        self.archivos_seleccionados = []
        self.resultados_calculados = []
        self.alumnos_total_raw = {}
        self.exenciones = {}
        self.lbl_archivos.config(text="Ningún archivo seleccionado.", fg="#555")
        self._set_btn(self.btn_calcular, 'calcular', False)
        self._set_btn(self.btn_limpiar,  'limpiar',  False)
        self._set_btn(self.btn_guardar,  'guardar',  False)
        self.lbl_guardado.config(text="")
        self.limpiar_consola()

    def seleccionar_destino(self):
        directorio = filedialog.askdirectory()
        if directorio:
            self.entry_dest.delete(0, tk.END)
            self.entry_dest.insert(0, directorio)

    def limpiar_consola(self):
        self.console.config(state='normal')
        self.console.delete(1.0, tk.END)
        self.console.config(state='disabled')

    def log(self, mensaje):
        self.console.config(state='normal')
        self.console.insert(tk.END, mensaje + "\n")
        self.console.see(tk.END)
        self.console.config(state='disabled')
        self.root.update_idletasks()

    def iniciar_calculo(self):
        if not self._btn_habilitado(self.btn_calcular):
            return
        if not self.archivos_seleccionados:
            messagebox.showwarning("Aviso", "No hay archivos seleccionados.")
            return
        self._set_btn(self.btn_calcular, 'calcular', False)
        self._set_btn(self.btn_cargar,   'limpiar',  False)
        self._set_btn(self.btn_guardar,  'guardar',  False)
        self.btn_cargar.config(bg="#a0bcd8", fg="#555555")
        self.limpiar_consola()
        threading.Thread(target=self.ejecutar_calculo, daemon=True).start()

    def ejecutar_calculo(self):
        alumnos_total = {}
        self.log("=" * 70 + "\n📄 PROCESANDO EXPEDIENTES...\n" + "=" * 70)

        for ruta_pdf in self.archivos_seleccionados:
            nombre_pdf = os.path.basename(ruta_pdf)
            self.log(f"\n📁 Archivo: {nombre_pdf}")
            try:
                nuevos = procesar_pdf(ruta_pdf, self.log)
                for nombre, datos in nuevos.items():
                    if nombre not in alumnos_total:
                        alumnos_total[nombre] = {'ACT': {}, 'AC': {}, 'AS': {}}
                    for ambito in ['ACT', 'AC', 'AS']:
                        for modulo, valor in datos[ambito].items():
                            prev = alumnos_total[nombre][ambito].get(modulo)
                            if prev is None or valor > prev:
                                alumnos_total[nombre][ambito][modulo] = valor
            except Exception as e:
                self.log(f"  ❌ Error: {e}")

        if not alumnos_total:
            self.log("\n❌ No se encontraron datos válidos en los archivos.")
            self._set_btn(self.btn_calcular, 'calcular', True)
            self.btn_cargar.config(bg="#1565C0", fg="white")
            return

        self.alumnos_total_raw = alumnos_total
        self.log(f"\n✅ Extracción completada. {len(alumnos_total)} alumno(s) encontrado(s).")
        self.log("Abriendo pantalla de exenciones...")

        # Abrir el diálogo de exenciones en el hilo principal
        self.root.after(0, self._abrir_dialogo_exenciones)

    def _abrir_dialogo_exenciones(self):
        """Lanza el diálogo modal y, cuando se cierra, continúa con el cálculo."""
        dialogo = DialogoExenciones(self.root, self.alumnos_total_raw)
        self.root.wait_window(dialogo)

        if dialogo.resultado is None:
            # El usuario cerró la ventana sin confirmar → cancelar
            self.log("\n⚠️  Cálculo cancelado por el usuario.")
            self._set_btn(self.btn_calcular, 'calcular', True)
            self.btn_cargar.config(bg="#1565C0", fg="white")
            return

        self.exenciones = dialogo.resultado
        # Continuar el cálculo en un hilo para no bloquear la UI
        threading.Thread(target=self._calcular_medias_y_mostrar, daemon=True).start()

    def _calcular_medias_y_mostrar(self):
        resultados = []
        self.log("\n" + "=" * 70 + "\n📊 RESULTADOS\n" + "=" * 70)

        for nombre, datos in self.alumnos_total_raw.items():
            exentos = self.exenciones.get(nombre, set())
            m_act, m_ac, m_as, m_global = calcular_medias(datos, exentos)

            self.log(f"\n👤 Alumno/a: {nombre}")

            if exentos:
                self.log(f"  ⚠️  Ámbitos exentos (prueba libre): {', '.join(sorted(exentos))}")

            for ambito, media, etiqueta in [
                ('ACT', m_act, 'ACT'),
                ('AC',  m_ac,  'AC '),
                ('AS',  m_as,  'AS '),
            ]:
                if ambito in exentos:
                    self.log(f"  {etiqueta}: [EXCLUIDO — exento por prueba libre]")
                elif media is not None:
                    detalle = ", ".join(
                        f"{mod}: {v}" for mod, v in datos[ambito].items()
                    )
                    n = len(datos[ambito])
                    self.log(f"  {etiqueta} ({n} módulos): {detalle} → Media: {media:.2f}")

            if m_global is not None:
                self.log(f"  ▶ MEDIA GLOBAL: {m_global:.2f}")

            resultados.append({
                'Nombre':       nombre,
                'Media ACT':    round(m_act,    2) if m_act    is not None else None,
                'Media AC':     round(m_ac,     2) if m_ac     is not None else None,
                'Media AS':     round(m_as,     2) if m_as     is not None else None,
                'Media Global': round(m_global, 2) if m_global is not None else None,
                'Exentos':      ", ".join(sorted(exentos)) if exentos else "—",
            })

        self.resultados_calculados = resultados
        self.log("\n" + "=" * 70)
        self.log(f"✅ Cálculo completado. {len(resultados)} alumno(s) procesado(s).")
        self.log("Puedes guardar el resultado en el Paso 3.")

        self._set_btn(self.btn_guardar,  'guardar',  True)
        self._set_btn(self.btn_calcular, 'calcular', True)
        self.btn_cargar.config(bg="#1565C0", fg="white")

    def guardar_excel(self):
        if not self._btn_habilitado(self.btn_guardar):
            return
        dest_folder = self.entry_dest.get()
        if not os.path.isdir(dest_folder):
            messagebox.showerror("Error", "La carpeta de destino no es válida.")
            return
        if not self.resultados_calculados:
            messagebox.showwarning("Aviso", "No hay resultados para guardar. Ejecuta primero el cálculo.")
            return

        ahora = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"Medias_ESPAD_{ahora}.xlsx"
        ruta_final = os.path.join(dest_folder, nombre_archivo)

        try:
            pd.DataFrame(self.resultados_calculados).to_excel(ruta_final, index=False)
            self.lbl_guardado.config(text=f"✅ Guardado: {nombre_archivo}")
            self.log(f"\n💾 Excel guardado: {ruta_final}")
            messagebox.showinfo("Guardado", f"Archivo guardado en:\n{ruta_final}")

            if self.var_abrir_carpeta.get():
                if sys.platform == "win32":
                    os.startfile(dest_folder)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", dest_folder])
                else:
                    subprocess.Popen(["xdg-open", dest_folder])

        except Exception as e:
            self.log(f"❌ Error al guardar: {e}")
            messagebox.showerror("Error al guardar", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = AppCalculadora(root)
    root.mainloop()
