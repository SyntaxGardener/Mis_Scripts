import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import PyPDF2
import os
import re
import subprocess
from PIL import Image, ImageTk
import io
import fitz  # PyMuPDF

class SeparadorPDF:
    def __init__(self, root):
        self.root = root
        self.root.title("Separador de PDF + Extractor de páginas")
        
        # Ventana más compacta
        width = 850
        height = 650
        screen_width = self.root.winfo_screenwidth()
        x = (screen_width // 2) - (width // 2)
        y = 20
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Variables
        self.pdf_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.paginas_info = tk.StringVar(value="Páginas totales: -")
        self.naming_option = tk.IntVar(value=2)
        self.open_folder = tk.BooleanVar(value=True)
        self.modo_operacion = tk.StringVar(value="dividir")  # "dividir" o "extraer"
        
        # Variables para el visor
        self.pdf_documento = None
        self.total_paginas_pdf = 0
        self.miniaturas = []
        self.canvas_items = []
        self.grupos_paginas = []  # Lista de grupos (cada grupo es una lista de páginas)
        self.seleccion_actual = []  # Páginas seleccionadas actualmente
        
        self.create_widgets()

    def create_widgets(self):
        # Frame principal dividido
        main_panel = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        main_panel.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Panel izquierdo - Controles
        left_frame = tk.Frame(main_panel, width=350)
        main_panel.add(left_frame, width=350)
        
        # Panel derecho - Visor
        right_frame = tk.Frame(main_panel)
        main_panel.add(right_frame, width=500)
        
        self.create_control_panel(left_frame)
        self.create_viewer_panel(right_frame)

    def create_control_panel(self, parent):
        # 1. Selección de archivo
        tk.Label(parent, text="1. Selecciona el archivo PDF:", font=('Arial', 10, 'bold')).pack(anchor="w", padx=10, pady=(10, 2))
        file_frame = tk.Frame(parent)
        file_frame.pack(fill="x", padx=10)
        tk.Entry(file_frame, textvariable=self.pdf_path, width=30).pack(side="left", expand=True, fill="x")
        tk.Button(file_frame, text="Buscar", command=self.select_file, bg="#3498DB", fg="white").pack(side="right", padx=5)
        
        self.paginas_label = tk.Label(parent, textvariable=self.paginas_info, font=('Arial', 9, 'bold'), fg="#2E86C1")
        self.paginas_label.pack(anchor="w", padx=10)

        # 2. MODO DE OPERACIÓN
        tk.Label(parent, text="2. ¿Qué quieres hacer?", font=('Arial', 10, 'bold')).pack(anchor="w", padx=10, pady=(10, 2))
        
        modo_frame = tk.Frame(parent)
        modo_frame.pack(fill="x", padx=10, pady=2)
        
        tk.Radiobutton(modo_frame, text="📄 Dividir PDF (varios archivos)", 
                      variable=self.modo_operacion, value="dividir",
                      command=self.cambiar_modo).pack(anchor="w")
        tk.Radiobutton(modo_frame, text="📑 Extraer páginas (un solo archivo)", 
                      variable=self.modo_operacion, value="extraer",
                      command=self.cambiar_modo).pack(anchor="w")
        
        # 3. Selección de páginas
        tk.Label(parent, text="3. Selecciona páginas:", font=('Arial', 10, 'bold')).pack(anchor="w", padx=10, pady=(10, 2))
        
        # Botones de acción
        action_frame = tk.Frame(parent)
        action_frame.pack(fill="x", padx=10, pady=2)
        
        self.btn_guardar_grupo = tk.Button(action_frame, text="📥 Añadir como grupo", 
                                          command=self.guardar_grupo,
                                          bg="#90ee90", fg="black", width=20, state="disabled")
        self.btn_guardar_grupo.pack(side=tk.LEFT, padx=2)
        
        self.btn_limpiar = tk.Button(action_frame, text="🗑️ Limpiar selección", 
                                    command=self.limpiar_seleccion,
                                    bg="#E74C3C", fg="white", width=20)
        self.btn_limpiar.pack(side=tk.LEFT, padx=2)
        
        # Info de selección actual
        self.lbl_seleccion_actual = tk.Label(parent, text="Selección actual: Ninguna", 
                                            font=('Arial', 9, 'italic'), fg="#555", 
                                            wraplength=300, bg="#f0f0f0", pady=3)
        self.lbl_seleccion_actual.pack(anchor="w", padx=10, pady=2, fill="x")

        # 4. Grupos definidos
        tk.Label(parent, text="4. Grupos definidos:", font=('Arial', 10, 'bold')).pack(anchor="w", padx=10, pady=(5, 2))
        
        # Lista de grupos
        list_frame = tk.Frame(parent, height=100)
        list_frame.pack(fill="x", padx=10, pady=2)
        list_frame.pack_propagate(False)
        
        self.grupos_listbox = tk.Listbox(list_frame, height=4)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.grupos_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.grupos_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.grupos_listbox.yview)
        
        # Botones para gestionar grupos
        grupo_btn_frame = tk.Frame(parent)
        grupo_btn_frame.pack(fill="x", padx=10, pady=2)
        
        tk.Button(grupo_btn_frame, text="🗑️ Eliminar", command=self.eliminar_grupo,
                 bg="#E67E22", fg="white", width=20).pack(side=tk.LEFT, padx=2)
        tk.Button(grupo_btn_frame, text="🔄 Limpiar todo", command=self.limpiar_todos_grupos,
                 bg="#E74C3C", fg="white", width=20).pack(side=tk.LEFT, padx=2)

        # Vista previa de rangos
        tk.Label(parent, text="Vista previa:", font=('Arial', 9, 'bold')).pack(anchor="w", padx=10, pady=(5, 0))
        self.range_entry = tk.Entry(parent, font=('Consolas', 9), bg="#f0f0f0")
        self.range_entry.pack(fill="x", padx=10, pady=2)
        self.range_entry.config(state="readonly")

        # BOTÓN EJECUTAR
        self.btn_run = tk.Button(parent, text="▶ EJECUTAR", command=self.mostrar_dialogo_guardado, 
                                bg="#90ee90", fg="white", font=('Arial', 14, 'bold'), 
                                cursor="hand2", height=2, state="disabled")
        self.btn_run.pack(pady=10, fill="x", padx=20)

    def create_viewer_panel(self, parent):
        tk.Label(parent, text="VISOR DE PÁGINAS", font=('Arial', 12, 'bold')).pack(pady=2)
        
        # Instrucciones según modo
        self.instrucciones_label = tk.Label(parent, 
            text="🖱️ Click en las páginas para seleccionarlas. Luego guarda el grupo.",
            font=('Arial', 9, 'italic'), fg="#555", wraplength=600)
        self.instrucciones_label.pack()
        
        # Frame para miniaturas
        canvas_frame = tk.Frame(parent)
        canvas_frame.pack(fill="both", expand=True, padx=5, pady=2)
        
        self.canvas_visor = tk.Canvas(canvas_frame, bg='white')
        scrollbar_y = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas_visor.yview)
        scrollbar_x = ttk.Scrollbar(parent, orient="horizontal", command=self.canvas_visor.xview)
        
        self.frame_miniaturas = tk.Frame(self.canvas_visor, bg='white')
        self.frame_miniaturas.bind("<Configure>", lambda e: self.canvas_visor.configure(scrollregion=self.canvas_visor.bbox("all")))
        
        self.canvas_visor.create_window((0, 0), window=self.frame_miniaturas, anchor="nw")
        self.canvas_visor.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.canvas_visor.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        
        # Vista previa
        preview_frame = tk.LabelFrame(parent, text="Vista previa", padx=2, pady=2)
        preview_frame.pack(fill="x", padx=5, pady=2)
        
        self.preview_label = tk.Label(preview_frame, text="Doble click en página para ver", 
                                     font=('Arial', 8), fg="#888", bg="#f0f0f0", height=2)
        self.preview_label.pack(fill="x")

    def cambiar_modo(self):
        """Actualizar interfaz según el modo seleccionado"""
        if self.modo_operacion.get() == "dividir":
            self.instrucciones_label.config(
                text="📄 DIVIDIR: Selecciona páginas para un grupo, guarda, repite para cada archivo."
            )
        else:
            self.instrucciones_label.config(
                text="📑 EXTRAER: Selecciona TODAS las páginas que quieras y guarda UNA SOLA VEZ."
            )
        self.limpiar_seleccion()
        self.limpiar_todos_grupos()

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("Archivos PDF", "*.pdf")])
        if path:
            self.pdf_path.set(path)
            try:
                self.pdf_documento = fitz.open(path)
                reader = PyPDF2.PdfReader(path)
                self.total_paginas_pdf = len(reader.pages)
                self.paginas_info.set(f"Páginas totales: {self.total_paginas_pdf}")
                
                self.cargar_miniaturas()
                self.grupos_paginas = []
                self.seleccion_actual = []
                self.actualizar_listbox_grupos()
                self.actualizar_entrada_rangos()
                self.btn_guardar_grupo.config(state="normal")
                self.btn_run.config(state="normal")
                
            except Exception as e:
                self.paginas_info.set(f"Error al leer el PDF: {e}")
                messagebox.showerror("Error", f"No se pudo leer el PDF: {e}")

    def cargar_miniaturas(self):
        for widget in self.frame_miniaturas.winfo_children():
            widget.destroy()
        
        self.miniaturas = []
        self.canvas_items = []
        
        fila = 0
        columna = 0
        max_columnas = 4
        
        for i in range(self.total_paginas_pdf):
            frame_pagina = tk.Frame(self.frame_miniaturas, bg='white', relief='raised', borderwidth=1)
            frame_pagina.grid(row=fila, column=columna, padx=3, pady=3, sticky='n')
            
            try:
                pagina = self.pdf_documento[i]
                zoom = 0.15
                mat = fitz.Matrix(zoom, zoom)
                pix = pagina.get_pixmap(matrix=mat)
                
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                img_tk = ImageTk.PhotoImage(img)
                self.miniaturas.append(img_tk)
                
                lbl_img = tk.Label(frame_pagina, image=img_tk, bg='white', cursor="hand2")
                lbl_img.pack(padx=1, pady=1)
                
                lbl_num = tk.Label(frame_pagina, text=f"Pág.{i+1}", bg='white', font=("Arial", 7))
                lbl_num.pack()
                
                # Eventos
                lbl_img.bind("<Button-1>", lambda e, idx=i: self.toggle_seleccion_pagina(idx))
                lbl_num.bind("<Button-1>", lambda e, idx=i: self.toggle_seleccion_pagina(idx))
                lbl_img.bind("<Double-Button-1>", lambda e, idx=i: self.mostrar_preview(idx))
                
                self.canvas_items.append({
                    'frame': frame_pagina,
                    'label': lbl_img,
                    'num': i,
                    'original_bg': 'white'
                })
                
            except Exception as e:
                print(f"Error cargando página {i+1}: {e}")
            
            columna += 1
            if columna >= max_columnas:
                columna = 0
                fila += 1

    def toggle_seleccion_pagina(self, idx):
        """Seleccionar o deseleccionar una página"""
        pagina_num = idx + 1
        
        if pagina_num in self.seleccion_actual:
            self.seleccion_actual.remove(pagina_num)
        else:
            self.seleccion_actual.append(pagina_num)
        
        self.seleccion_actual.sort()
        self.actualizar_resaltado_paginas()
        self.actualizar_label_seleccion()

    def actualizar_resaltado_paginas(self):
        """Resaltar páginas seleccionadas"""
        # Resetear todos
        for item in self.canvas_items:
            item['frame'].config(bg='white')
            for child in item['frame'].winfo_children():
                child.config(bg='white', fg='black')
        
        # Resaltar seleccionadas
        for num in self.seleccion_actual:
            idx = num - 1
            if 0 <= idx < len(self.canvas_items):
                item = self.canvas_items[idx]
                item['frame'].config(bg='#3498DB')
                for child in item['frame'].winfo_children():
                    child.config(bg='#3498DB', fg='white')

    def guardar_grupo(self):
        """Guardar la selección actual como un grupo"""
        if not self.seleccion_actual:
            messagebox.showwarning("Atención", "Selecciona al menos una página.")
            return
        
        # Guardar grupo
        self.grupos_paginas.append(self.seleccion_actual.copy())
        
        # En modo "extraer", deshabilitar más grupos
        if self.modo_operacion.get() == "extraer":
            self.btn_guardar_grupo.config(state="disabled")
            self.instrucciones_label.config(
                text="✅ Grupo guardado. Ya puedes ejecutar."
            )
        
        # Limpiar selección actual
        self.seleccion_actual = []
        self.actualizar_resaltado_paginas()
        self.actualizar_listbox_grupos()
        self.actualizar_entrada_rangos()
        self.actualizar_label_seleccion()

    def limpiar_seleccion(self):
        """Limpiar selección actual"""
        self.seleccion_actual = []
        self.actualizar_resaltado_paginas()
        self.actualizar_label_seleccion()

    def eliminar_grupo(self):
        """Eliminar grupo seleccionado"""
        seleccion = self.grupos_listbox.curselection()
        if seleccion:
            idx = seleccion[0]
            del self.grupos_paginas[idx]
            self.actualizar_listbox_grupos()
            self.actualizar_entrada_rangos()
            
            # Reactivar botón si estábamos en modo extraer
            if self.modo_operacion.get() == "extraer" and len(self.grupos_paginas) == 0:
                self.btn_guardar_grupo.config(state="normal")
                self.instrucciones_label.config(
                    text="📑 EXTRAER: Selecciona TODAS las páginas que quieras y guarda UNA SOLA VEZ."
                )

    def limpiar_todos_grupos(self):
        """Limpiar todos los grupos"""
        self.grupos_paginas = []
        self.actualizar_listbox_grupos()
        self.actualizar_entrada_rangos()
        
        if self.modo_operacion.get() == "extraer":
            self.btn_guardar_grupo.config(state="normal")
            self.instrucciones_label.config(
                text="📑 EXTRAER: Selecciona TODAS las páginas que quieras y guarda UNA SOLA VEZ."
            )

    def actualizar_label_seleccion(self):
        """Actualizar texto de selección actual"""
        if self.seleccion_actual:
            if len(self.seleccion_actual) == 1:
                texto = f"Seleccionada: Página {self.seleccion_actual[0]}"
            else:
                texto = f"Seleccionadas: {len(self.seleccion_actual)} páginas"
        else:
            texto = "Selección actual: Ninguna"
        self.lbl_seleccion_actual.config(text=texto)

    def actualizar_listbox_grupos(self):
        """Actualizar listbox con los grupos definidos"""
        self.grupos_listbox.delete(0, tk.END)
        for i, grupo in enumerate(self.grupos_paginas, 1):
            if len(grupo) == 1:
                texto = f"Grupo {i}: Pág.{grupo[0]}"
            else:
                texto = f"Grupo {i}: {len(grupo)} págs ({grupo[0]}-{grupo[-1]})"
            self.grupos_listbox.insert(tk.END, texto)

    def actualizar_entrada_rangos(self):
        """Actualizar campo de entrada con todos los grupos"""
        if not self.grupos_paginas:
            self.range_entry.config(state="normal")
            self.range_entry.delete(0, tk.END)
            self.range_entry.config(state="readonly")
            return
        
        if self.modo_operacion.get() == "dividir":
            texto_final = f"{len(self.grupos_paginas)} grupos definidos"
        else:
            todas = []
            for grupo in self.grupos_paginas:
                todas.extend(grupo)
            texto_final = f"{len(todas)} páginas seleccionadas"
        
        self.range_entry.config(state="normal")
        self.range_entry.delete(0, tk.END)
        self.range_entry.insert(0, texto_final)
        self.range_entry.config(state="readonly")

    def mostrar_preview(self, idx):
        """Mostrar vista previa ampliada"""
        try:
            pagina = self.pdf_documento[idx]
            zoom = 0.3
            mat = fitz.Matrix(zoom, zoom)
            pix = pagina.get_pixmap(matrix=mat)
            
            img_data = pix.tobytes("ppm")
            img = Image.open(io.BytesIO(img_data))
            
            max_width = 300
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            img_tk = ImageTk.PhotoImage(img)
            self.preview_label.config(image=img_tk, text="", height=100)
            self.preview_label.image = img_tk
            
        except Exception as e:
            self.preview_label.config(image="", text=f"Error: {e}")

    def mostrar_dialogo_guardado(self):
        """Mostrar diálogo para opciones de guardado"""
        if not self.pdf_path.get():
            messagebox.showwarning("Atención", "Selecciona un archivo PDF.")
            return
        
        if not self.grupos_paginas:
            messagebox.showwarning("Atención", "Define al menos un grupo de páginas.")
            return

        # Crear ventana de diálogo
        dialog = tk.Toplevel(self.root)
        dialog.title("Opciones de guardado")
        dialog.geometry("450x300")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_set()
        
        # Centrar diálogo
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Variables locales
        output_dir = tk.StringVar(value=self.output_dir.get() or os.path.expanduser("~/Downloads"))
        naming_option = tk.IntVar(value=self.naming_option.get())
        open_folder = tk.BooleanVar(value=self.open_folder.get())
        
        # Interfaz del diálogo
        tk.Label(dialog, text="Guardar archivos en:", font=('Arial', 10, 'bold')).pack(anchor="w", padx=20, pady=(15, 5))
        
        dir_frame = tk.Frame(dialog)
        dir_frame.pack(fill="x", padx=20)
        tk.Entry(dir_frame, textvariable=output_dir, width=35).pack(side="left", expand=True, fill="x")
        tk.Button(dir_frame, text="Examinar", command=lambda: self._select_output_dir_dialog(output_dir)).pack(side="right", padx=5)
        
        tk.Label(dialog, text="Criterio para nombrar:", font=('Arial', 10, 'bold')).pack(anchor="w", padx=20, pady=(15, 5))
        tk.Radiobutton(dialog, text="Nombre original + número (Apuntes/Temas)", 
                      variable=naming_option, value=2).pack(anchor="w", padx=30)
        tk.Radiobutton(dialog, text="Detectar 'Apellidos y nombre' (Certificados)", 
                      variable=naming_option, value=1).pack(anchor="w", padx=30)
        
        tk.Checkbutton(dialog, text="Abrir carpeta al terminar", 
                      variable=open_folder).pack(anchor="w", padx=20, pady=15)
        
        # Frame de botones
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        def confirmar_y_ejecutar():
            # Guardar valores
            self.output_dir.set(output_dir.get())
            self.naming_option.set(naming_option.get())
            self.open_folder.set(open_folder.get())
            
            # Cerrar diálogo
            dialog.destroy()
            
            # Ejecutar procesamiento
            self.root.after(100, self.ejecutar_procesamiento)  # Pequeño delay para asegurar que el diálogo se cierre
        
        tk.Button(btn_frame, text="Cancelar", command=dialog.destroy, 
                 bg="#E74C3C", fg="white", width=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Aceptar", command=confirmar_y_ejecutar, 
                 bg="#28B463", fg="white", width=10).pack(side="right", padx=5)

    def _select_output_dir_dialog(self, var):
        """Seleccionar carpeta desde el diálogo"""
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    def ejecutar_procesamiento(self):
        """Ejecutar el procesamiento con las opciones seleccionadas"""
        try:
            print("Iniciando procesamiento...")  # Depuración
            print(f"PDF: {self.pdf_path.get()}")
            print(f"Carpeta: {self.output_dir.get()}")
            print(f"Modo: {self.modo_operacion.get()}")
            print(f"Grupos: {self.grupos_paginas}")
            
            reader = PyPDF2.PdfReader(self.pdf_path.get())
            base_name = os.path.splitext(os.path.basename(self.pdf_path.get()))[0]
            output_folder = self.output_dir.get()
            
            # Verificar que la carpeta existe
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
                print(f"Creada carpeta: {output_folder}")
            
            if self.modo_operacion.get() == "dividir":
                print("Modo DIVIDIR: Creando múltiples archivos...")
                archivos_generados = []
                
                for i, grupo in enumerate(self.grupos_paginas, 1):
                    print(f"Procesando grupo {i}: páginas {grupo}")
                    writer = PyPDF2.PdfWriter()
                    for p in grupo:
                        writer.add_page(reader.pages[p - 1])
                    
                    if self.naming_option.get() == 1:
                        detected = self.extract_student_name(reader, [p-1 for p in grupo])
                        final_filename = detected if detected else f"{base_name}_{i}"
                    else:
                        final_filename = f"{base_name}-{i}"
                    
                    final_filename = re.sub(r'[\\/*?:"<>|]', "", final_filename)
                    output_path = os.path.join(output_folder, f"{final_filename}.pdf")
                    
                    with open(output_path, "wb") as f:
                        writer.write(f)
                    
                    archivos_generados.append(output_path)
                    print(f"Archivo guardado: {output_path}")
                
                messagebox.showinfo("Éxito", 
                    f"Se han generado {len(self.grupos_paginas)} archivos en:\n{output_folder}")
            
            else:  # Modo extraer
                print("Modo EXTRAER: Creando un solo archivo...")
                # Un solo archivo con todas las páginas
                writer = PyPDF2.PdfWriter()
                todas_paginas = []
                for grupo in self.grupos_paginas:
                    todas_paginas.extend(grupo)
                todas_paginas.sort()
                
                print(f"Páginas a extraer: {todas_paginas}")
                
                for p in todas_paginas:
                    writer.add_page(reader.pages[p - 1])
                
                if self.naming_option.get() == 1:
                    detected = self.extract_student_name(reader, [todas_paginas[0]-1])
                    final_filename = detected if detected else f"{base_name}_extraido"
                else:
                    final_filename = f"{base_name}_extraido"
                
                final_filename = re.sub(r'[\\/*?:"<>|]', "", final_filename)
                output_path = os.path.join(output_folder, f"{final_filename}.pdf")
                
                with open(output_path, "wb") as f:
                    writer.write(f)
                
                print(f"Archivo guardado: {output_path}")
                messagebox.showinfo("Éxito", 
                    f"Se ha generado 1 archivo con {len(todas_paginas)} páginas en:\n{output_folder}")
            
            if self.open_folder.get():
                print("Abriendo carpeta...")
                if os.name == 'nt':
                    os.startfile(output_folder)
                else:
                    subprocess.run(['open', output_folder])
            
            # Limpiar después del éxito
            self.root.after(500, self.limpiar_despues_procesamiento)
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Ocurrió un fallo:\n{str(e)}")

    def limpiar_despues_procesamiento(self):
        """Limpiar la interfaz después de procesar"""
        self.pdf_path.set("")
        self.paginas_info.set("Páginas totales: -")
        self.grupos_paginas = []
        self.seleccion_actual = []
        self.actualizar_listbox_grupos()
        self.actualizar_entrada_rangos()
        self.actualizar_resaltado_paginas()
        self.actualizar_label_seleccion()
        self.btn_guardar_grupo.config(state="disabled")
        self.btn_run.config(state="disabled")
        
        # Limpiar visor
        for widget in self.frame_miniaturas.winfo_children():
            widget.destroy()

    def extract_student_name(self, reader, pages):
        try:
            text = reader.pages[pages[0]].extract_text()
            match = re.search(r"Apellidos y nombre:\s*([^\n\r]+)", text)
            if match:
                return match.group(1).strip().replace(',', '')
        except:
            pass
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = SeparadorPDF(root)
    root.mainloop()