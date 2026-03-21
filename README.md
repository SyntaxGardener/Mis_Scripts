# 🧰 Mis Scripts — Herramientas para el día a día en el aula

Colección de scripts Python para profesores. Juegos educativos, herramientas de gestión, utilidades de PC y más. Todo hecho a medida para el trabajo real en un centro escolar. Asturias (España)

> **Sistema operativo:** Windows · **Lenguaje:** Python 3.x · **Interfaz:** Tkinter (sin consola)

---

## 📋 Tabla de contenidos

- [🎮 Juegos para clase](#-juegos-para-clase)
- [👩‍🏫 Herramientas para el profesor](#-herramientas-para-el-profesor)
- [📄 Gestión de PDFs](#-gestión-de-pdfs)
- [🎬 Multimedia](#-multimedia)
- [🎓 Administración y certificados](#-administración-y-certificados)
- [💻 Utilidades del PC](#-utilidades-del-pc)
- [🛠️ Otras utilidades](#️-otras-utilidades)
- [⚙️ Instalación](#️-instalación)

---

## 🎮 Juegos para clase

| Script | Descripción |
|--------|-------------|
| `games.pyw` | Menú central con acceso a tres juegos en inglés y español: hangman, spelling bee y wordle |
| `Pasapalabra.pyw` | Juego tipo Pasapalabra con rosco interactivo. Hay que subir docx con tabla de 3 columnas: Letra - Pista - Respuesta |
| `Bingo.pyw` | Bingo con cartones generados automáticamente, para usar en inglés o español. Se puede seleccionar rango de números |


Los juegos incluyen listas de palabras en español e inglés en varios niveles:
`rae_1000.txt`, `rae_5000.txt`, `english1000.txt`, `english5000.txt`, `words_alpha.txt`

---

## 👩‍🏫 Herramientas para el profesor

| Script | Descripción |
|--------|-------------|
| `examenes.pyw` | Generador de exámenes extrayendo preguntas de apuntes |
| `resumenes.pyw` | Generador de resúmenes de texto |
| `presentaciones.pyw` | Herramienta para crear presentaciones |
| `excel_notas.pyw` | Generador de hoja Excel para registro de notas a partir de listados de Sauce |
| `horarios_por_ensenanza.pyw` | Generador de horarios por enseñanza a partir de horarios proporcionados por la Jefa de estudios de mi centro. |
| `Calculador_medias.pyw` | Calculadora de medias y calificaciones a partir de historiales académicos generados por Sauce|
| `word_a_excel.pyw` | Extrae tablas de Word y las pasa a un Excel |
| `generar_docs_multiples.pyw` | Generación de documentos en lote . Se necesita aportar plantilla docx y excel con datos del alumnado. 
`Picker.pyw` | Selector aleatorio (p.ej. para elegir alumnos) |
| `Cronometro.pyw` | Cronómetro para clase |
| `Traductor.pyw` | Traductor de textos orales y escritos. Varios idiomas |
| `Txt_Voz.pyw` | Conversor de texto a voz |

---

## 📄 Gestión de PDFs

| Script | Descripción |
|--------|-------------|
| `Suite_PDF.pyw` | Suite completa de herramientas PDF |
| `Separador_PDF.pyw` | Divide PDFs por páginas o rangos |
| `Imagen_a_pdf.pyw` | Convierte imágenes a PDF |
| `separador_de_apuntes.pyw` | Separa apuntes en documentos individuales |
| `separador_de_certificados.pyw` | Separa certificados generados por Sauce en PDF individual por alumno |
| `limpiador_metadatos.pyw` | Elimina metadatos de archivos PDF |
| `formateador.pyw` | Formateador de documentos (.txt > .docx o .pdf) |

---

## 🎬 Multimedia

| Script | Descripción |
|--------|-------------|
| `video_studio.pyw` | Editor de vídeo básico |
| `editor_audio.pyw` | Editor de audio |
| `extraer_audio.pyw` | Extrae el audio de un archivo de vídeo |
| `Descargar_Youtube.pyw` | Descarga vídeos de YouTube |
| `Comprimir_Imagenes.pyw` | Comprime imágenes en lote |
| `Descargar_Imagenes.pyw` | Descarga imágenes desde URLs |
| `mezclador.pyw` | Mezclador para hacer anuncio de radio |
---

## 🎓 Administración y certificados

| Script | Descripción |
|--------|-------------|
| `Generar_certificados.pyw` | Generador de certificados en PDF. Yo lo uso para generar certificados supletorios de título a partir de una plantilla y un excel con los datos del alumnado |
| `diplomas.pyw` | Generador de diplomas a partir de una plantilla (de Canva) y un excel con los datos |
| `Diligencia_Titulo.pyw` | Genera diligencias de título para Sauce |
| `Graficos_Gestion.pyw` | Genera gráficos para presentar la Cuenta de gestión del centro a partir de un excel, con una tabla con la evolución del saldo, otra con los ingresos desglosados y una tercera con los gastos |
| `calculadora_IVA.py` | Calculadora de base imponible  para tickets de compra en los que no se indica |

---

## 💻 Utilidades del PC

| Script | Descripción |
|--------|-------------|
| `limpiar_windows.pyw` | Limpieza de archivos temporales de Windows |
| `expulsar_USB.pyw` | Expulsa unidades USB de forma segura |
| `reparar_expulsion_usb.py` | Repara problemas con la expulsión de USB |
| `Cerrar_Procesos.bat` | Cierra procesos en masa (útil cuando un USB se resiste a ser expulsado por haber algún proceso abierto) |
| `Test_Nuevo_PC.py` | Comprueba dependencias en un PC nuevo |
| `analizar_imports.pyw` | Analiza qué librerías necesita cada script |
| `Sincronizador.pyw` | Sincronización de carpetas |
| `Organizador_Descargas.pyw` | Organiza automáticamente la carpeta de Descargas |
| `comparador_de_archivos.pyw` | Compara el contenido de dos archivos |

---

## 🛠️ Otras utilidades

| Script | Descripción |
|--------|-------------|
| `menu.pyw` | Menú principal con acceso a todos los scripts |
| `Generador_QR.pyw` | Generador de códigos QR |

---

## ⚙️ Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/SyntaxGardener/Mis_Scripts.git
cd Mis_Scripts
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

> 💡 Si es un PC nuevo, ejecuta primero `Test_Nuevo_PC.py` para comprobar qué falta, o usa `analizar_imports.pyw` para ver las dependencias de un script concreto.

### 3. Ejecutar un script

Haz doble clic en cualquier archivo `.pyw` para abrirlo directamente sin consola, o ejecuta desde terminal:

```bash
python menu.pyw
```

---

## 📁 Estructura del repositorio

```
Mis_Scripts/
├── menu.pyw                  ← Punto de entrada principal
├├── fonts/                   ← Fuentes usadas por los scripts
├── gs/                       ← Recursos Ghostscript para PDFs
├── requirements.txt          ← Dependencias Python
├── *.pyw                     ← Scripts con interfaz gráfica
└── *.py                      ← Scripts de consola / utilidades
```

---

## 🗒️ Notas

- Los archivos `.pyw` se ejecutan **sin ventana de consola** (ideal para usar en clase).
- Algunos scripts requieren **ffmpeg** instalado para las funciones de vídeo y audio.
- El script `Test_Nuevo_PC.py` es el primero que hay que ejecutar en una instalación nueva.

---

*Hecho con 🐍 Python y muchas horas de clase por delante.*
