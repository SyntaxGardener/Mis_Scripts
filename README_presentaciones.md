# 📊 docx_to_presentacion — Resúmenes Word → PDF vistoso

Convierte automáticamente tus resúmenes en Word en presentaciones PDF profesionales,
usando la IA de Claude para estructurar el contenido, generar iconos y escribir
las notas del presentador.

---

## 🚀 Instalación (una sola vez)

### 1. Requisitos previos
- **Python 3.9+** → https://www.python.org/downloads/
- **Node.js 18+** → https://nodejs.org/
- **LibreOffice** (para convertir a PDF) → https://www.libreoffice.org/download/
- **Cuenta en Anthropic** con API key → https://console.anthropic.com/

### 2. Instalar dependencias Python
```bash
pip install python-docx requests
```

### 3. Instalar dependencias Node.js
```bash
npm install -g pptxgenjs react react-dom react-icons sharp
```

### 4. Configurar la API key de Claude
**En Mac/Linux** — añade esta línea a tu `~/.zshrc` o `~/.bashrc`:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```
Luego ejecuta: `source ~/.zshrc`

**En Windows** — en PowerShell:
```powershell
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY","sk-ant-...","User")
```

---

## 📖 Uso

### Uso básico
```bash
python3 docx_to_presentacion.py mi_resumen.docx
```
Genera `mi_resumen.pdf` en la misma carpeta.

### Con opciones
```bash
python3 docx_to_presentacion.py mi_resumen.docx --color coral --slides 10
```

### Todas las opciones
```
--color     Paleta de colores (ver lista abajo). Default: oceano
--slides    Número aproximado de diapositivas. Default: 8
--salida    Nombre del archivo de salida (sin extensión)
```

---

## 🎨 Paletas de colores disponibles

| Nombre     | Aspecto                        |
|------------|--------------------------------|
| `oceano`   | Azul marino profundo (default) |
| `coral`    | Coral + dorado + azul marino   |
| `bosque`   | Verde bosque + musgo           |
| `terracota`| Terracota cálido               |
| `teal`     | Verde azulado moderno          |
| `nocturno` | Azul noche + hielo             |
| `cereza`   | Rojo cereza elegante           |
| `sage`     | Verde salvia suave             |

---

## 🃏 Tipos de diapositiva generadas

La IA elige automáticamente el tipo más adecuado para cada sección:

- **Portada** — título grande, subtítulo y asignatura
- **Contenido** — puntos numerados con icono temático
- **Dos columnas** — comparativa lado a lado con tarjetas
- **Estadística** — datos numéricos destacados a tamaño grande
- **Lista de iconos** — tarjetas con icono + título + descripción
- **Resumen/Cierre** — puntos clave de la sesión

Todas incluyen **notas del presentador** visibles en PowerPoint/LibreOffice Impress.

---

## 📁 Archivos del proyecto

```
docx_to_presentacion.py   ← Script principal (Python)
generar_pptx.js           ← Generador de diapositivas (Node.js)
README.md                 ← Esta guía
```

---

## 💡 Consejos

- **Estructura tu Word con títulos** (Título 1, Título 2) para que la IA detecte mejor las secciones.
- Para temas **cortos** (2-3 páginas), usa `--slides 6`.
- Para temas **largos** (10+ páginas), usa `--slides 12`.
- El **mismo resumen** puede generar presentaciones distintas — prueba varias veces si no te convence el resultado.
- Los archivos `.pptx` generados también se pueden editar en PowerPoint o LibreOffice Impress.

---

## ❓ Solución de problemas

**"Falta la variable de entorno ANTHROPIC_API_KEY"**
→ Revisa el paso 4 de instalación. Cierra y vuelve a abrir la terminal.

**"Error en Node.js"**
→ Asegúrate de tener instaladas las dependencias npm con el comando del paso 3.

**"La conversión a PDF falló"**
→ Instala LibreOffice. El script igual entregará el `.pptx` que puedes abrir y exportar a PDF manualmente.

**El PDF tiene caracteres extraños**
→ LibreOffice a veces no tiene las fuentes Georgia/Calibri. Instala el paquete de fuentes de Microsoft:
```bash
# En Ubuntu/Debian:
sudo apt install ttf-mscorefonts-installer
```
