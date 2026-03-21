
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
import subprocess
import requests
import json
import google.genai as genai
from google.genai import types as genai_types
import time
from pathlib import Path
from datetime import datetime
import configparser as _cp, pathlib as _pl

# ── Modelos disponibles ───────────────────────────────────────────────────────

MODELOS_GEMINI = ["gemini-1.5-flash"]

MODELOS_GROQ = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

MODELOS_CLAUDE = [
    "claude-haiku-4-5-20251001",   # rápido, barato y muy bueno
    "claude-sonnet-4-6",           # el mejor, algo más caro
]

# ── Leer API keys ─────────────────────────────────────────────────────────────

def _leer_api_keys() -> dict:
    cfg_path = _pl.Path(__file__).parent / "config.ini"
    keys = {"gemini": "", "groq": "", "claude": ""}
    if cfg_path.exists():
        cfg = _cp.ConfigParser()
        cfg.read(cfg_path, encoding="utf-8")
        keys["gemini"] = cfg.get("gemini", "api_key", fallback="").strip()
        keys["groq"]   = cfg.get("groq",   "api_key", fallback="").strip()
        keys["claude"] = cfg.get("claude", "api_key", fallback="").strip()
    return keys

# ── Extracción de texto ───────────────────────────────────────────────────────

def extraer_texto_pdf(ruta: str) -> str:
    try:
        import pdfplumber
        texto = []
        with pdfplumber.open(ruta) as pdf:
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    texto.append(t)
        return "\n".join(texto)
    except ImportError:
        from pypdf import PdfReader
        reader = PdfReader(ruta)
        return "\n".join(p.extract_text() or "" for p in reader.pages)


def extraer_texto_docx(ruta: str) -> str:
    from docx import Document
    doc = Document(ruta)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extraer_texto_web(url: str) -> str:
    import requests
    from bs4 import BeautifulSoup
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ResumidorBot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def obtener_texto(fuente: str) -> str:
    fuente = fuente.strip()
    if fuente.startswith("http://") or fuente.startswith("https://"):
        return extraer_texto_web(fuente)
    ext = Path(fuente).suffix.lower()
    if ext == ".pdf":
        return extraer_texto_pdf(fuente)
    if ext in (".docx", ".doc"):
        return extraer_texto_docx(fuente)
    raise ValueError(f"Formato no soportado: '{ext}'. Usa PDF, DOCX o URL.")


# ── Construcción del prompt ───────────────────────────────────────────────────
# Estrategia: instrucciones al principio + recordatorio ANTES del texto
# para que los modelos pequeños (Groq) no las pierdan de vista.

def _recordatorio_resumen(idioma: str) -> str:
    return (
        f"ANTES DE ESCRIBIR, repasa estas reglas:\n"
        f"• Por cada término, concepto, figura, recurso o regla que aparezca en el texto:\n"
        f"  1. Escríbelo en negrita o en mayúsculas como encabezado.\n"
        f"  2. Escribe su definición en 1-2 frases sencillas, como si se lo explicaras\n"
        f"     a un alumno de secundaria que nunca lo ha oído.\n"
        f"  3. Pon un ejemplo concreto y breve (una frase es suficiente).\n"
        f"• PROHIBIDO escribir frases del tipo 'entre las figuras encontramos X, Y, Z'\n"
        f"  sin explicar qué es cada una. Si nombras algo, defínelo en el acto.\n"
        f"• Usa el formato exacto para cada entrada:\n"
        f"    ▸ NOMBRE\n"
        f"      Definición: ...\n"
        f"      Ejemplo: ...\n"
        f"• Agrupa las entradas por temas con encabezado: ══ TEMA: [título] ══\n"
        f"• Idioma de toda la respuesta: {idioma}.\n"
        f"\nAhora genera el glosario-esquema del siguiente texto:\n"
    )

def _recordatorio_examen(secciones_txt: str, tiene_lectora: bool, tiene_literaria: bool) -> str:
    partes = [
        "RECUERDA ANTES DE EMPEZAR:",
        f"• Genera EXACTAMENTE estas secciones, en este orden:\n{secciones_txt}",
    ]
    if tiene_lectora:
        partes.append("• Sección COMPRENSIÓN LECTORA: el texto debe tener MÍNIMO 175 palabras y MÁXIMO 250. Cuenta las palabras antes de terminar.")
    if tiene_literaria:
        partes.append("• Sección COMPRENSIÓN LITERARIA: el fragmento debe tener MÍNIMO 200 palabras y MÁXIMO 300. Cuenta las palabras antes de terminar.")
    partes.append("• Las respuestas correctas SOLO en la sección CLAVE DE RESPUESTAS al final, nunca en el cuerpo.")
    partes.append("Ahora genera el examen basándote en el siguiente texto:\n")
    return "\n".join(partes)

