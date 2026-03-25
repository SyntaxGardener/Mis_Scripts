import cv2
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import subprocess
import os
import whisper
import threading
import re
from datetime import timedelta

class Subtitulador:
    def __init__(self, root):
        self.root = root
        self.root.title("Subtitulador")
        
        # Posicionamiento GUI
        ancho_v, alto_v = 550, 570
        px = (self.root.winfo_screenwidth() // 2) - (ancho_v // 2)
        self.root.geometry(f"{ancho_v}x{alto_v}+{px}+5")
        
        self.color_sub = (255, 255, 255)
        self.video_in = ""
        self.srt_externo = ""
        self.dir_out = ""

        # Contenedor Principal
        main_frame = tk.Frame(root, padx=20, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- SECCIÓN 1: ARCHIVOS ---
        tk.Label(main_frame, text="1. RUTAS DE ARCHIVOS", font=("Arial", 10, "bold")).pack(anchor="w")
        
        self.btn_v = tk.Button(main_frame, text="📁 Seleccionar Vídeo", command=self.sel_video, bg="#f0f0f0")
        self.btn_v.pack(fill="x", pady=2)
        self.lbl_v = tk.Label(main_frame, text="Ninguno", fg="gray", font=("Arial", 8))
        self.lbl_v.pack(anchor="w")

        self.btn_d = tk.Button(main_frame, text="📂 Carpeta de Destino", command=self.sel_dir, bg="#f0f0f0")
        self.btn_d.pack(fill="x", pady=2)
        self.lbl_d = tk.Label(main_frame, text="Ninguna", fg="gray", font=("Arial", 8))
        self.lbl_d.pack(anchor="w")

        # --- SECCIÓN 2: MODO ---
        tk.Label(main_frame, text="\n2. MODO DE TRABAJO", font=("Arial", 10, "bold")).pack(anchor="w")
        self.modo = tk.StringVar(value="incrustar_ia")
        
        modos = [
            ("Auto: Transcribir + Incrustar", "incrustar_ia"),
            ("Solo crear .SRT", "solo_srt"),
            ("Usar .SRT externo", "usar_srt")
        ]
        for text, mode in modos:
            tk.Radiobutton(main_frame, text=text, variable=self.modo, value=mode, command=self.actualizar_gui).pack(anchor="w")

        self.frame_srt_ext = tk.Frame(main_frame, pady=5)
        tk.Button(self.frame_srt_ext, text="📄 Seleccionar archivo .SRT", command=self.sel_srt, bg="#e1f5fe").pack(fill="x")
        self.lbl_s = tk.Label(self.frame_srt_ext, text="No seleccionado", fg="red", font=("Arial", 8))
        self.lbl_s.pack(anchor="w")

        # --- SECCIÓN 3: PERSONALIZACIÓN (ESTILO) ---
        self.estetica = tk.LabelFrame(main_frame, text="3. PERSONALIZACIÓN VISUAL", padx=10, pady=10)
        self.estetica.pack(fill="x", pady=10)

        # Fila 1: Fuente y Tamaño
        f1 = tk.Frame(self.estetica)
        f1.pack(fill="x", pady=2)
        tk.Label(f1, text="Fuente:").pack(side=tk.LEFT)
        self.font_name = tk.Entry(f1, width=15)
        self.font_name.insert(0, "arial.ttf")
        self.font_name.pack(side=tk.LEFT, padx=5)
        
        tk.Label(f1, text="Tamaño:").pack(side=tk.LEFT, padx=5)
        self.size_v = tk.IntVar(value=45)
        tk.Spinbox(f1, from_=10, to=200, textvariable=self.size_v, width=5).pack(side=tk.LEFT)

        # Fila 2: Color y Posición
        f2 = tk.Frame(self.estetica)
        f2.pack(fill="x", pady=10)
        
        tk.Label(f2, text="Posición:").pack(side=tk.LEFT)
        self.pos_var = tk.StringVar(value="Superior")
        tk.OptionMenu(f2, self.pos_var, "Superior", "Inferior").pack(side=tk.LEFT, padx=5)

        self.btn_col = tk.Button(f2, text="Elegir Color", command=self.sel_color, bg="white", width=12)
        self.btn_col.pack(side=tk.RIGHT)

        # --- SECCIÓN 4: PROGRESO ---
        self.prog = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate")
        self.prog.pack(pady=10, fill="x")
        
        self.lbl_st = tk.Label(main_frame, text="Esperando...", fg="blue")
        self.lbl_st.pack()

        self.btn_go = tk.Button(main_frame, text="🚀 INICIAR PROCESO", command=self.go, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), height=2)
        self.btn_go.pack(fill="x", pady=10)
        
        self.actualizar_gui()

    def actualizar_gui(self):
        if self.modo.get() == "usar_srt":
            self.frame_srt_ext.pack(fill="x")
        else:
            self.frame_srt_ext.pack_forget()
        
        # Deshabilitar estética si solo vamos a generar SRT
        estado = "normal" if self.modo.get() != "solo_srt" else "disabled"
        for child in self.estetica.winfo_children():
            try: child.configure(state=estado)
            except: pass

    def sel_video(self):
        self.video_in = filedialog.askopenfilename(filetypes=[("Vídeo", "*.mp4 *.avi *.mov")])
        if self.video_in: self.lbl_v.config(text=os.path.basename(self.video_in), fg="black")

    def sel_dir(self):
        self.dir_out = filedialog.askdirectory()
        if self.dir_out: self.lbl_d.config(text=self.dir_out, fg="black")

    def sel_srt(self):
        self.srt_externo = filedialog.askopenfilename(filetypes=[("Subtítulos", "*.srt")])
        if self.srt_externo: self.lbl_s.config(text=os.path.basename(self.srt_externo), fg="black")

    def sel_color(self):
        c = colorchooser.askcolor()
        if c[1]: 
            self.color_sub = tuple(map(int, c[0]))
            self.btn_col.config(bg=c[1], fg="white" if sum(self.color_sub)<300 else "black")

    def parse_srt(self, srt_path):
        subtitles = []
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        blocks = re.split(r'\n\s*\n', content.strip())
        for block in blocks:
            lines = block.split('\n')
            if len(lines) >= 3:
                try:
                    times = lines[1].split(' --> ')
                    start = self.srt_to_sec(times[0])
                    end = self.srt_to_sec(times[1])
                    text = " ".join(lines[2:])
                    subtitles.append({'start': start, 'end': end, 'text': text})
                except: continue
        return subtitles

    def srt_to_sec(self, t):
        h, m, s = t.replace(',', '.').split(':')
        return int(h)*3600 + int(m)*60 + float(s)

    def sec_to_srt(self, s):
        td = timedelta(seconds=s)
        ms = int(td.microseconds / 1000)
        return f"{str(td).split('.')[0].zfill(8)},{ms:03d}"

    def go(self):
        if not self.video_in or not self.dir_out:
            return messagebox.showwarning("Faltan datos", "Selecciona vídeo y carpeta de destino.")
        threading.Thread(target=self.process, daemon=True).start()

    def process(self):
        try:
            self.btn_go.config(state="disabled")
            base = os.path.splitext(os.path.basename(self.video_in))[0]
            m = self.modo.get()
            
            # 1. Obtención de datos
            if m == "usar_srt":
                if not self.srt_externo: return messagebox.showerror("Error", "Falta el archivo SRT.")
                segments = self.parse_srt(self.srt_externo)
            else:
                self.lbl_st.config(text="🤖 IA Analizando audio...")
                model = whisper.load_model("base")
                result = model.transcribe(self.video_in, fp16=False)
                segments = result['segments']

            # 2. Generar Solo SRT
            if m == "solo_srt":
                path = os.path.join(self.dir_out, f"{base}.srt")
                with open(path, "w", encoding="utf-8") as f:
                    for i, s in enumerate(segments, 1):
                        f.write(f"{i}\n{self.sec_to_srt(s['start'])} --> {self.sec_to_srt(s['end'])}\n{s['text'].strip()}\n\n")
                messagebox.showinfo("Éxito", "Archivo SRT creado con éxito.")
            
            # 3. Incrustar (IA o Externo)
            else:
                out_v = os.path.join(self.dir_out, f"{base}_subtitulado.mp4")
                tmp_v = os.path.join(self.dir_out, "temp_render.mp4")
                
                cap = cv2.VideoCapture(self.video_in)
                w, h, fps = int(cap.get(3)), int(cap.get(4)), cap.get(5)
                total = int(cap.get(7))
                writer = cv2.VideoWriter(tmp_v, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

                try: font = ImageFont.truetype(self.font_name.get(), self.size_v.get())
                except: font = ImageFont.load_default()

                self.lbl_st.config(text="🎬 Dibujando subtítulos...")
                count = 0
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret: break
                    
                    time_now = count / fps
                    txt = next((s['text'].strip() for s in segments if s['start'] <= time_now <= s['end']), "")
                    
                    if txt:
                        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        draw = ImageDraw.Draw(img)
                        bbox = draw.textbbox((0,0), txt, font=font)
                        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                        
                        pos_x = (w - tw) / 2
                        # LOGICA DE POSICIÓN
                        pos_y = 10 if self.pos_var.get() == "Superior" else (h - th - 50)
                        
                        draw.text((pos_x+2, pos_y+2), txt, font=font, fill=(0,0,0))
                        draw.text((pos_x, pos_y), txt, font=font, fill=self.color_sub)
                        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    
                    writer.write(frame)
                    count += 1
                    if count % 25 == 0:
                        self.prog['value'] = (count/total)*100
                        self.root.update_idletasks()

                cap.release()
                writer.release()
                
                self.lbl_st.config(text="🔊 Mezclando audio...")
                subprocess.run(['ffmpeg', '-y', '-i', tmp_v, '-i', self.video_in, '-c', 'copy', '-map', '0:v:0', '-map', '1:a:0', '-shortest', out_v], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if os.path.exists(tmp_v): os.remove(tmp_v)
                messagebox.showinfo("Éxito", "¡Vídeo terminado!")

            os.startfile(self.dir_out)
        except Exception as e: messagebox.showerror("Error", str(e))
        finally:
            self.btn_go.config(state="normal")
            self.lbl_st.config(text="Terminado")
            self.prog['value'] = 0

if __name__ == "__main__":
    root = tk.Tk()
    app = Subtitulador(root)
    root.mainloop()