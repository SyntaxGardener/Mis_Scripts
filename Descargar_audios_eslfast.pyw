#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descargador de audios de ESLfast.com
-------------------------------------
Permite pegar una o varias URLs de páginas de eslfast.com (diálogos, robot,
conversaciones...) y descarga automáticamente el/los archivo(s) de audio
asociados a cada página, guardándolos en la carpeta que elijas.

No requiere librerías externas: solo la biblioteca estándar de Python
(tkinter, urllib). Funciona como doble clic (.pyw, sin consola).
"""

import os
import re
import sys
import threading
import subprocess
import urllib.request
import urllib.parse
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Extensiones de audio que reconocemos dentro del HTML de la página
AUDIO_PATTERN = re.compile(
    r'["\']([^"\'<>\s]+\.(?:mp3|wav|ogg|m4a))["\']',
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def fetch_html(url):
    """Descarga el HTML de la página como texto."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="ignore")


def find_audio_urls(html, page_url):
    """Busca en el HTML cualquier referencia a un archivo de audio y
    devuelve las URLs absolutas, sin duplicados, conservando el orden."""
    found = []
    seen = set()
    for match in AUDIO_PATTERN.finditer(html):
        rel = match.group(1)
        abs_url = urllib.parse.urljoin(page_url, rel)
        if abs_url not in seen:
            seen.add(abs_url)
            found.append(abs_url)
    return found


def safe_filename(audio_url, fallback_slug, index, total):
    """Elige un nombre de archivo razonable para el audio descargado."""
    name = os.path.basename(urllib.parse.urlsplit(audio_url).path)
    if not name or "." not in name:
        suffix = "" if total <= 1 else f"_{index}"
        name = f"{fallback_slug}{suffix}.mp3"
    return name