def construir_prompt(tipo: str, idioma: str, secciones_examen: dict = None) -> dict:
    """Devuelve {"inicio": str, "recordatorio": str} para colocar el recordatorio
    justo antes del texto y así reforzar las instrucciones en modelos pequeños."""

    instrucciones = {
        "Contenido": (
            f"Genera un resumen completo y detallado del siguiente texto en {idioma}. "
            "Desarrolla cada idea principal en un párrafo propio con explicación suficiente. "
            "No hagas un resumen telegráfico: cada punto debe quedar bien explicado.",
            f"RECUERDA: respuesta en {idioma}, resumen detallado con cada idea bien desarrollada.\nTexto a resumir:\n"
        ),
        "Esquema": (
            f"Genera un esquema estructurado con jerarquía de puntos (usa ►, •, -) "
            f"del siguiente texto en {idioma}. Incluye título, todas las secciones y sus puntos clave.",
            f"RECUERDA: esquema completo en {idioma}, sin omitir secciones.\nTexto:\n"
        ),
        "Puntos clave": (
            f"Extrae los puntos clave más importantes del siguiente texto en {idioma}. "
            "Presenta cada punto con una viñeta (•) y desarróllalo en 2-3 frases, no en una sola palabra.",
            f"RECUERDA: cada punto clave desarrollado en 2-3 frases, en {idioma}.\nTexto:\n"
        ),
        "Resumen": (
            f"Eres un profesor de {idioma} de secundaria. "
            f"Tu tarea es generar un GLOSARIO-ESQUEMA del siguiente texto "
            f"que sirva a los alumnos para estudiar SIN necesitar el original.\n"
            "\n"
            "REGLA ÚNICA E IRROMPIBLE:\n"
            "Cada término, concepto, figura literaria, recurso, regla gramatical "
            "o cualquier elemento con nombre propio que aparezca en el texto "
            "DEBE aparecer en tu respuesta con este formato EXACTO:\n"
            "  ▸ NOMBRE (en mayúsculas)\n"
            "    Definición: una o dos frases claras y sencillas.\n"
            "    Ejemplo: una frase corta que ilustre el concepto.\n"
            "\n"
            "NUNCA escribas frases como 'las figuras son: metáfora, hipérbole...'\n"
            "sin definir cada una. Nombrar sin definir está PROHIBIDO.\n"
            "\n"
            "ESTRUCTURA de la respuesta:\n"
            "  ══ TEMA: [título del tema] ══\n"
            "  (una o dos frases de introducción muy breve)\n"
            "  ▸ CONCEPTO 1\n"
            "    Definición: ...\n"
            "    Ejemplo: ...\n"
            "  ▸ CONCEPTO 2\n"
            "    Definición: ...\n"
            "    Ejemplo: ...\n"
            "  (repite para todos los conceptos del tema)\n"
            "\n"
            "Repite el bloque ══ TEMA ══ para cada tema o unidad del texto.\n"
            "Al final, escribe 3-5 PREGUNTAS DE REPASO sin respuesta.\n"
            "No escribas párrafos de relleno ni resumas el argumento: "
            "solo el glosario-esquema con el formato indicado.",
            None  # el recordatorio se construye dinámicamente
        ),
        "Cuestionario": (
            f"Genera un cuestionario de 10 preguntas con 4 opciones de respuesta (A, B, C, D) "
            f"basado en el siguiente texto en {idioma}. "
            "Pregunta numerada, las 4 opciones en líneas separadas, "
            "y al final de cada pregunta indica entre paréntesis cuál es la respuesta correcta. "
            "Las preguntas deben cubrir los conceptos más importantes.",
            f"RECUERDA: 10 preguntas, 4 opciones cada una, respuesta correcta entre paréntesis, en {idioma}.\nTexto:\n"
        ),
        "Examen": (None, None),  # se construye abajo
    }

    if tipo == "Resumen":
        inicio = instrucciones["Resumen"][0]
        recordatorio = _recordatorio_resumen(idioma)
        return {"inicio": inicio, "recordatorio": recordatorio}

    if tipo == "Examen" and secciones_examen:
        secs = []
        clave_secs = []
        n = 1
        tiene_lectora   = False
        tiene_literaria = False
        if secciones_examen.get("verdadero_falso"):
            secs.append(f"{n}) VERDADERO/FALSO: 5 afirmaciones. NO incluyas la respuesta correcta en el enunciado.")
            clave_secs.append(f"Sección {n} — Verdadero/Falso"); n += 1
        if secciones_examen.get("opcion_multiple"):
            secs.append(f"{n}) OPCIÓN MÚLTIPLE: 5 preguntas con opciones A, B, C, D. NO marques la correcta en el enunciado.")
            clave_secs.append(f"Sección {n} — Opción múltiple"); n += 1
        if secciones_examen.get("comprension_lectora"):
            tiene_lectora = True
            secs.append(
                f"{n}) COMPRENSIÓN LECTORA:\n"
                f"   TEXTO: redacta un texto descriptivo, expositivo o argumentativo original, "
                f"adaptado al nivel. OBLIGATORIO: mínimo 175 palabras, máximo 250. "
                f"Cuenta las palabras y ajusta si es necesario.\n"
                f"   PREGUNTAS: 5 preguntas de comprensión sobre ese texto."
            )
            n += 1
        if secciones_examen.get("comprension_literaria"):
            tiene_literaria = True
            secs.append(
                f"{n}) COMPRENSIÓN LECTORA (TEXTO LITERARIO):\n"
                f"   TEXTO: escribe un fragmento literario original (narrativo o poético), "
                f"adaptado al nivel y relacionado con el documento. "
                f"OBLIGATORIO: mínimo 200 palabras, máximo 300. "
                f"Cuenta las palabras y ajusta si es necesario.\n"
                f"   PREGUNTAS: 5 preguntas de comprensión y análisis literario."
            )
            clave_secs.append(f"Sección {n} — Comprensión literaria"); n += 1
        if secciones_examen.get("expresion_escrita"):
            secs.append(
                f"{n}) EXPRESIÓN ESCRITA:\n"
                f"   Propón 1 tarea de redacción concreta y motivadora (carta, descripción, "
                f"narración breve, exposición, argumentación, creación literaria...) "
                f"relacionada con el documento. "
                f"Indica tipo de texto, extensión aproximada (80-150 palabras) "
                f"y una pauta de ayuda con 3-4 puntos."
            )
            n += 1
        if secciones_examen.get("comprension_oral"):
            secs.append(f"{n}) COMPRENSIÓN ORAL: describe 1-2 actividades de escucha relacionadas con el tema.")
            n += 1
        if secciones_examen.get("preguntas_cortas"):
            secs.append(f"{n}) PREGUNTAS CORTAS: 3 preguntas de respuesta breve.")
            n += 1
        if secciones_examen.get("desarrollo"):
            secs.append(f"{n}) DESARROLLO: 1 pregunta de respuesta elaborada.")
            n += 1

        clave_txt = (
            f"\nAl final del examen añade una sección 'CLAVE DE RESPUESTAS' "
            f"con las respuestas correctas de: {', '.join(clave_secs)}. "
            f"NO incluyas respuestas en el cuerpo del examen."
            if clave_secs else ""
        )
        secs_txt = "\n".join(secs)
        inicio = (
            f"Genera un examen formal en {idioma} con estas secciones, en este orden:\n"
            f"{secs_txt}{clave_txt}"
        )
        recordatorio = _recordatorio_examen(secs_txt, tiene_lectora, tiene_literaria)
        return {"inicio": inicio, "recordatorio": recordatorio}

    # Tipos simples
    inicio_txt, rec_txt = instrucciones.get(tipo, instrucciones["Contenido"])
    return {"inicio": inicio_txt, "recordatorio": rec_txt}


