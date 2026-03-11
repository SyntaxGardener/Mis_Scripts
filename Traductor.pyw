# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
from deep_translator import GoogleTranslator
import edge_tts
import asyncio
import pygame
import os
import threading
import speech_recognition as sr
from datetime import datetime

class TraductorUSB:
    def __init__(self, root):
        self.root = root
        self.root.title("TRADUCTOR")
        # Ventana ajustada para evitar espacio negro sobrante
        ancho = 600
        alto = 630
        pos_x = (self.root.winfo_screenwidth() // 2) - (ancho // 2)
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+20")
        self.root.configure(bg="#121212")
        self.root.resizable(False, False)
        
        pygame.mixer.init()
        self.recognizer = sr.Recognizer()

        # --- LÓGICA DE RUTA PARA LA RAÍZ REAL DE LA UNIDAD ---
        try:
            ruta_script = os.path.dirname(os.path.abspath(__file__))
            unidad_raiz = os.path.splitdrive(ruta_script)[0] + os.sep
            self.carpeta_audios = os.path.join(unidad_raiz, "AUDIOS_TRADUCTOR")
            if not os.path.exists(self.carpeta_audios):
                os.makedirs(self.carpeta_audios)
        except:
            self.carpeta_audios = "AUDIOS_TRADUCTOR"
            if not os.path.exists(self.carpeta_audios): os.makedirs(self.carpeta_audios)

        # Configuración de idiomas y voces (Sin 'auto')
        self.idiomas_lista = ["arabic", "spanish", "ukrainian", "russian", "english", "french", "german", "italian", "portuguese"]
        
        self.codigos_voz = {
            "spanish": "es-ES", "english": "en-US", "french": "fr-FR", 
            "german": "de-DE", "italian": "it-IT", "portuguese": "pt-PT",
            "ukrainian": "uk-UA", "arabic": "ar-MA", "russian": "ru-RU"
        }

        self.voces_edge = {
            "spanish": "es-ES-AlvaroNeural", "english": "en-US-GuyNeural",
            "french": "fr-FR-DeniseNeural", "german": "de-DE-ConradNeural",
            "ukrainian": "uk-UA-OstapNeural", "arabic": "ar-MA-MounaNeural", 
            "russian": "ru-RU-DmitryNeural"
        }

        # --- INTERFAZ GRÁFICA ---
        tk.Label(root, text="TRADUCTOR", font=("Segoe UI", 18, "bold"), 
                 bg="#121212", fg="#3498db").pack(pady=15)

        # Selección de Idiomas (CENTRADO)
        lang_container = tk.Frame(root, bg="#121212")
        lang_container.pack(pady=5)
        
        self.combo_origen = ttk.Combobox(lang_container, values=self.idiomas_lista, state="readonly", width=12)
        self.combo_origen.set("arabic") 
        self.combo_origen.pack(side="left", padx=10)

        tk.Label(lang_container, text="➜", font=("Segoe UI", 12), bg="#121212", fg="white").pack(side="left")

        self.combo_destino = ttk.Combobox(lang_container, values=self.idiomas_lista, state="readonly", width=12)
        self.combo_destino.set("spanish")
        self.combo_destino.pack(side="left", padx=10)

        # Botón Micrófono
        self.btn_mic = tk.Button(root, text=" 🎤 PULSAR Y HABLAR ", font=("Segoe UI", 12, "bold"), 
                                 bg="#e74c3c", fg="white", relief="flat", cursor="hand2", command=self.escuchar_thread)
        self.btn_mic.pack(pady=15, fill="x", padx=100)

        tk.Label(root, text="Texto detectado / original:", bg="#121212", fg="#888888", font=("Segoe UI", 9)).pack(anchor="w", padx=40)
        self.txt_entrada = tk.Text(root, height=3, bg="#1e1e1e", fg="white", relief="flat", padx=10, pady=10, font=("Segoe UI", 10))
        self.txt_entrada.pack(fill="x", padx=40, pady=5)

        # Botones centrales
        btn_frame = tk.Frame(root, bg="#121212")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text=" TRADUCIR ", font=("Segoe UI", 9, "bold"), bg="#2ecc71", command=self.traducir, cursor="hand2").grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text=" 📋 COPIAR ", font=("Segoe UI", 9, "bold"), bg="#3498db", fg="white", command=self.copiar_texto, cursor="hand2").grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text=" 🗑 ", font=("Segoe UI", 9), bg="#444444", fg="white", command=self.limpiar, cursor="hand2").grid(row=0, column=2, padx=5)

        # Botones de Audio
        audio_btn_frame = tk.Frame(root, bg="#121212")
        audio_btn_frame.pack(pady=5, fill="x", padx=100)

        tk.Button(audio_btn_frame, text=" 🔊 ESCUCHAR ", font=("Segoe UI", 10, "bold"), 
                  bg="#f1c40f", fg="black", relief="flat", command=self.reproducir_voz_thread, cursor="hand2").pack(side="left", fill="x", expand=True, padx=2)
        
        tk.Button(audio_btn_frame, text=" 💾 GUARDAR MP3 ", font=("Segoe UI", 10, "bold"), 
                  bg="#9b59b6", fg="white", relief="flat", command=self.guardar_audio_thread, cursor="hand2").pack(side="left", fill="x", expand=True, padx=2)

        self.txt_salida = tk.Text(root, height=3, bg="#2d2d2d", fg="#2ecc71", relief="flat", padx=10, pady=10, font=("Segoe UI", 10, "bold"))
        self.txt_salida.pack(fill="x", padx=40, pady=5)

        self.lbl_status = tk.Label(root, text="-", bg="#121212", fg="#3498db", font=("Segoe UI", 9, "italic"))
        self.lbl_status.pack(pady=10)

    # --- FUNCIONES ---
    def escuchar_thread(self): threading.Thread(target=self.escuchar_voz, daemon=True).start()

    def escuchar_voz(self):
        idioma_origen = self.combo_origen.get()
        codigo = self.codigos_voz.get(idioma_origen, "es-ES")
        with sr.Microphone() as source:
            self.lbl_status.config(text="👂 Escuchando...", fg="#e74c3c")
            try:
                audio = self.recognizer.listen(source, timeout=5)
                self.lbl_status.config(text="⌛ Procesando voz...", fg="#f1c40f")
                texto = self.recognizer.recognize_google(audio, language=codigo)
                self.txt_entrada.delete("1.0", tk.END)
                self.txt_entrada.insert(tk.END, texto)
                self.traducir()
            except:
                self.lbl_status.config(text="❌ No se detectó voz", fg="#888888")

    def traducir(self):
        t = self.txt_entrada.get("1.0", "end-1c")
        if not t.strip(): return
        try:
            res = GoogleTranslator(source=self.combo_origen.get(), target=self.combo_destino.get()).translate(t)
            self.txt_salida.delete("1.0", tk.END)
            self.txt_salida.insert(tk.END, res)
            self.lbl_status.config(text="✔ Traducido", fg="#2ecc71")
        except: self.lbl_status.config(text="Error de conexión")

    def reproducir_voz_thread(self): threading.Thread(target=self.reproducir_voz, daemon=True).start()

    def reproducir_voz(self):
        texto = self.txt_salida.get("1.0", "end-1c")
        if not texto.strip(): return
        voz = self.voces_edge.get(self.combo_destino.get(), "es-ES-AlvaroNeural")
        async def generar():
            await edge_tts.Communicate(texto, voz).save("temp.mp3")
        try:
            asyncio.run(generar())
            pygame.mixer.music.load("temp.mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy(): pass
            pygame.mixer.music.unload()
            os.remove("temp.mp3")
        except: pass

    def guardar_audio_thread(self): threading.Thread(target=self.guardar_audio, daemon=True).start()

    def guardar_audio(self):
        texto = self.txt_salida.get("1.0", "end-1c")
        if not texto.strip(): return
        idioma = self.combo_destino.get()
        voz = self.voces_edge.get(idioma, "es-ES-AlvaroNeural")
        nombre_base = f"Traduccion_{idioma}_{datetime.now().strftime('%H%M%S')}.mp3"
        ruta_final = os.path.join(self.carpeta_audios, nombre_base)

        async def generar():
            await edge_tts.Communicate(texto, voz).save(ruta_final)
        try:
            self.lbl_status.config(text="💾 Guardando...", fg="#9b59b6")
            asyncio.run(generar())
            self.lbl_status.config(text=f"✔ Guardado en Raíz", fg="#2ecc71")
            os.startfile(self.carpeta_audios)
        except: self.lbl_status.config(text="❌ Error al guardar")

    def copiar_texto(self):
        c = self.txt_salida.get("1.0", "end-1c")
        if c.strip():
            self.root.clipboard_clear()
            self.root.clipboard_append(c)
            self.lbl_status.config(text="✔ ¡Copiado!", fg="#2ecc71")

    def limpiar(self):
        self.txt_entrada.delete("1.0", tk.END)
        self.txt_salida.delete("1.0", tk.END)
        self.lbl_status.config(text="Listo", fg="#3498db")

if __name__ == "__main__":
    root = tk.Tk()
    app = TraductorUSB(root)
    root.mainloop()