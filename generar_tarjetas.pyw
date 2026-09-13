import sys
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import docx
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Paleta de colores para los marcos redondeados
PALETA_COLORES = [
    colors.HexColor('#2E7D32'), # Verde
    colors.HexColor('#1565C0'), # Azul
    colors.HexColor('#C2185B'), # Magenta
    colors.HexColor('#E65100'), # Naranja
    colors.HexColor('#6A1B9A'), # Violeta
    colors.HexColor('#00838F'), # Turquesa
    colors.HexColor('#D84315'), # Coral
    colors.HexColor('#455A64'), # Gris Azulado
    colors.HexColor('#8E24AA'), # Púrpura
    colors.HexColor('#00695C')  # Verde Azulado
]

def limpiar_texto(texto):
    """Limpia etiquetas de 'Tarjeta X:' y comillas estropeadas o repetidas."""
    if not texto:
        return ""
    
    # Quitar etiquetas "Tarjeta X:"
    texto = re.sub(r'^\s*Tarjeta\s*\d+\s*:\s*', '', texto, flags=re.IGNORECASE)
    
    # Limpiar comillas o caracteres sobrantes
    texto = texto.strip(' <>«»"')
    texto = re.sub(r'^[<«"]+', '', texto)
    texto = re.sub(r'[>»"]+$', '', texto)
    
    return texto.strip()

def docx_a_textos(ruta_docx):
    doc = docx.Document(ruta_docx)
    textos = []
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                txt = limpiar_texto(cell.text)
                if txt:
                    textos.append(txt)
    return textos

class CanvasTarjetasIndependientes(canvas.Canvas):
    """Canvas que dibuja los marcos redondeados sin tapar el texto (fill=0)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tarjetas_a_dibujar = []

    def registrar_tarjeta(self, x, y, ancho, alto, color):
        self.tarjetas_a_dibujar.append((x, y, ancho, alto, color))

    def showPage(self):
        self.saveState()
        for (x, y, ancho, alto, color) in self.tarjetas_a_dibujar:
            self.setStrokeColor(color)
            self.setLineWidth(3.0)
            self.roundRect(x, y, ancho, alto, radius=14, stroke=1, fill=0)
        self.restoreState()
        self.tarjetas_a_dibujar = []
        super().showPage()

def generar_pdf(textos, ruta_pdf):
    # Dimensiones A4 en puntos (595.27 x 841.89)
    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=A4,
        rightMargin=25,
        leftMargin=25,
        topMargin=25,
        bottomMargin=25
    )
    
    styles = getSampleStyleSheet()
    estilo_texto = ParagraphStyle(
        'TarjetaTexto',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        alignment=1, # Centrado horizontal
        textColor=colors.HexColor('#111111')
    )

    COLUMNAS = 2
    FILAS = 4
    TARJETAS_POR_PAGINA = COLUMNAS * FILAS
    
    ANCHO_PAGINA = 595.27
    ALTO_PAGINA = 841.89
    
    ANCHO_TARJETA = 240
    ALTO_TARJETA = 170
    
    GAP_X = 20  # Espacio libre entre tarjetas horizontales
    GAP_Y = 18  # Espacio libre entre tarjetas verticales

    # Centrado exacto de la cuadrícula en el folio A4
    ANCHO_TOTAL_GRID = (COLUMNAS * ANCHO_TARJETA) + GAP_X
    ALTO_TOTAL_GRID = (FILAS * ALTO_TARJETA) + ((FILAS - 1) * GAP_Y)
    
    MARGEN_IZQ = (ANCHO_PAGINA - ANCHO_TOTAL_GRID) / 2.0
    MARGEN_SUP = (ALTO_PAGINA - ALTO_TOTAL_GRID) / 2.0

    def maker(filename, **kw):
        return CanvasTarjetasIndependientes(filename, **kw)

    story = []

    for i in range(0, len(textos), TARJETAS_POR_PAGINA):
        bloque = textos[i:i + TARJETAS_POR_PAGINA]
        
        celdas_bloque = []
        for j, txt in enumerate(bloque):
            txt_html = txt.replace('\n', '<br/>')
            p = Paragraph(f"«{txt_html}»", estilo_texto)
            celdas_bloque.append(p)
            
        while len(celdas_bloque) < TARJETAS_POR_PAGINA:
            celdas_bloque.append("")

        filas_tabla = []
        for r in range(FILAS):
            c1 = celdas_bloque[r * 2]
            c2 = celdas_bloque[r * 2 + 1]
            filas_tabla.append([c1, c2])

        # Se ajusta la tabla exactamente a las dimensiones de las tarjetas + huecos
        t = Table(
            filas_tabla, 
            colWidths=[ANCHO_TARJETA + GAP_X, ANCHO_TARJETA], 
            rowHeights=[ALTO_TARJETA + (GAP_Y if r < FILAS - 1 else 0) for r in range(FILAS)]
        )
        
        t.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            # Alineación y padding exacto para centrar el párrafo en la tarjeta
            ('LEFTPADDING', (0,0), (0,-1), 15),
            ('RIGHTPADDING', (0,0), (0,-1), 15 + GAP_X),
            ('LEFTPADDING', (1,0), (1,-1), 15),
            ('RIGHTPADDING', (1,0), (1,-1), 15),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-2), 10 + GAP_Y),
            ('BOTTOMPADDING', (0,-1), (-1,-1), 10),
        ]))
        
        story.append(t)
        if i + TARJETAS_POR_PAGINA < len(textos):
            story.append(PageBreak())

    def dibujar_marcos_independientes(canvas_obj, doc_obj):
        page_num = doc_obj.page - 1
        start_idx = page_num * TARJETAS_POR_PAGINA
        
        for idx_rel in range(TARJETAS_POR_PAGINA):
            idx_global = start_idx + idx_rel
            if idx_global >= len(textos):
                break
                
            row = idx_rel // COLUMNAS
            col = idx_rel % COLUMNAS
            
            x = MARGEN_IZQ + col * (ANCHO_TARJETA + GAP_X)
            y = ALTO_PAGINA - MARGEN_SUP - (row + 1) * ALTO_TARJETA - row * GAP_Y
            
            color = PALETA_COLORES[idx_global % len(PALETA_COLORES)]
            canvas_obj.registrar_tarjeta(x, y, ANCHO_TARJETA, ALTO_TARJETA, color)

    doc.build(story, canvasmaker=maker, onFirstPage=dibujar_marcos_independientes, onLaterPages=dibujar_marcos_independientes)

def ejecutar_gui():
    root = tk.Tk()
    root.withdraw()

    messagebox.showinfo("Conversor a Tarjetas", "Selecciona tu documento Word (.docx)")
    
    ruta_docx = filedialog.askopenfilename(
        title="Seleccionar Word",
        filetypes=[("Archivos Word", "*.docx")]
    )
    
    if not ruta_docx:
        return

    textos = docx_a_textos(ruta_docx)
    
    if not textos:
        messagebox.showwarning("Atención", "No se encontraron textos en el archivo.")
        return
        
    ruta_pdf = filedialog.asksaveasfilename(
        title="Guardar PDF de Tarjetas",
        defaultextension=".pdf",
        filetypes=[("Archivo PDF", "*.pdf")]
    )
    
    if not ruta_pdf:
        return

    try:
        generar_pdf(textos, ruta_pdf)
        messagebox.showinfo("¡Éxito!", f"Se han generado {len(textos)} tarjetas perfectamente centradas en:\n{ruta_pdf}")
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al crear el PDF:\n{str(e)}")

if __name__ == "__main__":
    ejecutar_gui()