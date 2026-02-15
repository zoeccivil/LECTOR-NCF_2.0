"""
Test OCR en una sola factura
Uso: python scripts/test_ocr_single.py test_data/facturas_originales/factura_001.jpg
"""
import sys
from pathlib import Path
import json

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ocr_processor import ocr_processor
from app.ncf_parser import ncf_parser
from app.utils.image_processor import optimize_image_for_ocr


def test_single_invoice(image_path: str, show_ocr_text: bool = False):
    """Probar OCR en una sola factura"""
    
    print("=" * 70)
    print(f"📸 Probando: {Path(image_path).name}")
    print("=" * 70)
    
    # Leer imagen
    try:
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
    except FileNotFoundError:
        print(f"❌ Error: Archivo no encontrado: {image_path}")
        return None, None, None
    
    print(f"📦 Tamaño original: {len(image_bytes):,} bytes ({len(image_bytes)/1024:.1f} KB)")
    
    # Optimizar
    try:
        optimized = optimize_image_for_ocr(image_bytes)
        print(f"📦 Tamaño optimizado: {len(optimized):,} bytes ({len(optimized)/1024:.1f} KB)")
    except Exception as e:
        print(f"❌ Error optimizando imagen: {e}")
        return None, None, None
    
    # OCR
    print("\n🔍 Ejecutando OCR...")
    try:
        ocr_text, confidence = ocr_processor.process_invoice_image(optimized)
    except Exception as e:
        print(f"❌ Error en OCR: {e}")
        return None, None, None
    
    print(f"✅ Confianza: {confidence:.2%}")
    print(f"📝 Caracteres extraídos: {len(ocr_text)}")
    
    if show_ocr_text:
        print("\n" + "=" * 70)
        print("TEXTO EXTRAÍDO (RAW OCR):")
        print("=" * 70)
        print(ocr_text[:1000])  # Primeros 1000 caracteres
        if len(ocr_text) > 1000:
            print(f"\n... ({len(ocr_text) - 1000} caracteres más)")
        print("=" * 70)
    
    # Parsear
    print("\n🧮 Parseando datos...")
    try:
        invoice = ncf_parser.parse_invoice(ocr_text, confidence, Path(image_path).name)
    except Exception as e:
        print(f"❌ Error parseando: {e}")
        return None, ocr_text, confidence
    
    # Mostrar resultados
    print("\n" + "=" * 70)
    print("RESULTADOS EXTRAÍDOS:")
    print("=" * 70)
    print(f"NCF:      {invoice.ncf or '❌ NO ENCONTRADO'}")
    print(f"Tipo NCF: {invoice.tipo_ncf or '❌ NO ENCONTRADO'}")
    print(f"RNC:      {invoice.rnc or '❌ NO ENCONTRADO'}")
    print(f"Empresa:  {invoice.empresa or '❌ NO ENCONTRADO'}")
    print(f"Fecha:    {invoice.fecha or '❌ NO ENCONTRADO'}")
    print(f"Subtotal: RD${invoice.montos.subtotal:,.2f}" if invoice.montos.subtotal else "Subtotal: ❌ NO ENCONTRADO")
    print(f"ITBIS:    RD${invoice.montos.itbis:,.2f}" if invoice.montos.itbis else "ITBIS:    ❌ NO ENCONTRADO")
    print(f"Total:    RD${invoice.montos.total:,.2f}" if invoice.montos.total else "Total:    ❌ NO ENCONTRADO")
    
    # Warnings
    warnings = []
    if not invoice.ncf:
        warnings.append("NCF no encontrado")
    if not invoice.rnc:
        warnings.append("RNC no encontrado")
    if not invoice.montos.total:
        warnings.append("Total no encontrado")
    
    if warnings:
        print("\n⚠️ ADVERTENCIAS:")
        for warning in warnings:
            print(f"   • {warning}")
    
    print("=" * 70)
    
    return invoice, ocr_text, confidence


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Error: Debes especificar la ruta de la imagen")
        print("\nUso: python scripts/test_ocr_single.py <ruta_imagen>")
        print("\nEjemplo:")
        print("  python scripts/test_ocr_single.py test_data/facturas_originales/factura_001.jpg")
        print("\nOpciones:")
        print("  --show-text    Mostrar el texto OCR completo")
        sys.exit(1)
    
    image_path = sys.argv[1]
    show_text = "--show-text" in sys.argv
    
    test_single_invoice(image_path, show_text)