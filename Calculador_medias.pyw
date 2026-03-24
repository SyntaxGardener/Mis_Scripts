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
CONVERSION = {'SB': 9.5, 'NT': 8.5, 'BI': 6.5, 'SU': 5.5, 'IN': 4.0, 'NP': 0.0}
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

# Regex principal: captura ámbito y nombre de módulo.
# Formato de línea: "ACT Materia y fuerza IN SU 1 2024/2025"
#   - puede haber UNA nota (solo ordinaria) o DOS (ordinaria + extraordinaria)
#   - tomamos TODAS las notas de la línea y nos quedamos con el valor más alto
# \b evita que NT coincida dentro de 'Entornos' o IN dentro de 'Inecuaciones'.
PATRON_LINEA = re.compile(
    r'^(ACT|AC|AS)\s+(.+?)\s+(?:\b(?:SB|NT|BI|SU|IN|NP)\b)'
)
# Busca todos los tokens de nota en cualquier parte de la línea
PATRON_NOTAS = re.compile(r'\b(SB|NT|BI|SU|IN|NP)\b')

def procesar_pdf(ruta_pdf, log_func):
    # Cada ámbito es ahora un dict {nombre_modulo: mejor_valor}
    # para poder aplicar la regla "si hay dos notas, cuenta la más alta".
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
                # Filtro rápido: la línea debe contener un año válido
                if not any(anio in linea for anio in ANIOS_VALIDOS):
                    continue
                m = PATRON_LINEA.match(linea.strip())
                if not m:
                    continue
                ambito = m.group(1)          # 'ACT', 'AC' o 'AS'
                modulo = m.group(2).strip()  # nombre del módulo
                # Extraer TODAS las notas de la línea (ordinaria y/o extraordinaria)
                # y quedarse con el valor más alto
                notas_linea = PATRON_NOTAS.findall(linea)
                if not notas_linea:
                    continue
                mejor_valor = max(CONVERSION[n] for n in notas_linea)
                # Actualizar solo si mejora la nota ya registrada para ese módulo
                prev = alumnos[nombre][ambito].get(modulo)
                if prev is None or mejor_valor > prev:
                    alumnos[nombre][ambito][modulo] = mejor_valor
    return alumnos


# --- INTERFAZ GRÁFICA ---

class AppCalculadora:
    def __init__(self, root):
        self.root = root
        self.root.title("Calculadora de Notas Medias LOMLOE")

        ancho = 820
        alto = 715
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+10")
        self.root.resizable(False, False)

        # Estado interno
        self.archivos_seleccionados = []
        self.resultados_calculados = []
        self.ruta_excel_guardada = None

        # Colores activo/inactivo por botón (para evitar el gris feo de Windows)
        self.COLORES = {
            'limpiar':   {'on': ('#c0392b', 'white'), 'off': ('#e8b5b0', '#888888')},
            'calcular':  {'on': ('#2E7D32', 'white'), 'off': ('#a5c8a7', '#666666')},
            'guardar':   {'on': ('#6A1B9A', 'white'), 'off': ('#c9a8e0', '#666666')},
        }
        # Flags de habilitación manual
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
            text="📂  Seleccionar PDFs",
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
        """Habilita o deshabilita un botón visualmente sin usar state=disabled."""
        estado = 'on' if activo else 'off'
        bg, fg = self.COLORES[key][estado]
        btn.config(bg=bg, fg=fg)
        # Guardamos el flag en un atributo del propio botón
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
            # Resetear estado previo
            self.resultados_calculados = []
            self._set_btn(self.btn_guardar, 'guardar', False)
            self.lbl_guardado.config(text="")
            self.limpiar_consola()

    def limpiar_seleccion(self):
        if not self._btn_habilitado(self.btn_limpiar):
            return
        self.archivos_seleccionados = []
        self.resultados_calculados = []
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
        self._set_btn(self.btn_cargar,   'limpiar',  False)  # reutilizamos paleta apagada
        self._set_btn(self.btn_guardar,  'guardar',  False)
        self.btn_cargar.config(bg="#a0bcd8", fg="#555555")   # apagado neutro para btn_cargar
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
                    # Fusionar dicts: si el mismo módulo aparece en dos PDFs,
                    # conservar el valor más alto.
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

        resultados = []
        self.log("\n" + "=" * 70 + "\n📊 RESULTADOS\n" + "=" * 70)

        for nombre, datos in alumnos_total.items():
            self.log(f"\n👤 Alumno/a: {nombre}")
            vals_act = list(datos['ACT'].values())
            vals_ac  = list(datos['AC'].values())
            vals_as  = list(datos['AS'].values())
            m_act = sum(vals_act) / len(vals_act) if vals_act else None
            m_ac  = sum(vals_ac)  / len(vals_ac)  if vals_ac  else None
            m_as  = sum(vals_as)  / len(vals_as)  if vals_as  else None

            if m_act is not None:
                detalle = ", ".join(
                    f"{mod}: {v}" for mod, v in datos['ACT'].items()
                )
                self.log(f"  ACT ({len(vals_act)} módulos): {detalle} → Media: {m_act:.2f}")
            if m_ac is not None:
                detalle = ", ".join(
                    f"{mod}: {v}" for mod, v in datos['AC'].items()
                )
                self.log(f"  AC  ({len(vals_ac)} módulos): {detalle} → Media: {m_ac:.2f}")
            if m_as is not None:
                detalle = ", ".join(
                    f"{mod}: {v}" for mod, v in datos['AS'].items()
                )
                self.log(f"  AS  ({len(vals_as)} módulos): {detalle} → Media: {m_as:.2f}")

            validas  = [m for m in [m_act, m_ac, m_as] if m is not None]
            m_global = sum(validas) / len(validas) if validas else None
            if m_global is not None: self.log(f"  ▶ MEDIA GLOBAL: {m_global:.2f}")

            resultados.append({
                'Nombre':       nombre,
                'Media ACT':    round(m_act,    2) if m_act    is not None else "N/A",
                'Media AC':     round(m_ac,     2) if m_ac     is not None else "N/A",
                'Media AS':     round(m_as,     2) if m_as     is not None else "N/A",
                'Media Global': round(m_global, 2) if m_global is not None else "N/A"
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
