"""
Test OCR en todas las facturas de prueba
Uso: python scripts/test_ocr_batch.py
"""
import sys
from pathlib import Path
import json
from datetime import datetime
import csv

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.test_ocr_single import test_single_invoice


def load_ground_truth():
    """Cargar datos correctos desde JSON"""
    gt_path = Path("test_data/ground_truth/facturas.json")
    if gt_path.exists():
        try:
            with open(gt_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error cargando ground truth: {e}")
    return {}


def compare_results(invoice, ground_truth):
    """Comparar resultados con ground truth"""
    if not invoice:
        return ["Error procesando factura"], False
    
    errors = []
    perfect = True
    
    # Comparar NCF
    gt_ncf = ground_truth.get("ncf", "").strip()
    inv_ncf = (invoice.ncf or "").strip()
    if gt_ncf and gt_ncf != inv_ncf:
        errors.append(f"NCF: esperado '{gt_ncf}', obtenido '{inv_ncf}'")
        perfect = False
    elif not inv_ncf and gt_ncf:
        errors.append(f"NCF: no encontrado (esperado '{gt_ncf}')")
        perfect = False
    
    # Comparar RNC
    gt_rnc = ground_truth.get("rnc", "").strip()
    inv_rnc = (invoice.rnc or "").strip()
    if gt_rnc and gt_rnc != inv_rnc:
        errors.append(f"RNC: esperado '{gt_rnc}', obtenido '{inv_rnc}'")
        perfect = False
    
    # Comparar Total
    gt_total = ground_truth.get("total")
    inv_total = invoice.montos.total if invoice.montos else None
    if gt_total and inv_total:
        diff = abs(gt_total - inv_total)
        if diff > 0.01:
            errors.append(f"Total: esperado {gt_total:,.2f}, obtenido {inv_total:,.2f}")
            perfect = False
    elif gt_total and not inv_total:
        errors.append(f"Total: no encontrado (esperado {gt_total:,.2f})")
        perfect = False
    
    return errors, perfect


def test_batch():
    """Probar todas las facturas"""
    
    facturas_dir = Path("test_data/facturas_originales")
    ground_truth = load_ground_truth()
    
    if not facturas_dir.exists():
        print(f"❌ Error: Directorio no encontrado: {facturas_dir}")
        return
    
    results = []
    
    print("=" * 70)
    print("🧪 PRUEBA EN BATCH - OCR TESTING")
    print("=" * 70)
    
    # Buscar imágenes
    facturas = sorted(facturas_dir.glob("*.jpg")) + sorted(facturas_dir.glob("*.png"))
    
    if not facturas:
        print(f"❌ No se encontraron facturas en {facturas_dir}")
        print("\nColoca las imágenes de facturas en:")
        print(f"  {facturas_dir.absolute()}")
        return
    
    print(f"📁 Facturas encontradas: {len(facturas)}\n")
    
    for i, factura_path in enumerate(facturas, 1):
        print(f"\n{'='*70}")
        print(f"[{i}/{len(facturas)}] {factura_path.name}")
        print(f"{'='*70}")
        
        try:
            invoice, ocr_text, confidence = test_single_invoice(str(factura_path), show_ocr_text=False)
            
            # Comparar con ground truth
            gt = ground_truth.get(factura_path.name, {})
            errors, perfect = compare_results(invoice, gt) if gt else ([], None)
            
            result = {
                "archivo": factura_path.name,
                "ncf": invoice.ncf if invoice else None,
                "tipo_ncf": invoice.tipo_ncf if invoice else None,
                "rnc": invoice.rnc if invoice else None,
                "empresa": invoice.empresa if invoice else None,
                "total": invoice.montos.total if invoice and invoice.montos else None,
                "subtotal": invoice.montos.subtotal if invoice and invoice.montos else None,
                "itbis": invoice.montos.itbis if invoice and invoice.montos else None,
                "confidence": confidence,
                "errores": len(errors),
                "detalles_errores": "; ".join(errors) if errors else "",
                "perfecto": "✅" if perfect else "⚠️" if errors and invoice else "❌"
            }
            
            results.append(result)
            
            if errors:
                print(f"\n⚠️ {len(errors)} error(es) detectado(s):")
                for error in errors:
                    print(f"   • {error}")
            elif perfect:
                print(f"\n✅ ¡Perfecto! Todos los campos correctos")
        
        except Exception as e:
            print(f"\n❌ Error procesando: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "archivo": factura_path.name,
                "ncf": None,
                "rnc": None,
                "total": None,
                "confidence": None,
                "errores": 1,
                "detalles_errores": str(e),
                "perfecto": "❌"
            })
    
    # Guardar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = Path(f"test_data/resultados/test_results_{timestamp}.csv")
    
    try:
        with open(results_file, 'w', newline='', encoding='utf-8') as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
        print(f"\n✅ Resultados guardados en: {results_file}")
    except Exception as e:
        print(f"\n❌ Error guardando resultados: {e}")
    
    # Resumen
    total = len(results)
    perfectos = sum(1 for r in results if r["perfecto"] == "��")
    con_errores = sum(1 for r in results if r["perfecto"] == "⚠️")
    fallidos = sum(1 for r in results if r["perfecto"] == "❌")
    
    # Accuracy por campo
    ncf_ok = sum(1 for r in results if r.get("ncf"))
    rnc_ok = sum(1 for r in results if r.get("rnc"))
    total_ok = sum(1 for r in results if r.get("total"))
    
    print("\n" + "=" * 70)
    print("📊 RESUMEN FINAL")
    print("=" * 70)
    print(f"Total facturas:        {total}")
    print(f"✅ Perfectas:          {perfectos:2} ({perfectos/total*100:.1f}%)")
    print(f"⚠️ Con errores:        {con_errores:2} ({con_errores/total*100:.1f}%)")
    print(f"❌ Fallidas:           {fallidos:2} ({fallidos/total*100:.1f}%)")
    print(f"\n{'─'*70}")
    print("ACCURACY POR CAMPO:")
    print(f"{'─'*70}")
    print(f"NCF extraído:          {ncf_ok:2}/{total} ({ncf_ok/total*100:.1f}%)")
    print(f"RNC extraído:          {rnc_ok:2}/{total} ({rnc_ok/total*100:.1f}%)")
    print(f"Total extraído:        {total_ok:2}/{total} ({total_ok/total*100:.1f}%)")
    print("=" * 70)
    
    return results


if __name__ == "__main__":
    test_batch()