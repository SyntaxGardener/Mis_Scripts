import tkinter as tk
from tkinter import messagebox, filedialog
from docx import Document

class PasapalabraPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Pasapalabra / Alphabetical")

        ancho_ventana = 850
        alto_ventana = 760
        ancho_pantalla = self.root.winfo_screenwidth()
        pos_x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        pos_y = 0
        self.root.geometry(f"{ancho_ventana}x{alto_ventana}+{pos_x}+{pos_y}")
        self.root.configure(bg="#1e272e")

        self.datos = []
        self.total_palabras = 0
        self.indice = 0
        self.aciertos = 0
        self.fallos = 0
        self.tiempo_total = 150
        self.timer_id = None
        self.juego_activo = False

        self.main_container = tk.Frame(self.root, bg="#1e272e")
        self.main_container.pack(expand=True, fill="both")

        self.mostrar_pantalla_inicio()

    def mostrar_pantalla_inicio(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

        self.juego_activo = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

        tk.Label(self.main_container, text="PASAPALABRA", font=("Arial", 50, "bold"),
                 bg="#1e272e", fg="#f1c40f").pack(pady=(50, 10))
        tk.Label(self.main_container, text="Configura tu partida", font=("Arial", 14),
                 bg="#1e272e", fg="white").pack(pady=10)

        self.frame_tiempo = tk.Frame(self.main_container, bg="#1e272e")
        self.frame_tiempo.pack(pady=20)
        tk.Label(self.frame_tiempo, text="Segundos totales:", font=("Arial", 12),
                 bg="#1e272e", fg="#95a5a6").pack(side="left")
        self.entry_tiempo = tk.Entry(self.frame_tiempo, font=("Arial", 14), width=5, justify="center")
        self.entry_tiempo.insert(0, "150")
        self.entry_tiempo.pack(side="left", padx=10)

        tk.Button(self.main_container, text="Cargar Word y Comenzar",
                  font=("Arial", 16, "bold"), bg="#2ecc71", fg="white",
                  padx=30, pady=15, command=self.validar_y_cargar,
                  relief="flat", cursor="hand2").pack(pady=20)

        tk.Label(self.main_container, text="ENTER para comprobar  |  TAB o ESC para Pasapalabra",
                 font=("Arial", 10), bg="#1e272e", fg="#95a5a6").pack(pady=20)

    def validar_y_cargar(self):
        try:
            self.tiempo_total = int(self.entry_tiempo.get())
            self.cargar_y_empezar()
        except ValueError:
            messagebox.showerror("Error", "Por favor, introduce un numero valido para el tiempo.")

    def cargar_y_empezar(self):
        archivo = filedialog.askopenfilename(
            title="Selecciona el archivo Word",
            filetypes=[("Documentos de Word", "*.docx")])
        if not archivo:
            return

        try:
            doc = Document(archivo)
            self.datos = []
            tabla = doc.tables[0]
            for i, fila in enumerate(tabla.rows):
                if i == 0:
                    continue
                celdas = [c.text.strip() for c in fila.cells]
                if len(celdas) >= 3 and celdas[1] and celdas[2]:
                    self.datos.append({
                        "letra": celdas[0].upper(),
                        "pista": celdas[1],
                        "correcta": celdas[2]
                    })

            if self.datos:
                self.total_palabras = len(self.datos)
                self.indice = 0
                self.aciertos = 0
                self.fallos = 0
                self.setup_ui_juego()
                self.juego_activo = True
                self.mostrar_pregunta()
                self.actualizar_reloj_global()   # arranca el reloj una sola vez
            else:
                messagebox.showwarning("Aviso", "Tabla no valida.")
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def setup_ui_juego(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

        # ── Reloj centrado ────────────────────────────────────────────────
        header = tk.Frame(self.main_container, bg="#1e272e")
        header.pack(fill="x", padx=40, pady=(20, 5))

        self.lbl_timer = tk.Label(header, text=f"  {self.tiempo_total}s",
                                  font=("Arial", 28, "bold"), bg="#1e272e", fg="#f39c12")
        self.lbl_timer.pack()

        # ── Marcador: 4 bloques de estadisticas ───────────────────────────
        stats = tk.Frame(self.main_container, bg="#1e272e")
        stats.pack(fill="x", padx=40, pady=(0, 10))

        def stat_bloque(parent, titulo, color):
            f = tk.Frame(parent, bg="#2c3e50", padx=18, pady=8)
            f.pack(side="left", expand=True, fill="x", padx=6)
            tk.Label(f, text=titulo, font=("Arial", 9), bg="#2c3e50", fg="#95a5a6").pack()
            lbl = tk.Label(f, text="0", font=("Arial", 22, "bold"), bg="#2c3e50", fg=color)
            lbl.pack()
            return lbl

        self.lbl_total     = stat_bloque(stats, "TOTAL",        "#ecf0f1")
        self.lbl_acertadas = stat_bloque(stats, "ACERTADAS",    "#2ecc71")
        self.lbl_falladas  = stat_bloque(stats, "FALLADAS",     "#e74c3c")
        self.lbl_restantes = stat_bloque(stats, "PENDIENTES",   "#3498db")

        # ── Letra grande ──────────────────────────────────────────────────
        self.lbl_letra = tk.Label(self.main_container, text="", font=("Arial", 110, "bold"),
                                  bg="#1e272e", fg="#f1c40f")
        self.lbl_letra.pack()

        # ── Pista ─────────────────────────────────────────────────────────
        self.lbl_pista = tk.Label(self.main_container, text="", font=("Arial", 22, "italic"),
                                  bg="#1e272e", fg="white", wraplength=700)
        self.lbl_pista.pack(pady=6)

        # ── Mensaje de error ──────────────────────────────────────────────
        self.lbl_error = tk.Label(self.main_container, text="", font=("Arial", 14, "bold"),
                                  bg="#1e272e", fg="#e74c3c")
        self.lbl_error.pack(pady=3)

        # ── Campo de respuesta ────────────────────────────────────────────
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(self.main_container, textvariable=self.entry_var,
                              font=("Arial", 32), justify="center", width=15,
                              bg="#34495e", fg="white", borderwidth=0, insertbackground="white")
        self.entry.pack(pady=8)
        self.entry.focus_set()

        tk.Button(self.main_container, text="PASAPALABRA  (Tab / Esc)",
                  font=("Arial", 14, "bold"), bg="#3498db", fg="white",
                  padx=20, pady=8, command=self.pasapalabra, relief="flat").pack(pady=12)

        # ── Atajos de teclado ─────────────────────────────────────────────
        self.root.bind('<Return>', lambda e: self.comprobar())
        self.root.bind('<Tab>',    lambda e: (self.pasapalabra(), "break")[1])
        self.root.bind('<Escape>', lambda e: self.pasapalabra())

    # ── Reloj ──────────────────────────────────────────────────────────────
    def actualizar_reloj_global(self):
        if not self.juego_activo:
            # Reloj en pausa (durante fallo); reintenta en 200 ms
            self.timer_id = self.root.after(200, self.actualizar_reloj_global)
            return
        if self.tiempo_total > 0:
            self.tiempo_total -= 1
            color = "#e74c3c" if self.tiempo_total <= 10 else "#f39c12"
            self.lbl_timer.config(text=f"  {self.tiempo_total}s", fg=color)
            self.timer_id = self.root.after(1000, self.actualizar_reloj_global)
        else:
            self.finalizar_juego("TIEMPO AGOTADO")

    # ── Actualiza las 4 estadisticas ──────────────────────────────────────
    def actualizar_stats(self):
        pendientes = len(self.datos) - self.indice
        self.lbl_total.config(text=str(self.total_palabras))
        self.lbl_acertadas.config(text=str(self.aciertos))
        self.lbl_falladas.config(text=str(self.fallos))
        self.lbl_restantes.config(text=str(max(pendientes, 0)))

    # ── Muestra la pregunta actual ────────────────────────────────────────
    def mostrar_pregunta(self):
        if self.indice < len(self.datos):
            p = self.datos[self.indice]
            self.lbl_letra.config(text=p["letra"], fg="#f1c40f")
            self.lbl_pista.config(text=p["pista"])
            self.lbl_error.config(text="")
            self.entry_var.set("")
            self.entry.config(state="normal")
            self.entry.focus_set()
            self.juego_activo = True
            self.actualizar_stats()
        else:
            self.finalizar_juego("HAS COMPLETADO EL ROSCO")

    # ── Comprueba la respuesta ────────────────────────────────────────────
    def comprobar(self):
        if self.entry.cget("state") == "disabled" or not self.juego_activo:
            return
        res_usuario  = self.entry_var.get().strip().lower()
        res_correcta = self.datos[self.indice]["correcta"].lower()

        if res_usuario == res_correcta:
            self.indice += 1
            self.aciertos += 1
            self.mostrar_pregunta()
        else:
            self.mostrar_fallo(f"Incorrecto - era: {res_correcta.upper()}")

    # ── Pasapalabra ───────────────────────────────────────────────────────
    def pasapalabra(self, event=None):
        if self.juego_activo:
            palabra_saltada = self.datos.pop(self.indice)
            self.datos.append(palabra_saltada)
            self.mostrar_pregunta()

    # ── Gestion de fallo ──────────────────────────────────────────────────
    def mostrar_fallo(self, mensaje):
        self.juego_activo = False          # pausa el reloj
        self.fallos += 1
        self.entry.config(state="disabled")
        self.lbl_letra.config(fg="#e74c3c")
        self.lbl_error.config(text=mensaje)
        self.actualizar_stats()
        self.root.after(1500, self.siguiente_automatico)

    def siguiente_automatico(self):
        if self.tiempo_total > 0:
            self.indice += 1
            self.mostrar_pregunta()        # reactiva juego_activo; el reloj retoma solo

    # ── Fin de partida ────────────────────────────────────────────────────
    def finalizar_juego(self, motivo):
        self.juego_activo = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        sin_responder = self.total_palabras - self.aciertos - self.fallos
        resumen = (
            f"{motivo}\n\n"
            f"Total de palabras : {self.total_palabras}\n"
            f"Acertadas         : {self.aciertos}\n"
            f"Falladas          : {self.fallos}\n"
            f"Sin responder     : {sin_responder}"
        )
        messagebox.showinfo("Resultados", resumen)
        self.mostrar_pantalla_inicio()


if __name__ == "__main__":
    root = tk.Tk()
    app = PasapalabraPro(root)
    root.mainloop()
