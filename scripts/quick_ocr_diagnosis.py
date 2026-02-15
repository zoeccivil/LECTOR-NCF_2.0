"""
Test OCR en una sola factura con el parser mejorado
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ocr_processor import ocr_processor
from app.ncf_parser import ncf_parser
from app.utils.image_processor import optimize_image_for_ocr


def test_single_invoice(image_path: str, show_ocr_text: bool = False):
    """Probar OCR en una sola factura con el parser mejorado"""
    
    print("=" * 70)
    print(f"📸 Probando: {image_path}")
    print("=" * 70)
    
    # Leer imagen
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    print(f"📦 Tamaño original: {len(image_bytes)} bytes")
    
    # Optimizar
    optimized = optimize_image_for_ocr(image_bytes)
    print(f"📦 Tamaño optimizado: {len(optimized)} bytes")
    
    # OCR
    print("\n🔍 Ejecutando OCR...")
    ocr_text, confidence = ocr_processor.process_invoice_image(optimized)
    
    print(f"✅ Confianza OCR: {confidence:.2%}")
    print(f"📝 Caracteres extraídos: {len(ocr_text)}")
    
    if show_ocr_text:
        print("\n" + "=" * 70)
        print("TEXTO EXTRAÍDO:")
        print("=" * 70)
        print(ocr_text)
        print("=" * 70)
    
    # Parsear con el parser mejorado (python-stdnum)
    print("\n🧮 Parseando con patrones mejorados...")
    invoice = ncf_parser.parse_invoice(ocr_text, confidence, Path(image_path).name)
    
    # Mostrar resultados
    print("\n" + "=" * 70)
    print("📊 RESULTADOS:")
    print("=" * 70)
    print(f"NCF:               {invoice.ncf or '❌ NO ENCONTRADO'}")
    print(f"Tipo NCF:          {invoice.tipo_ncf.value if invoice.tipo_ncf else '❌'}")
    print(f"RNC:               {invoice.rnc or '❌ NO ENCONTRADO'}")
    print(f"RNC (formateado):  {invoice.rnc_formatted or '❌'}")
    print(f"Cédula:            {invoice.cedula or '-'}")
    print(f"Empresa:           {invoice.empresa or '❌ NO ENCONTRADO'}")
    print(f"Fecha:             {invoice.fecha or '❌ NO ENCONTRADO'}")
    print(f"Subtotal:          RD${invoice.montos.subtotal:,.2f}" if invoice.montos.subtotal else "Subtotal:          ❌")
    print(f"ITBIS:             RD${invoice.montos.itbis:,.2f}" if invoice.montos.itbis else "ITBIS:             ❌")
    print(f"Total:             RD${invoice.montos.total:,.2f}" if invoice.montos.total else "Total:             ❌")
    
    print(f"\n🎯 CONFIANZA TOTAL:   {invoice.confidence_score:.0%}" if invoice.confidence_score else "\n🎯 CONFIANZA TOTAL:   N/A")
    print(f"✅ VÁLIDA:            {'SÍ' if invoice.is_valid else 'NO'}")
    
    if invoice.audit_flags:
        print(f"\n⚠️ ALERTAS: {', '.join(invoice.audit_flags)}")
    
    print("=" * 70)
    
    return invoice, ocr_text, confidence


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/quick_ocr_diagnosis.py <ruta_imagen>")
        print("Ejemplo: python scripts/quick_ocr_diagnosis.py test_data/facturas_originales/factura_001.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    show_text = "--show-text" in sys.argv
    
    test_single_invoice(image_path, show_text)