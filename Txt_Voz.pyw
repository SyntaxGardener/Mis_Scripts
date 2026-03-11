import sys
import os
import re
import unicodedata

def lanzar_aplicacion():
    try:
        import ctypes
        ctypes.windll.kernel32.FreeConsole()
    except: pass

    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

    import warnings
    warnings.filterwarnings("ignore")
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    import threading
    import asyncio
    import edge_tts
    import pygame
    from pypdf import PdfReader
    import docx2txt
    from deep_translator import GoogleTranslator

    pygame.mixer.init()

    class LectorPro:
        def __init__(self, root):
            self.root = root
            self.root.title("Lector + Traductor")
            ancho_ventana = 600
            alto_ventana = 550
            distancia_superior = 10

            # USAR 'root' en lugar de 'ventana'
            ancho_pantalla = root.winfo_screenwidth()

            # Calcular la posición X para que esté centrada
            posicion_x = (ancho_pantalla // 2) - (ancho_ventana // 2)

            # Aplicar la geometría a 'root'
            root.geometry(f"{ancho_ventana}x{alto_ventana}+{posicion_x}+{distancia_superior}")
            
            self.voces_disponibles = []
            self.filtros = {
                "España (ES)": "es-ES", "México (MX)": "es-MX",
                "Inglés USA": "en-US", "Inglés UK": "en-GB", 
                "Francés": "fr-FR", "Alemán": "de-DE", "Italiano": "it-IT"
            }

            self.crear_ui()
            threading.Thread(target=self.obtener_voces, daemon=True).start()

        def crear_ui(self):
            frame = ttk.Frame(self.root, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)

            # --- TEXTO ---
            ttk.Label(frame, text="Texto:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
            self.txt = tk.Text(frame, height=8, wrap=tk.WORD)
            self.txt.pack(fill=tk.X, pady=5)
            self.txt.bind("<KeyRelease>", lambda e: self.actualizar_sugerencia())
            
            btn_docs = ttk.Frame(frame)
            btn_docs.pack(fill=tk.X)
            ttk.Button(btn_docs, text="📁 Abrir Archivo", command=self.leer_file).pack(side=tk.LEFT, expand=True, fill=tk.X)
            ttk.Button(btn_docs, text="✨ Limpiar", command=lambda: self.txt.delete("1.0", tk.END)).pack(side=tk.LEFT, fill=tk.X)

            ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=15)

            # --- TRADUCTOR ---
            ttk.Label(frame, text="Traductor Rápido:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
            f_trad = ttk.Frame(frame)
            f_trad.pack(fill=tk.X, pady=5)
            
            self.c_hacia = ttk.Combobox(f_trad, values=["spanish", "english", "french", "german", "italian"], state="readonly")
            self.c_hacia.set("english")
            self.c_hacia.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,5))
            
            ttk.Button(f_trad, text="Traducir Texto", command=self.lanzar_traduccion).pack(side=tk.LEFT)

            ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=15)

            # --- VOZ ---
            ttk.Label(frame, text="Configuración de Voz:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
            self.c_pais = ttk.Combobox(frame, values=list(self.filtros.keys()), state="readonly")
            self.c_pais.set("España (ES)")
            self.c_pais.pack(fill=tk.X, pady=5)
            self.c_pais.bind("<<ComboboxSelected>>", lambda e: self.llenar_voces())

            self.c_voz = ttk.Combobox(frame, state="readonly")
            self.c_voz.pack(fill=tk.X, pady=5)

            # --- NOMBRE Y GUARDADO ---
            ttk.Label(frame, text="Nombre del MP3:", font=('Arial', 9, 'bold')).pack(anchor=tk.W, pady=(10,0))
            self.ent_nombre = ttk.Entry(frame)
            self.ent_nombre.pack(fill=tk.X, pady=5)

            btn_f = ttk.Frame(frame)
            btn_f.pack(fill=tk.X, pady=20)
            ttk.Button(btn_f, text="▶ Oír", command=self.previa).pack(side=tk.LEFT, expand=True, fill=tk.X)
            ttk.Button(btn_f, text="⏹ Parar", command=self.detener_audio).pack(side=tk.LEFT, expand=True, fill=tk.X)
            ttk.Button(btn_f, text="💾 GUARDAR", command=self.salvar).pack(side=tk.LEFT, expand=True, fill=tk.X)

        def detener_audio(self):
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()

        def lanzar_traduccion(self):
            texto_orig = self.txt.get("1.0", tk.END).strip()
            if not texto_orig: return
            
            idioma_destino = self.c_hacia.get()
            
            def proce_trad():
                try:
                    traducido = GoogleTranslator(source='auto', target=idioma_destino).translate(texto_orig)
                    self.root.after(0, lambda: self.finalizar_traduccion(traducido))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", "No hay conexión a internet."))

            threading.Thread(target=proce_trad, daemon=True).start()

        def finalizar_traduccion(self, texto):
            self.txt.delete("1.0", tk.END)
            self.txt.insert(tk.END, texto)
            self.actualizar_sugerencia()
            
            # Cambiar el selector de país automáticamente
            mapping = {"english": "Inglés USA", "spanish": "España (ES)", "french": "Francés", "german": "Alemán", "italian": "Italiano"}
            if self.c_hacia.get() in mapping:
                self.c_pais.set(mapping[self.c_hacia.get()])
            
            self.llenar_voces()
            messagebox.showinfo("Traductor", "Traducción terminada. Ahora selecciona una voz y pulsa Oír.")

        def actualizar_sugerencia(self):
            texto = self.txt.get("1.0", "1.50").strip()
            limpio = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
            palabras = re.findall(r'[a-zA-Z0-9]+', limpio)
            if palabras:
                self.ent_nombre.delete(0, tk.END)
                self.ent_nombre.insert(0, "_".join(palabras[:3]))

        def obtener_voces(self):
            try:
                loop = asyncio.new_event_loop()
                v = loop.run_until_complete(edge_tts.VoicesManager.create())
                self.voces_disponibles = v.voices
                self.root.after(0, self.llenar_voces)
            except: pass

        def llenar_voces(self):
            cod = self.filtros.get(self.c_pais.get(), "es-ES")
            lista = [f"{v['ShortName']} ({'M' if v['Gender']=='Male' else 'F'})" for v in self.voces_disponibles if cod in v['ShortName']]
            self.c_voz['values'] = lista
            if lista: self.c_voz.current(0)

        def leer_file(self):
            f = filedialog.askopenfilename(filetypes=[("Docs", "*.txt *.docx *.pdf")])
            if f:
                ext = os.path.splitext(f)[1].lower()
                t = ""
                if ext == ".txt":
                    with open(f, 'r', encoding='utf-8') as file: t = file.read()
                elif ext == ".docx": t = docx2txt.process(f)
                elif ext == ".pdf":
                    r = PdfReader(f)
                    t = "\n".join([p.extract_text() for p in r.pages if p.extract_text()])
                self.txt.delete("1.0", tk.END)
                self.txt.insert(tk.END, t.strip())
                self.actualizar_sugerencia()

        def previa(self):
            self.detener_audio()
            tx = self.txt.get("1.0", tk.END).strip()
            # Si el texto es muy largo, para la previa solo usamos una parte para que no tarde
            if len(tx) > 1000: tx = tx[:1000]
            
            v_info = self.c_voz.get()
            if not tx or not v_info: 
                messagebox.showwarning("Aviso", "Asegúrate de tener texto y una voz seleccionada.")
                return
            
            v = v_info.split(" ")[0]
            threading.Thread(target=lambda: asyncio.run(self.generar(tx, v, "tmp.mp3", True)), daemon=True).start()

        def salvar(self):
            contenido = self.txt.get("1.0", tk.END).strip()
            nombre_base = self.ent_nombre.get().strip()
            v_info = self.c_voz.get()
            
            if not contenido or not nombre_base or not v_info: return

            v = v_info.split(" ")[0]
            carpeta = filedialog.askdirectory()
            if carpeta:
                ruta = os.path.join(carpeta, f"{nombre_base}.mp3")
                threading.Thread(target=lambda: asyncio.run(self.generar(contenido, v, ruta, False)), daemon=True).start()

        async def generar(self, texto, voz, ruta, play):
            try:
                # El problema solía ser que no se esperaba a que el archivo se soltara
                comm = edge_tts.Communicate(texto, voz)
                await comm.save(ruta)
                if play:
                    pygame.mixer.music.load(ruta)
                    pygame.mixer.music.play()
                else:
                    messagebox.showinfo("Éxito", "¡Audio guardado!")
            except Exception as e:
                print(f"Error en generar: {e}")

    root = tk.Tk()
    app = LectorPro(root)
    root.mainloop()

if __name__ == "__main__":
    lanzar_aplicacion()