def download_file(audio_url, dest_folder, fallback_slug, index, total):
    """Descarga un archivo de audio y lo guarda en dest_folder, evitando
    sobrescribir archivos existentes."""
    req = urllib.request.Request(audio_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()

    filename = safe_filename(audio_url, fallback_slug, index, total)
    path = os.path.join(dest_folder, filename)
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(path):
        path = f"{base} ({counter}){ext}"
        counter += 1

    with open(path, "wb") as f:
        f.write(data)
    return path


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Descargador de audios - ESLfast")
        self.geometry("640x600")
        self.minsize(560, 480)

        self.dest_folder = tk.StringVar(
            value=os.path.join(os.path.expanduser("~"), "Desktop")
        )
        self.open_after = tk.BooleanVar(value=True)

        self._build_ui()

    # ---------------------------------------------------------- UI ----
    def _build_ui(self):
        main = tk.Frame(self, padx=14)
        main.pack(fill="both", expand=True)

        # Título: a 5 px del borde superior de la ventana
        header = tk.Label(
            main,
            text="Descargador de audios de ESLfast.com",
            font=("Segoe UI", 13, "bold"),
        )
        header.pack(fill="x", pady=(5, 10), anchor="w")

        tk.Label(
            main,
            text="Pega aquí una o varias URLs de eslfast.com (una por línea):",
            font=("Segoe UI", 10),
        ).pack(fill="x", anchor="w")

        self.url_box = scrolledtext.ScrolledText(
            main, height=8, font=("Segoe UI", 10), wrap="word"
        )
        self.url_box.pack(fill="both", expand=False, pady=(2, 10))
        self.url_box.insert(
            "1.0", "https://www.eslfast.com/easydialogs/ec/dating07.htm"
        )

        # Carpeta de destino
        folder_frame = tk.Frame(main)
        folder_frame.pack(fill="x", pady=(0, 10))
        tk.Label(folder_frame, text="Carpeta de destino:", font=("Segoe UI", 10)).pack(
            side="left"
        )
        self.folder_entry = tk.Entry(
            folder_frame, textvariable=self.dest_folder, font=("Segoe UI", 10)
        )
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        tk.Button(folder_frame, text="Examinar...", command=self.choose_folder).pack(
            side="left"
        )

        # Opciones
        options_frame = tk.Frame(main)
        options_frame.pack(fill="x", pady=(0, 10))
        tk.Checkbutton(
            options_frame,
            text="Abrir la carpeta de destino al terminar",
            variable=self.open_after,
            font=("Segoe UI", 10),
        ).pack(side="left")

        # Botón de descarga
        btn_frame = tk.Frame(main)
        btn_frame.pack(fill="x", pady=(0, 10))
        self.download_btn = tk.Button(
            btn_frame,
            text="Descargar audios",
            font=("Segoe UI", 11, "bold"),
            bg="#2d6cdf",
            fg="white",
            relief="flat",
            padx=12,
            pady=6,
            activebackground="#1f57bf",
            command=self.start_download,
        )
        self.download_btn.pack(side="left")

        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 10))

        # Registro
        tk.Label(main, text="Registro:", font=("Segoe UI", 10)).pack(anchor="w")
        self.log_box = scrolledtext.ScrolledText(
            main, height=10, font=("Consolas", 9), state="disabled"
        )
        self.log_box.pack(fill="both", expand=True)

    # ----------------------------------------------------- acciones ----
    def choose_folder(self):
        folder = filedialog.askdirectory(
            initialdir=self.dest_folder.get() or os.path.expanduser("~")
        )
        if folder:
            self.dest_folder.set(folder)

    def log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def start_download(self):
        urls_raw = self.url_box.get("1.0", "end").strip()
        if not urls_raw:
            messagebox.showwarning("Sin URLs", "Pega al menos una URL de eslfast.com.")
            return
        urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]

        dest = self.dest_folder.get().strip()
        if not dest:
            messagebox.showwarning("Sin carpeta", "Elige una carpeta de destino.")
            return
        try:
            os.makedirs(dest, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo usar esa carpeta:\n{e}")
            return

        self.download_btn.config(state="disabled")
        self.progress["value"] = 0
        self.progress["maximum"] = len(urls)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        thread = threading.Thread(
            target=self.run_downloads, args=(urls, dest), daemon=True
        )
        thread.start()

    def run_downloads(self, urls, dest):
        ok_count = 0
        for i, page_url in enumerate(urls, start=1):
            self.after(0, self.log, f"[{i}/{len(urls)}] Procesando: {page_url}")
            try:
                html = fetch_html(page_url)
                audio_urls = find_audio_urls(html, page_url)
                if not audio_urls:
                    self.after(
                        0, self.log, "    No se encontró audio en esta página."
                    )
                else:
                    slug = (
                        os.path.splitext(
                            os.path.basename(urllib.parse.urlsplit(page_url).path)
                        )[0]
                        or "audio"
                    )
                    for idx, audio_url in enumerate(audio_urls, start=1):
                        try:
                            saved_path = download_file(
                                audio_url, dest, slug, idx, len(audio_urls)
                            )
                            self.after(
                                0,
                                self.log,
                                f"    Guardado: {os.path.basename(saved_path)}",
                            )
                            ok_count += 1
                        except Exception as e:
                            self.after(
                                0,
                                self.log,
                                f"    Error al descargar {audio_url}: {e}",
                            )
            except Exception as e:
                self.after(0, self.log, f"    Error al abrir la página: {e}")

            self.after(0, self._advance_progress, i)

        self.after(0, self.finish_download, ok_count, dest)

    def _advance_progress(self, value):
        self.progress["value"] = value

    def finish_download(self, ok_count, dest):
        self.download_btn.config(state="normal")
        self.log(f"\nTerminado. Audios descargados correctamente: {ok_count}")
        if ok_count == 0:
            messagebox.showinfo(
                "Sin resultados",
                "No se ha podido descargar ningún audio. Revisa las URLs o "
                "el registro para más detalles.",
            )
        elif self.open_after.get():
            self.open_folder(dest)

    def open_folder(self, path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.log(f"No se pudo abrir la carpeta: {e}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
