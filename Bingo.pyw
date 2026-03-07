# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox
import random
import pyttsx3
import time

class BingoDocenteFinal:
    def __init__(self, root):
        self.root = root
        self.root.title("Bingo Bilingüe")
        
        # --- CONFIGURACIÓN DE GEOMETRÍA DINÁMICA ---
        # Definimos el tamaño de la ventana
        ancho_ventana = 850
        alto_ventana = 780
        
        # Obtenemos el ancho de tu pantalla actual
        ancho_pantalla = self.root.winfo_screenwidth()
        
        # Calculamos la posición X para que esté centrada
        pos_x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        # Posición Y en 0 para que esté pegada arriba
        pos_y = 0
        
        # Aplicamos la geometría: "Ancho x Alto + X + Y"
        self.root.geometry(f"{ancho_ventana}x{alto_ventana}+{pos_x}+{pos_y}")
        self.root.configure(bg="#2c3e50")

        # --- LÓGICA ---
        self.idioma_actual = "ES" 
        self.numeros_disponibles = []
        self.historial = []
        self.ultimo_numero = None
        self.ids_voces = {"ES": None, "EN": None}

        self.escanear_sistema_de_voces()

        # --- INTERFAZ ---
        self.frame_config = tk.Frame(root, bg="#34495e", pady=10)
        self.frame_config.pack(fill="x")

        self.btn_idioma = tk.Button(self.frame_config, text="MODO: ESPAÑOL 🇪🇸", command=self.alternar_idioma, 
                                   bg="#f39c12", fg="white", font=("Arial", 10, "bold"))
        self.btn_idioma.pack(side="left", padx=20)

        tk.Label(self.frame_config, text="Rango:", fg="white", bg="#34495e").pack(side="left")
        
        self.entry_min = tk.Entry(self.frame_config, width=5, justify="center")
        self.entry_min.insert(0, "1") 
        self.entry_min.pack(side="left", padx=5)
        
        self.entry_max = tk.Entry(self.frame_config, width=5, justify="center")
        self.entry_max.insert(0, "99") 
        self.entry_max.pack(side="left", padx=5)

        self.btn_reiniciar = tk.Button(self.frame_config, text="REINICIAR BOMBO", command=self.preparar_bombo, 
                                      bg="#e74c3c", fg="white", font=("Arial", 9, "bold"))
        self.btn_reiniciar.pack(side="right", padx=20)

        # Pantalla Central
        self.label_numero = tk.Label(root, text="?", font=("Helvetica", 240, "bold"), bg="#2c3e50", fg="#f1c40f")
        self.label_numero.pack(expand=True)

        self.text_historial = tk.Label(root, text="Pulsa REINICIAR para empezar", fg="#ecf0f1", bg="#2c3e50", 
                                       font=("Arial", 13), wraplength=750)
        self.text_historial.pack(pady=5)

        # Controles
        self.frame_controles = tk.Frame(root, bg="#2c3e50")
        self.frame_controles.pack(fill="x", pady=10)

        self.btn_sacar = tk.Button(self.frame_controles, text="¡SACAR BOLA!", command=self.sacar_bola, 
                                  font=("Arial", 22, "bold"), bg="#27ae60", fg="white", height=2)
        self.btn_sacar.pack(side="left", fill="x", expand=True, padx=(20, 10))

        self.btn_repetir = tk.Button(self.frame_controles, text="🔊 REPETIR", command=self.repetir_voz,
                                    font=("Arial", 18, "bold"), bg="#3498db", fg="white", height=2, state="disabled")
        self.btn_repetir.pack(side="right", fill="x", expand=True, padx=(10, 20))

        # Premios
        self.frame_premios = tk.Frame(root, bg="#2c3e50")
        self.frame_premios.pack(fill="x", pady=10)

        self.btn_linea = tk.Button(self.frame_premios, text="⭐ ¡LÍNEA! ⭐", command=lambda: self.cantar_premio("linea"),
                                   bg="#9b59b6", fg="white", font=("Arial", 14, "bold"), height=2)
        self.btn_linea.pack(side="left", fill="x", expand=True, padx=(20, 5))

        self.btn_bingo = tk.Button(self.frame_premios, text="🏆 ¡BINGO! 🏆", command=lambda: self.cantar_premio("bingo"),
                                   bg="#f1c40f", fg="#2c3e50", font=("Arial", 14, "bold"), height=2)
        self.btn_bingo.pack(side="right", fill="x", expand=True, padx=(5, 20))

        self.preparar_bombo()

    def escanear_sistema_de_voces(self):
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            for v in voices:
                v_name = v.name.lower()
                if "spanish" in v_name or "españ" in v_name:
                    self.ids_voces["ES"] = v.id
                elif "english" in v_name or "en-us" in v_name or "en-gb" in v_name:
                    self.ids_voces["EN"] = v.id
            del engine
        except: pass

    def alternar_idioma(self):
        self.idioma_actual = "EN" if self.idioma_actual == "ES" else "ES"
        if self.idioma_actual == "EN":
            self.btn_idioma.config(text="MODE: ENGLISH 🇬🇧", bg="#2980b9")
            self.btn_sacar.config(text="DRAW BALL!")
            self.btn_repetir.config(text="🔊 REPEAT")
            self.btn_linea.config(text="⭐ LINE! ⭐")
            self.btn_bingo.config(text="🏆 BINGO! 🏆")
        else:
            self.btn_idioma.config(text="MODO: ESPAÑOL 🇪🇸", bg="#f39c12")
            self.btn_sacar.config(text="¡SACAR BOLA!")
            self.btn_repetir.config(text="🔊 REPETIR")
            self.btn_linea.config(text="⭐ ¡LÍNEA! ⭐")
            self.btn_bingo.config(text="🏆 ¡BINGO! 🏆")

    def ejecutar_voz(self, texto):
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 140)
            voz_id = self.ids_voces.get(self.idioma_actual)
            if voz_id:
                engine.setProperty('voice', voz_id)
            engine.say(texto)
            engine.runAndWait()
            engine.stop()
            del engine
            time.sleep(0.1)
        except: pass

    def sacar_bola(self):
        if self.numeros_disponibles:
            self.btn_sacar.config(state="disabled")
            self.btn_repetir.config(state="disabled")
            self.label_numero.config(text="?")
            self.root.update() 
            
            num = self.numeros_disponibles.pop()
            self.historial.append(num)
            self.ultimo_numero = num
            
            self.ejecutar_voz(str(num))
            
            self.label_numero.config(text=str(num))
            self.text_historial.config(text=", ".join(map(str, sorted(self.historial))))
            
            if self.numeros_disponibles:
                self.btn_sacar.config(state="normal")
            else:
                self.btn_sacar.config(text="FIN / EMPTY", state="disabled")
            self.btn_repetir.config(state="normal")
            self.root.update()

    def repetir_voz(self):
        if self.ultimo_numero is not None:
            self.ejecutar_voz(str(self.ultimo_numero))

    def cantar_premio(self, tipo):
        frases = {
            "ES": {"linea": "¡Línea!", "bingo": "¡Bingo! ¡Felicidades!"},
            "EN": {"linea": "Line!", "bingo": "Bingo! Congratulations!"}
        }
        self.ejecutar_voz(frases[self.idioma_actual][tipo])

    def preparar_bombo(self):
        try:
            v_min = int(self.entry_min.get())
            v_max = int(self.entry_max.get())
            if v_min >= v_max:
                messagebox.showwarning("Rango Incorrecto", "El mínimo debe ser menor al máximo.")
                return
            self.numeros_disponibles = list(range(v_min, v_max + 1))
            random.shuffle(self.numeros_disponibles)
            self.historial = []
            self.ultimo_numero = None
            self.label_numero.config(text="?")
            self.text_historial.config(text="Bombo listo: " + str(len(self.numeros_disponibles)) + " números.")
            self.btn_sacar.config(state="normal", text="¡SACAR BOLA!" if self.idioma_actual=="ES" else "DRAW BALL!")
            self.btn_repetir.config(state="disabled")
        except: pass

if __name__ == "__main__":
    root = tk.Tk()
    app = BingoDocenteFinal(root)
    root.mainloop()