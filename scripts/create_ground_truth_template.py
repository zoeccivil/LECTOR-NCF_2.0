"""
Crear ground truth de forma interactiva
Uso: python scripts/create_ground_truth_template.py
"""
import json
from pathlib import Path
from datetime import datetime


def create_ground_truth_interactive():
    """Crear ground truth interactivamente"""
    
    facturas_dir = Path("test_data/facturas_originales")
    gt_file = Path("test_data/ground_truth/facturas.json")
    
    # Cargar ground truth existente
    if gt_file.exists():
        with open(gt_file, 'r', encoding='utf-8') as f:
            ground_truth = json.load(f)
        print(f"✅ Ground truth existente cargado: {len(ground_truth)} facturas")
    else:
        ground_truth = {}
        print("📝 Creando nuevo ground truth")
    
    # Buscar facturas sin ground truth
    facturas = sorted(facturas_dir.glob("*.jpg")) + sorted(facturas_dir.glob("*.png"))
    facturas_sin_gt = [f for f in facturas if f.name not in ground_truth]
    
    if not facturas_sin_gt:
        print("\n✅ Todas las facturas ya tienen ground truth")
        print(f"Total: {len(ground_truth)} facturas")
        return
    
    print(f"\n📋 Facturas sin ground truth: {len(facturas_sin_gt)}")
    print("="*70)
    
    for i, factura in enumerate(facturas_sin_gt, 1):
        print(f"\n[{i}/{len(facturas_sin_gt)}] {factura.name}")
        print("─"*70)
        print("Ingresa los datos CORRECTOS de esta factura:")
        print("(Presiona Enter para omitir un campo)")
        print()
        
        # NCF
        ncf = input("NCF (ej: B0100015202): ").strip()
        
        # Tipo NCF
        tipo_ncf = ""
        if ncf:
            tipo_ncf = ncf[:3] if len(ncf) >= 3 else ""
        tipo_ncf_input = input(f"Tipo NCF [{tipo_ncf}]: ").strip()
        if tipo_ncf_input:
            tipo_ncf = tipo_ncf_input
        
        # RNC
        rnc = input("RNC (ej: 101019921): ").strip()
        
        # Empresa
        empresa = input("Empresa: ").strip()
        
        # Fecha
        fecha = input("Fecha (YYYY-MM-DD): ").strip()
        
        # Subtotal
        subtotal_str = input("Subtotal (ej: 1234.56): ").strip()
        subtotal = float(subtotal_str) if subtotal_str else None
        
        # ITBIS
        itbis_str = input("ITBIS (ej: 222.22): ").strip()
        itbis = float(itbis_str) if itbis_str else None
        
        # Total
        total_str = input("Total (ej: 1456.78): ").strip()
        total = float(total_str) if total_str else None
        
        # Notas
        notas = input("Notas (opcional): ").strip()
        
        # Guardar
        ground_truth[factura.name] = {
            "ncf": ncf or None,
            "tipo_ncf": tipo_ncf or None,
            "rnc": rnc or None,
            "empresa": empresa or None,
            "fecha": fecha or None,
            "subtotal": subtotal,
            "itbis": itbis,
            "total": total,
            "moneda": "RD$",
            "notas": notas or ""
        }
        
        print(f"\n✅ Guardado: {factura.name}")
        
        # Preguntar si continuar
        if i < len(facturas_sin_gt):
            continuar = input("\n¿Continuar con la siguiente? (s/n): ").strip().lower()
            if continuar != 's':
                break
    
    # Guardar archivo
    gt_file.parent.mkdir(parents=True, exist_ok=True)
    with open(gt_file, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*70)
    print(f"✅ Ground truth guardado: {gt_file}")
    print(f"Total facturas: {len(ground_truth)}")
    print("="*70)


def show_ground_truth():
    """Mostrar ground truth actual"""
    gt_file = Path("test_data/ground_truth/facturas.json")
    
    if not gt_file.exists():
        print("❌ No existe ground truth")
        return
    
    with open(gt_file, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
    
    print("="*70)
    print(f"GROUND TRUTH ACTUAL ({len(ground_truth)} facturas)")
    print("="*70)
    
    for i, (filename, data) in enumerate(ground_truth.items(), 1):
        print(f"\n{i}. {filename}")
        print(f"   NCF:      {data.get('ncf')}")
        print(f"   RNC:      {data.get('rnc')}")
        print(f"   Empresa:  {data.get('empresa')}")
        print(f"   Total:    RD${data.get('total'):,.2f}" if data.get('total') else "   Total:    N/A")
        if data.get('notas'):
            print(f"   Notas:    {data.get('notas')}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_ground_truth()
    else:
        print("="*70)
        print("📋 CREAR GROUND TRUTH INTERACTIVO")
        print("="*70)
        print("\nEste script te ayudará a crear el ground truth")
        print("para cada factura en test_data/facturas_originales/")
        print("\nMira cada factura e ingresa los datos CORRECTOS")
        print("que deberían extraerse del OCR.")
        print("="*70)
        
        input("\nPresiona Enter para comenzar...")
        create_ground_truth_interactive()