# ── Llamada a Gemini ──────────────────────────────────────────────────────────

def llamar_gemini(prompt: str, api_key: str, log_fn=None) -> tuple:
    import requests
    import json
    import time

    # 1. Función interna para listar modelos disponibles si el predeterminado falla
    def obtener_modelo_valido():
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        try:
            res = requests.get(list_url, timeout=10)
            if res.status_code == 200:
                modelos = res.json().get('models', [])
                # Buscamos cualquiera que diga '1.5-flash' o simplemente el primero que soporte generar contenido
                for m in modelos:
                    nombre = m['name'].split('/')[-1]
                    if "1.5-flash" in nombre and "generateContent" in m.get('supportedGenerationMethods', []):
                        return nombre
                # Si no hay flash, devolvemos el primero disponible
                return modelos[0]['name'].split('/')[-1]
        except: pass
        return "gemini-1.5-flash" # Fallback por si acaso

    nombre_modelo = "gemini-1.5-flash"
    ultimo_error = None

    for intento in range(2):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{nombre_modelo}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            if log_fn: log_fn(f"  Intentando con: {nombre_modelo}...")
            response = requests.post(url, json=payload, timeout=90)
            
            if response.status_code == 200:
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text'], nombre_modelo
            
            elif response.status_code == 404:
                if log_fn: log_fn("  ⚠ Modelo no encontrado. Buscando alternativa...")
                nombre_modelo = obtener_modelo_valido() # <--- AQUÍ BUSCAMOS EL NOMBRE REAL
                continue 
            
            elif response.status_code == 429:
                time.sleep(65)
                continue
            else:
                raise Exception(f"Error {response.status_code}")

        except Exception as e:
            ultimo_error = e
            time.sleep(2)
            
    raise Exception(f"Fallo total. Google dice: {ultimo_error}")

# ── Llamada a Groq ────────────────────────────────────────────────────────────

def llamar_groq(prompt: str, api_key: str, log_fn=None) -> tuple:
    from groq import Groq
    client = Groq(api_key=api_key)
    ultimo_error = None
    for nombre_modelo in MODELOS_GROQ:
        if log_fn:
            log_fn(f"  Groq — modelo: {nombre_modelo}")
        for intento in range(3):
            try:
                r = client.chat.completions.create(
                    model=nombre_modelo,
                    messages=[
                        {"role": "system", "content": "Eres un asistente experto en análisis y síntesis de documentos."},
                        {"role": "user",   "content": prompt},
                    ],
                    max_tokens=6000,
                    temperature=0.3,
                )
                return r.choices[0].message.content, nombre_modelo
            except Exception as e:
                ultimo_error = e
                msg = str(e).lower()
                if any(k in msg for k in ["rate_limit", "429", "too many"]):
                    espera = 15 * (intento + 1)
                    if log_fn:
                        log_fn(f"  ⚠ Límite RPM Groq. Esperando {espera}s…")
                    time.sleep(espera)
                    continue
                break
    raise Exception(f"Groq: error tras todos los modelos: {ultimo_error}")


# ── Llamada a Claude ─────────────────────────────────────────────────────────

