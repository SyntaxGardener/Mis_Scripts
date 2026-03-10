import os

def calcular():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("========================================")
    print("   ASISTENTE DE DESGLOSE DE FACTURAS    ")
    print("========================================\n")
    
    try:
        entrada_total = input("1. Introduce el TOTAL (con IVA): ").replace(',', '.')
        if not entrada_total: return
        total = float(entrada_total)
        
        entrada_iva = input("2. % IVA (Presiona Enter para 21%): ")
        iva_porcentaje = float(entrada_iva.replace(',', '.')) if entrada_iva else 21.0
        
        # Cálculo matemático
        # Base = Total / (1 + (IVA/100))
        base_imponible = total / (1 + (iva_porcentaje / 100))
        cuota_iva = total - base_imponible
        
        print("\n" + "-"*40)
        print(f" BASE IMPONIBLE:  {base_imponible:>10.2f} €")
        print(f" CUOTA IVA ({iva_porcentaje}%): {cuota_iva:>10.2f} €")
        print(f" TOTAL FACTURA:   {total:>10.2f} €")
        print("-"*40)
        
    except ValueError:
        print("\n¡Error! Introduce solo números (usa punto o coma para decimales).")

if __name__ == "__main__":
    while True:
        calcular()
        continuar = input("\n¿Calcular otra factura? (S/n): ").lower()
        if continuar == 'n':
            break