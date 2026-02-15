"""
Batch testing con métricas avanzadas
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ocr_processor import ocr_processor
from app.ncf_parser import ncf_parser
from app.utils.image_processor import optimize_image_for_ocr
import pandas as pd
from datetime import datetime


def run_batch_test(test_dir: str = "test_data/facturas_originales"):
    """Ejecutar test en batch con todas las facturas"""
    
    test_path = Path(test_dir)
    images = list(test_path.glob("*.jp*g")) + list(test_path.glob("*.png"))
    
    results = []
    
    print("=" * 70)
    print(f"🧪 BATCH TEST - {len(images)} facturas")
    print("=" * 70)
    
    for i, img_path in enumerate(images, 1):
        print(f"\n[{i}/{len(images)}] {img_path.name}...", end=" ")
        
        try:
            # OCR
            with open(img_path, 'rb') as f:
                image_bytes = f.read()
            
            optimized = optimize_image_for_ocr(image_bytes)
            ocr_text, confidence = ocr_processor.process_invoice_image(optimized)
            
            # Parse
            invoice = ncf_parser.parse_invoice(ocr_text, confidence, img_path.name)
            
            # Resultado
            result = {
                'imagen': img_path.name,
                'ncf': invoice.ncf,
                'tipo_ncf': invoice.tipo_ncf.value if invoice.tipo_ncf else None,
                'rnc': invoice.rnc,
                'rnc_formatted': invoice.rnc_formatted,
                'cedula': invoice.cedula,
                'empresa': invoice.empresa,
                'fecha': invoice.fecha,
                'subtotal': invoice.montos.subtotal,
                'itbis': invoice.montos.itbis,
                'total': invoice.montos.total,
                'confidence_score': invoice.confidence_score,
                'is_valid': invoice.is_valid,
                'audit_flags': ','.join(invoice.audit_flags),
                'ocr_confidence': confidence
            }
            
            results.append(result)
            
            if invoice.is_valid:
                print("✅ VÁLIDA")
            else:
                print("⚠️ CON ERRORES")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append({
                'imagen': img_path.name,
                'error': str(e)
            })
    
    # Generar reporte
    df = pd.DataFrame(results)
    
    print("\n" + "=" * 70)
    print("📊 RESUMEN:")
    print("=" * 70)
    
    total = len(df)
    validas = df['is_valid'].sum() if 'is_valid' in df.columns else 0
    
    print(f"Total facturas:     {total}")
    print(f"✅ Válidas:         {validas} ({validas/total*100:.1f}%)")
    print(f"❌ Con errores:     {total - validas} ({(total-validas)/total*100:.1f}%)")
    
    print("\n" + "─" * 70)
    print("ACCURACY POR CAMPO:")
    print("─" * 70)
    
    if 'ncf' in df.columns:
        ncf_ok = df['ncf'].notna().sum()
        print(f"NCF extraído:       {ncf_ok}/{total} ({ncf_ok/total*100:.1f}%)")
    
    if 'rnc' in df.columns:
        rnc_ok = df['rnc'].notna().sum()
        print(f"RNC extraído:       {rnc_ok}/{total} ({rnc_ok/total*100:.1f}%)")
    
    if 'total' in df.columns:
        total_ok = df['total'].notna().sum()
        print(f"Total extraído:     {total_ok}/{total} ({total_ok/total*100:.1f}%)")
    
    if 'confidence_score' in df.columns:
        avg_conf = df['confidence_score'].mean()
        print(f"\nConfianza promedio: {avg_conf:.0%}")
    
    print("=" * 70)
    
    # Guardar CSV
    output_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False)
    print(f"\n📄 Resultados guardados en: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_batch_test(sys.argv[1])
    else:
        run_batch_test()
