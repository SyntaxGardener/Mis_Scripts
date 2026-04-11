import tkinter as tk
from tkinter import messagebox

def on_click(button_text):
    current = entry.get()
    
    if button_text == "=":
        try:
            # Limpiamos símbolos visuales para que eval() los entienda
            expr = current.replace('×', '*').replace('÷', '/').replace(',', '.')
            result = eval(expr)
            entry.delete(0, tk.END)
            # Mostramos resultado con coma decimal
            entry.insert(tk.END, str(result).replace('.', ','))
        except:
            messagebox.showerror("Error", "Operación inválida")
            entry.delete(0, tk.END)
    elif button_text == "C":
        entry.delete(0, tk.END)
    elif button_text == "CE":
        entry.delete(0, tk.END)
    elif button_text == "⌫":
        entry.delete(len(current)-1, tk.END)
    elif button_text == "%":
        try:
            val = float(current.replace(',', '.'))
            entry.delete(0, tk.END)
            entry.insert(tk.END, str(val / 100).replace('.', ','))
        except: pass
    else:
        entry.insert(tk.END, button_text)

# Configuración Base
root = tk.Tk()
root.title("Calculator")
root.resizable(False, False)
root.attributes("-topmost", True)
root.configure(bg="#f3f3f3")

# Posicionamiento (Centrado y a 5px del tope)
w, h = 350, 500
sw = root.winfo_screenwidth()
root.geometry(f"{w}x{h}+{(sw//2)-(w//2)}+5")

# Pantalla (Entry)
entry = tk.Entry(root, font=("Segoe UI", 32), borderwidth=0, highlightthickness=2, 
                 highlightbackground="#cccccc", justify="right", bg="#f9f9f9")
entry.pack(fill="x", padx=10, pady=(20, 10))

# Frame para botones
btns_frame = tk.Frame(root, bg="#f3f3f3")
btns_frame.pack(expand=True, fill="both", padx=5, pady=5)

# Definición de botones según tu imagen
buttons = [
    ('%', '#f1f1f1'), ('CE', '#f1f1f1'), ('C', '#f1f1f1'), ('⌫', '#f1f1f1'),
    ('7', '#ffffff'), ('8', '#ffffff'), ('9', '#ffffff'), ('×', '#f1f1f1'),
    ('4', '#ffffff'), ('5', '#ffffff'), ('6', '#ffffff'), ('-', '#f1f1f1'),
    ('1', '#ffffff'), ('2', '#ffffff'), ('3', '#ffffff'), ('+', '#f1f1f1'),
    ('÷', '#f1f1f1'), ('0', '#ffffff'), (',', '#ffffff'), ('=', '#0067c0')
]

row, col = 0, 0
for (text, color) in buttons:
    fg_color = "white" if text == "=" else "black"
    btn = tk.Button(btns_frame, text=text, font=("Segoe UI", 14), 
                    bg=color, fg=fg_color, relief="flat", borderwidth=1,
                    command=lambda t=text: on_click(t))
    
    btn.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
    
    # Efecto visual al pasar el ratón
    btn.bind("<Enter>", lambda e, b=btn: b.configure(bg="#e1e1e1") if b['text'] != "=" else None)
    btn.bind("<Leave>", lambda e, b=btn, c=color: b.configure(bg=c))

    col += 1
    if col > 3:
        col = 0
        row += 1

# Ajuste de proporciones de las celdas
for i in range(4): btns_frame.columnconfigure(i, weight=1)
for i in range(5): btns_frame.rowconfigure(i, weight=1)

root.mainloop()