def llamar_claude(prompt: str, api_key: str, log_fn=None) -> tuple:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    ultimo_error = None
    for nombre_modelo in MODELOS_CLAUDE:
        if log_fn:
            log_fn(f"  Claude — modelo: {nombre_modelo}")
        for intento in range(2):
            try:
                msg = client.messages.create(
                    model=nombre_modelo,
                    max_tokens=8192,
                    system="Eres un asistente experto en análisis y síntesis de documentos.",
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text, nombre_modelo
            except Exception as e:
                ultimo_error = e
                msg_err = str(e).lower()
                if "529" in msg_err or "overloaded" in msg_err or "rate" in msg_err:
                    espera = 20 * (intento + 1)
                    if log_fn:
                        log_fn(f"  ⚠ Servidor ocupado. Esperando {espera}s…")
                    time.sleep(espera)
                    continue
                break
    raise Exception(f"Claude: error tras todos los modelos: {ultimo_error}")


# ── Motor principal ───────────────────────────────────────────────────────────

CHUNK_GEMINI = 15_000
CHUNK_GROQ   = 20_000
SOLAPAMIENTO = 500


def _verificar_resumen(resultado: str, api_key: str, proveedor: str,
                       idioma: str, _llamar, log_fn=None) -> str:
    """Solo para Groq: segunda pasada que detecta términos sin definir y los completa."""
    if proveedor != "Groq":
        return resultado
    if log_fn:
        log_fn("  ✏ Verificando términos sin definir…")
    prompt_verif = (
        f"Tienes el siguiente glosario-esquema en {idioma}. "
        f"Tu tarea es detectar si hay algún término, concepto o figura literaria que aparezca "
        f"mencionado pero sin su bloque completo (▸ NOMBRE / Definición / Ejemplo).\n"
        f"Si encuentras alguno, añade su bloque completo en el lugar correcto.\n"
        f"Si todos los términos ya están bien definidos, devuelve el texto exactamente igual.\n"
        f"NO resumas, NO elimines nada, NO cambies el formato. Solo añade los bloques que falten.\n\n"
        f"GLOSARIO A REVISAR:\n\n{resultado}"
    )
    try:
        revisado, _ = _llamar(prompt_verif, api_key, log_fn)
        return revisado
    except Exception:
        return resultado  # si falla la verificación, devolver el original


def _armar_prompt(partes: dict, texto: str) -> str:
    """Construye el prompt final: instrucciones + recordatorio + texto."""
    inicio = partes["inicio"]
    rec    = partes["recordatorio"] or ""
    return f"{inicio}\n\n---\n\n{rec}{texto}"


def resumir(texto: str, api_key: str, proveedor: str, tipo: str, idioma: str,
            secciones_examen: dict = None, log_fn=None) -> tuple:
    """Devuelve (resultado, modelo_usado). Delega en Gemini o Groq según proveedor."""

    if proveedor == "Gemini":
        _llamar = llamar_gemini
        chunk   = CHUNK_GEMINI
    elif proveedor == "Claude":
        _llamar = llamar_claude
        chunk   = CHUNK_GEMINI   # Claude tiene contexto grande, mismo chunk que Gemini
    else:
        _llamar = llamar_groq
        chunk   = CHUNK_GROQ
    partes_base = construir_prompt(tipo, idioma, secciones_examen)

    # ── Documento corto ───────────────────────────────────────────────────────
    if len(texto) <= chunk:
        if log_fn:
            log_fn("  Documento corto — procesando directamente…")
        resultado, modelo_usado = _llamar(_armar_prompt(partes_base, texto), api_key, log_fn)
        if tipo == "Resumen":
            resultado = _verificar_resumen(resultado, api_key, proveedor, idioma, _llamar, log_fn)
        return resultado, modelo_usado

    # ── Documento largo: fragmentos + síntesis ────────────────────────────────
    fragmentos = []
    inicio = 0
    while inicio < len(texto):
        fin = min(inicio + chunk, len(texto))
        fragmentos.append(texto[inicio:fin])
        inicio = fin - SOLAPAMIENTO if fin < len(texto) else fin

    total_frags = len(fragmentos)
    if log_fn:
        log_fn(f"  Documento largo — {total_frags} fragmentos a procesar…")

    resumenes_parciales = []
    modelo_usado = ""
    for i, frag in enumerate(fragmentos, 1):
        if log_fn:
            log_fn(f"  Fragmento {i}/{total_frags}…")
        p = (f"Este es el fragmento {i} de {total_frags} de un documento más largo.\n"
             f"Resume los puntos clave de ESTE fragmento en {idioma}, "
             f"con suficiente detalle (no telegráfico):\n\n{frag}")
        r, modelo_usado = _llamar(p, api_key, log_fn)
        resumenes_parciales.append(f"[Fragmento {i}/{total_frags}]\n{r}")
        if i < total_frags:
            if log_fn:
                log_fn("  Pausa entre fragmentos…")
            time.sleep(8 if proveedor == "Groq" else 40)

    if log_fn:
        log_fn("  Generando síntesis final…")

    texto_parciales = "\n\n".join(resumenes_parciales)

    # Prompts de síntesis: también con recordatorio al final
    prompts_sintesis = {
        "Contenido": {
            "inicio":
                f"A partir de los siguientes resúmenes parciales de un documento, "
                f"genera un RESUMEN FINAL completo y bien desarrollado en {idioma}. "
                f"Cada idea debe estar suficientemente explicada, no en telegráfico.",
            "recordatorio":
                f"RECUERDA: resumen detallado en {idioma}, cada idea desarrollada.\nResúmenes:\n",
        },
        "Esquema": {
            "inicio":
                f"A partir de los siguientes resúmenes parciales, genera un ESQUEMA FINAL "
                f"completo y estructurado en {idioma} (usa ►, •, -) con todas las secciones.",
            "recordatorio":
                f"RECUERDA: esquema completo en {idioma}, sin omitir secciones.\nResúmenes:\n",
        },
        "Puntos clave": {
            "inicio":
                f"A partir de los siguientes resúmenes parciales, extrae y consolida los "
                f"PUNTOS CLAVE más importantes en {idioma}. Cada punto desarrollado en 2-3 frases.",
            "recordatorio":
                f"RECUERDA: cada punto clave con 2-3 frases de desarrollo, en {idioma}.\nResúmenes:\n",
        },
        "Resumen": {
            "inicio":
                f"Eres un profesor de {idioma} de secundaria. "
                f"A partir de los siguientes fragmentos resumidos, genera un GLOSARIO-ESQUEMA "
                f"completo que sirva a los alumnos para estudiar SIN el original.\n\n"
                f"REGLA ÚNICA: cada concepto, figura, recurso o término con nombre propio "
                f"DEBE aparecer con este formato:\n"
                f"  ▸ NOMBRE\n"
                f"    Definición: frase clara y sencilla.\n"
                f"    Ejemplo: frase corta.\n\n"
                f"NUNCA listes nombres sin definirlos. "
                f"Agrupa por temas con ══ TEMA: [título] ══. "
                f"Al final, 3-5 PREGUNTAS DE REPASO sin respuesta.",
            "recordatorio":
                f"RECUERDA: formato ▸ NOMBRE / Definición / Ejemplo por cada concepto, "
                f"agrupado por temas, en {idioma}.\nFragmentos:\n",
        },
        "Cuestionario": {
            "inicio":
                f"A partir de los siguientes resúmenes parciales, genera un CUESTIONARIO FINAL "
                f"de 10 preguntas con 4 opciones (A, B, C, D) en {idioma}. "
                f"Indica la respuesta correcta entre paréntesis al final de cada pregunta.",
            "recordatorio":
                f"RECUERDA: 10 preguntas, 4 opciones, respuesta correcta entre paréntesis, en {idioma}.\nResúmenes:\n",
        },
        "Examen": partes_base,
    }
    partes_sintesis = prompts_sintesis.get(tipo, prompts_sintesis["Resumen"])
    resultado, modelo_usado = _llamar(
        _armar_prompt(partes_sintesis, texto_parciales), api_key, log_fn
    )
    return _verificar_resumen(resultado, api_key, proveedor, idioma, _llamar, log_fn) if tipo == "Resumen" else resultado, modelo_usado


# ── Colores ───────────────────────────────────────────────────────────────────

BG       = "#f4f4f8"
PANEL    = "#e8e8f0"
ENTRADA  = "#ffffff"
ACENTO   = "#5b4fcf"
ACENTO2  = "#2976d4"
TEXTO    = "#1a1a2e"
SUBTEXTO = "#666688"
EXITO    = "#1a7a3c"
ERROR    = "#c0392b"
BORDE    = "#ccccdd"

F_MONO   = ("Consolas", 10)
F_NORM   = ("Segoe UI", 10)
F_TITULO = ("Segoe UI", 13, "bold")
F_LABEL  = ("Segoe UI", 9)
F_BOLD   = ("Segoe UI", 9, "bold")

CONFIG_FILE = Path.home() / ".resumidor_config.json"


# ── Aplicación ────────────────────────────────────────────────────────────────

class ResumidorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Resúmenes y Exámenes con IA · Groq / Gemini / Claude")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._cargar_config()
        self._construir_ui()
        self._centrar_ventana(920, 700)
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

    # ── Config ────────────────────────────────────────────────────────────────

    def _cargar_config(self):
        self.cfg = {}
        if CONFIG_FILE.exists():
            try:
                self.cfg = json.loads(CONFIG_FILE.read_text())
            except Exception:
                pass

    def _guardar_config(self):
        self.cfg["carpeta_sal"] = self.var_carpeta.get().strip()
        self.cfg["tipo"]        = self.var_tipo.get()
        self.cfg["idioma"]      = self.var_idioma.get()
        self.cfg["proveedor"]   = self.var_proveedor.get()
        self.cfg["modelo"]      = self.var_modelo.get()
        try:
            CONFIG_FILE.write_text(json.dumps(self.cfg, indent=2))
        except Exception:
            pass

    def _al_cerrar(self):
        self._guardar_config()
        self.destroy()

    def _centrar_ventana(self, w: int, h: int):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        self.geometry(f"{w}x{h}+{x}+5")
        self.minsize(700, 520)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _construir_ui(self):
        self._estilo_combo()

        # Cabecera
        cab = tk.Frame(self, bg=ACENTO, pady=10)
        cab.pack(fill="x")
        tk.Label(cab, text="✦ Resúmenes · Cuestionarios · Exámenes con IA",
                 font=F_TITULO, bg=ACENTO, fg="white").pack(side="left", padx=18)
        tk.Label(cab, text="Powered by Groq / Gemini / Claude",
                 font=F_LABEL, bg=ACENTO, fg="#ccc8ff").pack(side="right", padx=18)

        paned = tk.PanedWindow(self, orient="horizontal", bg=BG,
                               sashwidth=5, sashrelief="flat", sashpad=2)
        paned.pack(fill="both", expand=True, padx=10, pady=8)

        # ── Columna izquierda ─────────────────────────────────────────────────
        izq_outer = tk.Frame(paned, bg=BG)
        paned.add(izq_outer, minsize=250, width=300)

        canvas_izq = tk.Canvas(izq_outer, bg=BG, highlightthickness=0)
        sb_izq = ttk.Scrollbar(izq_outer, orient="vertical", command=canvas_izq.yview)
        canvas_izq.configure(yscrollcommand=sb_izq.set)
        sb_izq.pack(side="right", fill="y")
        canvas_izq.pack(side="left", fill="both", expand=True)

        izq = tk.Frame(canvas_izq, bg=BG, padx=10)
        izq_window = canvas_izq.create_window((0, 0), window=izq, anchor="nw")

        def _on_izq_configure(e):
            canvas_izq.configure(scrollregion=canvas_izq.bbox("all"))
        def _on_canvas_resize(e):
            canvas_izq.itemconfig(izq_window, width=e.width)
        izq.bind("<Configure>", _on_izq_configure)
        canvas_izq.bind("<Configure>", _on_canvas_resize)

        def _scroll_izq(e):
            canvas_izq.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas_izq.bind_all("<MouseWheel>", _scroll_izq)

        # Proveedor
        self._lbl(izq, "🤖  Proveedor de IA")
        self.var_proveedor = tk.StringVar(value=self.cfg.get("proveedor", "Groq"))
        fr_prov = tk.Frame(izq, bg=BG)
        fr_prov.pack(fill="x", pady=(0, 4))
        for prov in ("Groq", "Gemini", "Claude"):
            tk.Radiobutton(fr_prov, text=prov, variable=self.var_proveedor, value=prov,
                           font=F_NORM, bg=BG, fg=TEXTO,
                           activebackground=BG, activeforeground=ACENTO,
                           selectcolor=PANEL, relief="flat",
                           command=self._actualizar_modelos).pack(side="left", padx=(0, 12))

        # Modelo
        self._lbl(izq, "   Modelo")
        self.var_modelo = tk.StringVar(value=self.cfg.get("modelo", MODELOS_GROQ[0]))
        self.combo_modelo = ttk.Combobox(izq, textvariable=self.var_modelo,
                                         state="readonly", font=F_NORM)
        self.combo_modelo.pack(fill="x", pady=(0, 8))
        self._actualizar_modelos()

        # Tipo de salida
        self._lbl(izq, "📝  Tipo de documento a generar")
        self.var_tipo = tk.StringVar(value=self.cfg.get("tipo", "Contenido"))
        for op in ("Contenido", "Esquema", "Puntos clave", "Resumen", "Cuestionario", "Examen"):
            tk.Radiobutton(izq, text=op, variable=self.var_tipo, value=op,
                           font=F_NORM, bg=BG, fg=TEXTO,
                           activebackground=BG, activeforeground=ACENTO,
                           selectcolor=PANEL, relief="flat",
                           command=self._toggle_secciones).pack(anchor="w", pady=1)

        # Secciones examen
        self.frame_secciones = tk.Frame(izq, bg=PANEL, padx=8, pady=6,
                                        relief="solid", bd=1)
        tk.Label(self.frame_secciones, text="Secciones del examen:",
                 font=F_BOLD, bg=PANEL, fg=SUBTEXTO).pack(anchor="w", pady=(0, 4))

        self.sec_vars = {
            "verdadero_falso":         tk.BooleanVar(value=True),
            "opcion_multiple":         tk.BooleanVar(value=True),
            "comprension_lectora":     tk.BooleanVar(value=False),
            "comprension_literaria":   tk.BooleanVar(value=False),
            "expresion_escrita":       tk.BooleanVar(value=False),
            "comprension_oral":        tk.BooleanVar(value=False),
            "preguntas_cortas":        tk.BooleanVar(value=True),
            "desarrollo":              tk.BooleanVar(value=True),
        }
        sec_labels = {
            "verdadero_falso":         "Verdadero / Falso",
            "opcion_multiple":         "Opción múltiple",
            "comprension_lectora":     "Comprensión lectora",
            "comprension_literaria":   "Comprensión lectora (texto literario)",
            "expresion_escrita":       "Expresión escrita (redacción)",
            "comprension_oral":        "Comprensión oral",
            "preguntas_cortas":        "Preguntas cortas",
            "desarrollo":              "Desarrollo",
        }
        for key, label in sec_labels.items():
            tk.Checkbutton(self.frame_secciones, text=label,
                           variable=self.sec_vars[key],
                           font=F_LABEL, bg=PANEL, fg=TEXTO,
                           activebackground=PANEL, activeforeground=ACENTO,
                           selectcolor=ENTRADA, relief="flat").pack(anchor="w", pady=1)

        # Idioma
        self._lbl(izq, "🌐  Idioma de salida")
        self.var_idioma = tk.StringVar(value=self.cfg.get("idioma", "Español"))
        idiomas = ["Español", "English", "Français", "Deutsch",
                   "Italiano", "Português", "中文", "日本語"]
        ttk.Combobox(izq, textvariable=self.var_idioma,
                     values=idiomas, state="readonly",
                     font=F_NORM).pack(fill="x", pady=(0, 10))

        # Carpeta de destino
        self._lbl(izq, "📁  Carpeta de destino")
        self.var_carpeta = tk.StringVar(
            value=self.cfg.get("carpeta_sal", str(Path.home() / "Resumenes")))
        fr_carp = tk.Frame(izq, bg=BG)
        fr_carp.pack(fill="x", pady=(0, 4))
        tk.Entry(fr_carp, textvariable=self.var_carpeta, font=F_NORM,
                 bg=ENTRADA, fg=TEXTO, relief="solid", bd=1).pack(
                     side="left", fill="x", expand=True)
        tk.Button(fr_carp, text="…", font=F_NORM, bg=ACENTO, fg="white",
                  relief="flat", cursor="hand2",
                  command=self._elegir_carpeta).pack(side="left", padx=(3, 0))

        tk.Button(izq, text="📂  Abrir carpeta de destino",
                  font=F_LABEL, bg=PANEL, fg=ACENTO2,
                  relief="flat", cursor="hand2", pady=6,
                  command=self._abrir_carpeta).pack(fill="x", pady=(4, 10))

        # ── Columna derecha ───────────────────────────────────────────────────
        der = tk.Frame(paned, bg=BG, padx=8)
        paned.add(der, minsize=400)

        self._lbl(der, "📄  Documentos / URLs  (uno por línea)")
        fr_txt = tk.Frame(der, bg=BORDE, bd=1, relief="solid")
        fr_txt.pack(fill="both", expand=False, pady=(0, 6))
        self.txt_fuentes = tk.Text(fr_txt, height=7, font=F_MONO,
                                   bg=ENTRADA, fg=TEXTO,
                                   insertbackground=TEXTO, relief="flat",
                                   bd=6, wrap="none",
                                   selectbackground=ACENTO,
                                   selectforeground="white")
        sb_f = ttk.Scrollbar(fr_txt, orient="vertical",
                             command=self.txt_fuentes.yview)
        self.txt_fuentes.configure(yscrollcommand=sb_f.set)
        self.txt_fuentes.pack(side="left", fill="both", expand=True)
        sb_f.pack(side="right", fill="y")

        self.menu_ctx = tk.Menu(self, tearoff=0, bg=ENTRADA, fg=TEXTO,
                                activebackground=ACENTO, activeforeground="white",
                                relief="flat", bd=1)
        self.menu_ctx.add_command(label="📋  Pegar",  command=self._pegar,  accelerator="Ctrl+V")
        self.menu_ctx.add_command(label="✂️  Cortar", command=self._cortar, accelerator="Ctrl+X")
        self.menu_ctx.add_command(label="📄  Copiar", command=self._copiar, accelerator="Ctrl+C")
        self.menu_ctx.add_separator()
        self.menu_ctx.add_command(label="✖  Limpiar todo",
                                  command=lambda: self.txt_fuentes.delete("1.0", "end"))
        self.txt_fuentes.bind("<Button-3>", self._mostrar_menu_ctx)

        fr_bts = tk.Frame(der, bg=BG)
        fr_bts.pack(fill="x", pady=(0, 6))
        tk.Button(fr_bts, text="＋ Agregar archivos", font=F_NORM,
                  bg=PANEL, fg=TEXTO, relief="flat", cursor="hand2",
                  padx=10, pady=5,
                  command=self._agregar_archivos).pack(side="left")
        tk.Button(fr_bts, text="✖ Limpiar", font=F_NORM,
                  bg=PANEL, fg=SUBTEXTO, relief="flat", cursor="hand2",
                  padx=10, pady=5,
                  command=lambda: self.txt_fuentes.delete("1.0", "end")
                  ).pack(side="left", padx=6)
        self.btn_procesar = tk.Button(
            fr_bts, text="▶  PROCESAR",
            font=("Segoe UI", 10, "bold"), bg=ACENTO, fg="white",
            relief="flat", cursor="hand2", padx=16, pady=5,
            command=self._iniciar_procesamiento)
        self.btn_procesar.pack(side="right")

        self._lbl(der, "📋  Resultados")
        fr_res = tk.Frame(der, bg=BORDE, bd=1, relief="solid")
        fr_res.pack(fill="both", expand=True)
        self.txt_resultado = scrolledtext.ScrolledText(
            fr_res, font=F_MONO, bg=ENTRADA, fg=TEXTO,
            insertbackground=TEXTO, relief="flat", bd=6,
            wrap="word", selectbackground=ACENTO,
            selectforeground="white", state="disabled")
        self.txt_resultado.pack(fill="both", expand=True)

        barra = tk.Frame(self, bg=PANEL)
        barra.pack(fill="x", side="bottom")
        self.var_estado = tk.StringVar(value="Listo.")
        tk.Label(barra, textvariable=self.var_estado,
                 font=F_LABEL, bg=PANEL, fg=SUBTEXTO,
                 anchor="w").pack(side="left", padx=12, pady=5)
        self.progreso = ttk.Progressbar(barra, mode="indeterminate", length=120)
        self.progreso.pack(side="right", padx=12, pady=5)

        self._toggle_secciones()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _lbl(self, padre, texto: str):
        tk.Label(padre, text=texto, font=F_BOLD,
                 bg=BG, fg=SUBTEXTO).pack(anchor="w", pady=(8, 2))

    def _estilo_combo(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TCombobox",
                    fieldbackground=ENTRADA, background=ENTRADA,
                    foreground=TEXTO, arrowcolor=ACENTO,
                    bordercolor=BORDE, lightcolor=ENTRADA,
                    darkcolor=ENTRADA, selectbackground=ACENTO,
                    selectforeground="white")
        s.configure("TScrollbar", background=PANEL,
                    troughcolor=BG, arrowcolor=SUBTEXTO)

    def _actualizar_modelos(self):
        prov = self.var_proveedor.get()
        if prov == "Groq":
            modelos = MODELOS_GROQ
        elif prov == "Claude":
            modelos = MODELOS_CLAUDE
        else:
            modelos = MODELOS_GEMINI
        self.combo_modelo["values"] = modelos
        if self.var_modelo.get() not in modelos:
            self.var_modelo.set(modelos[0])

    def _toggle_secciones(self):
        if self.var_tipo.get() == "Examen":
            self.frame_secciones.pack(fill="x", pady=(0, 8))
        else:
            self.frame_secciones.pack_forget()

    def _elegir_carpeta(self):
        d = filedialog.askdirectory(title="Selecciona carpeta de destino")
        if d:
            self.var_carpeta.set(d)

    def _abrir_carpeta(self):
        carpeta = self.var_carpeta.get().strip()
        if not carpeta:
            return
        Path(carpeta).mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(carpeta)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", carpeta])
        else:
            subprocess.Popen(["xdg-open", carpeta])

    def _agregar_archivos(self):
        archivos = filedialog.askopenfilenames(
            title="Selecciona documentos",
            filetypes=[("Documentos", "*.pdf *.docx *.doc"),
                       ("PDF", "*.pdf"), ("Word", "*.docx *.doc"),
                       ("Todos", "*.*")])
        for ruta in archivos:
            self.txt_fuentes.insert("end", ruta + "\n")

    def _mostrar_menu_ctx(self, event):
        try:
            self.menu_ctx.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu_ctx.grab_release()

    def _pegar(self):
        try:
            self.txt_fuentes.insert(tk.INSERT, self.clipboard_get())
        except tk.TclError:
            pass

    def _cortar(self):
        try:
            self.txt_fuentes.event_generate("<<Cut>>")
        except tk.TclError:
            pass

    def _copiar(self):
        try:
            self.txt_fuentes.event_generate("<<Copy>>")
        except tk.TclError:
            pass

    # ── Procesamiento ─────────────────────────────────────────────────────────

    def _iniciar_procesamiento(self):
        proveedor = self.var_proveedor.get()
        keys = _leer_api_keys()
        if proveedor == "Groq":
            api_key = keys["groq"]
        elif proveedor == "Claude":
            api_key = keys["claude"]
        else:
            api_key = keys["gemini"]

        if not api_key:
            mensajes = {
                "Groq":   ("No se encontró la clave de Groq.\n\n"
                           "Añade en config.ini:\n\n[groq]\napi_key = gsk_tu_clave_aqui"),
                "Gemini": ("No se encontró la clave de Gemini.\n\n"
                           "Añade en config.ini:\n\n[gemini]\napi_key = AIzaSy_tu_clave_aqui\n\n"
                           "Clave gratuita en: aistudio.google.com/app/apikey"),
                "Claude": ("No se encontró la clave de Claude.\n\n"
                           "Añade en config.ini:\n\n[claude]\napi_key = sk-ant-tu_clave_aqui\n\n"
                           "Consigue tu clave en: console.anthropic.com"),
            }
            messagebox.showerror("API Key no encontrada",
                                 mensajes.get(proveedor, "API Key no encontrada."))
            return

        fuentes = [f.strip() for f in
                   self.txt_fuentes.get("1.0", "end").splitlines() if f.strip()]
        if not fuentes:
            messagebox.showwarning("Sin fuentes", "Agrega al menos un documento o URL.")
            return

        self.btn_procesar.config(state="disabled", bg="#9990d8")
        self.progreso.start(12)
        self._limpiar_resultado()
        self._set_estado("Procesando…")
        self._guardar_config()

        secciones = {k: v.get() for k, v in self.sec_vars.items()}
        modelo_sel = self.var_modelo.get()
        threading.Thread(
            target=self._procesar_hilo,
            args=(fuentes, api_key, proveedor, modelo_sel,
                  self.var_tipo.get(), self.var_idioma.get(), secciones),
            daemon=True).start()

    def _procesar_hilo(self, fuentes, api_key, proveedor, modelo_sel,
                       tipo, idioma, secciones):
        # Poner el modelo elegido primero en la lista de fallback
        lista = MODELOS_GROQ if proveedor == "Groq" else MODELOS_GEMINI
        lista_orig = list(lista)
        lista.clear()
        lista.append(modelo_sel)
        for m in lista_orig:
            if m != modelo_sel:
                lista.append(m)

        carpeta_sal = Path(self.var_carpeta.get().strip())
        carpeta_sal.mkdir(parents=True, exist_ok=True)
        total = len(fuentes)

        for i, fuente in enumerate(fuentes, 1):
            nombre = (Path(fuente).stem
                      if not fuente.startswith("http") else f"web_{i}")
            self._set_estado(f"[{i}/{total}]  Leyendo: {nombre}…")
            try:
                texto = obtener_texto(fuente)
                if not texto.strip():
                    raise ValueError("No se pudo extraer texto del documento.")
                self._set_estado(f"[{i}/{total}]  Generando {tipo.lower()}: {nombre}…")

                def log(msg, _i=i, _t=total):
                    self._set_estado(f"[{_i}/{_t}]  {msg}")

                resultado, modelo_usado = resumir(
                    texto, api_key, proveedor, tipo, idioma, secciones, log)

                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                tipo_slug = tipo.lower().replace(" ", "_")
                ruta_sal = carpeta_sal / f"{nombre}_{tipo_slug}_{ts}.txt"
                ruta_sal.write_text(resultado, encoding="utf-8")

                bloque = (f"{'═'*58}\n"
                          f"  {tipo.upper()}: {nombre}\n"
                          f"{'─'*58}\n"
                          f"{resultado}\n"
                          f"  🤖 Modelo: {modelo_usado}\n"
                          f"  ✔ Guardado: {ruta_sal}\n")
                self._agregar_resultado(bloque, "ok")

            except Exception as e:
                bloque = (f"{'═'*58}\n"
                          f"  ✘ ERROR en: {nombre}\n"
                          f"{'─'*58}\n"
                          f"  {e}\n")
                self._agregar_resultado(bloque, "err")

        # Restaurar lista original
        lista.clear()
        lista.extend(lista_orig)

        self._set_estado(f"✔ Listo. {total} documento(s) procesados → {carpeta_sal}")
        self.after(0, self._fin_procesamiento)

    def _fin_procesamiento(self):
        self.progreso.stop()
        self.btn_procesar.config(state="normal", bg=ACENTO)

    def _set_estado(self, msg: str):
        self.after(0, lambda: self.var_estado.set(msg))

    def _limpiar_resultado(self):
        def _f():
            self.txt_resultado.config(state="normal")
            self.txt_resultado.delete("1.0", "end")
            self.txt_resultado.config(state="disabled")
        self.after(0, _f)

    def _agregar_resultado(self, texto: str, tipo: str = "ok"):
        color = EXITO if tipo == "ok" else ERROR
        def _f():
            self.txt_resultado.config(state="normal")
            self.txt_resultado.tag_configure(tipo, foreground=color)
            self.txt_resultado.insert("end", texto + "\n", tipo)
            self.txt_resultado.see("end")
            self.txt_resultado.config(state="disabled")
        self.after(0, _f)


# ── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = ResumidorApp()
    app.mainloop()
