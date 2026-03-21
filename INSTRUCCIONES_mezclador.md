# 🎙 Mezclador de Cuña Publicitaria

Herramienta para que los alumnos mezclen su locución con música de fondo.

---

## 📦 Instalación

### 1. Python
Necesitas Python 3.8 o superior.  
Descarga desde https://www.python.org/downloads/

### 2. Librerías Python
Abre una terminal (cmd / PowerShell / Terminal) y ejecuta:

```
pip install pydub pygame
```

### 3. FFmpeg (imprescindible para archivos MP3)

**Windows:**
1. Descarga desde https://ffmpeg.org/download.html → "Windows builds"
2. Descomprime y copia la carpeta (p. ej. `C:\ffmpeg`)
3. Añade `C:\ffmpeg\bin` a la variable de entorno PATH:
   - Busca "Variables de entorno" en el menú inicio
   - Edita la variable PATH del usuario
   - Añade la ruta a la carpeta `bin`

**macOS (con Homebrew):**
```
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```
sudo apt install ffmpeg
```

---

## ▶ Cómo usar el programa

1. Doble clic en `cuna_publicitaria.pyw` (o ejecútalo con `python cuna_publicitaria.pyw`)
2. Carga tu **locución** (el audio que grabaste)
3. Carga la **música de fondo**
4. Ajusta los parámetros:

| Parámetro | Descripción |
|-----------|-------------|
| Silencio al inicio | Segundos de música sola antes de que empieces a hablar |
| Silencio al final | Segundos de música sola después de que terminas |
| Vol. música en intro/outro | Qué tan alta suena la música cuando no hablas (%) |
| Vol. música durante locución | Qué tan baja suena la música mientras hablas (%) |
| Fundido entre secciones | Suavidad de la transición de volumen (ms) |
| Fade in | Duración del fundido de entrada (ms) |
| Fade out | Duración del fundido de salida (ms) |

5. Pulsa **▶ PREESCUCHAR** para escuchar el resultado
6. Si te gusta, pulsa **💾 EXPORTAR MEZCLA** y elige dónde guardar el archivo

---

## 🎵 Estructura de la cuña resultante

```
┌─────────────────┬───────────────────────┬─────────────────┐
│   INTRO         │     LOCUCIÓN          │   OUTRO         │
│ Música alta     │ Música baja + tu voz  │ Música alta     │
│ ← Fade in       │                       │ Fade out →      │
└─────────────────┴───────────────────────┴─────────────────┘
```

---

## 💡 Consejos para los alumnos

- Graba en un lugar silencioso, sin eco
- La locución debe estar a **buen volumen** antes de mezclar
- Música recomendada: sin letra, ritmo alegre y localidad/región
- Vol. durante locución: **15–25%** suele funcionar bien
- Vol. en intro/outro: **75–90%** da presencia sin saturar
- Fade in/out de **1.5–2 segundos** queda profesional
- Exporta en **MP3** para compartir fácilmente

---

## ❓ Problemas comunes

**"No module named pydub"**
→ Ejecuta: `pip install pydub`

**"FileNotFoundError: ffprobe"**
→ FFmpeg no está en el PATH. Revisa el paso 3 de instalación.

**El audio de preescucha no suena**
→ Ejecuta: `pip install pygame`

**La música se corta antes de tiempo**
→ La música se buclea automáticamente; asegúrate de que el archivo no esté dañado.
