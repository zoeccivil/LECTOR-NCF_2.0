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
    """
    Ejecutar test en batch con todas las facturas
    
    Args:
        test_dir: Directorio con imágenes de facturas
        
    Output:
        - CSV file saved to current working directory: test_results_YYYYMMDD_HHMMSS.csv
    """
    
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
            
            # Resultado - Compatible con modelo Invoice actual
            result = {
                'imagen': img_path.name,
                'ncf': invoice.ncf,
                'tipo_ncf': invoice.tipo_ncf if invoice.tipo_ncf else None,  # ✅ Sin .value
                'rnc': invoice.rnc,
                'empresa': invoice.razon_social,  # ✅ Nombre correcto del atributo
                'fecha': invoice.fecha_emision,   # ✅ Nombre correcto del atributo
                'subtotal': invoice.montos.subtotal,
                'itbis': invoice.montos.itbis,
                'total': invoice.montos.total,
                'ocr_confidence': confidence
            }
            
            results.append(result)
            
            # Validación simple basada en campos obligatorios
            if invoice.ncf and invoice.rnc and invoice.montos.total:
                print("✅ VÁLIDA")
            else:
                print("⚠️ INCOMPLETA")
                
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
    
    # Validación: facturas con NCF, RNC y Total
    if 'ncf' in df.columns and 'rnc' in df.columns and 'total' in df.columns:
        validas = ((df['ncf'].notna()) & (df['rnc'].notna()) & (df['total'].notna())).sum()
    else:
        validas = 0
    
    print(f"Total facturas:     {total}")
    print(f"✅ Válidas:         {validas} ({validas/total*100:.1f}%)")
    print(f"❌ Incompletas:     {total - validas} ({(total-validas)/total*100:.1f}%)")
    
    print("\n" + "─" * 70)
    print("ACCURACY POR CAMPO:")
    print("─" * 70)
    
    if 'ncf' in df.columns:
        ncf_ok = df['ncf'].notna().sum()
        print(f"NCF extraído:       {ncf_ok}/{total} ({ncf_ok/total*100:.1f}%)")
    
    if 'rnc' in df.columns:
        rnc_ok = df['rnc'].notna().sum()
        print(f"RNC extraído:       {rnc_ok}/{total} ({rnc_ok/total*100:.1f}%)")
    
    if 'fecha' in df.columns:
        fecha_ok = df['fecha'].notna().sum()
        print(f"Fecha extraída:     {fecha_ok}/{total} ({fecha_ok/total*100:.1f}%)")
    
    if 'subtotal' in df.columns:
        subtotal_ok = df['subtotal'].notna().sum()
        print(f"Subtotal extraído:  {subtotal_ok}/{total} ({subtotal_ok/total*100:.1f}%)")
    
    if 'itbis' in df.columns:
        itbis_ok = df['itbis'].notna().sum()
        print(f"ITBIS extraído:     {itbis_ok}/{total} ({itbis_ok/total*100:.1f}%)")
    
    if 'total' in df.columns:
        total_ok = df['total'].notna().sum()
        print(f"Total extraído:     {total_ok}/{total} ({total_ok/total*100:.1f}%)")
    
    if 'ocr_confidence' in df.columns:
        avg_conf = df['ocr_confidence'].mean()
        print(f"\nConfianza OCR promedio: {avg_conf:.2%}")
    
    print("=" * 70)
    
    # Guardar CSV
    output_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False)
    print(f"\n📄 Resultados guardados en: {output_file}")
    
    return df


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_batch_test(sys.argv[1])
    else:
        run_batch_test()