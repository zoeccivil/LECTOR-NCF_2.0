"""
Analizar patrones de errores del OCR
Uso: python scripts/analyze_errors.py
"""
import csv
from pathlib import Path
from collections import Counter
import json


def analyze_errors():
    """Analizar errores comunes del último test"""
    
    # Buscar el CSV más reciente
    results_dir = Path("test_data/resultados")
    if not results_dir.exists():
        print("❌ No existe el directorio de resultados")
        return
    
    csv_files = sorted(results_dir.glob("test_results_*.csv"))
    
    if not csv_files:
        print("❌ No hay resultados de pruebas")
        print("\nEjecuta primero: python scripts/test_ocr_batch.py")
        return
    
    latest_csv = csv_files[-1]
    print("=" * 70)
    print(f"📊 Analizando: {latest_csv.name}")
    print("=" * 70)
    
    # Leer resultados
    with open(latest_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        results = list(reader)
    
    if not results:
        print("❌ No hay datos en el archivo")
        return
    
    total = len(results)
    
    # Análisis de campos faltantes
    campos_faltantes = {
        "NCF": 0,
        "RNC": 0,
        "Empresa": 0,
        "Total": 0,
        "Subtotal": 0,
        "ITBIS": 0
    }
    
    for result in results:
        if not result.get("ncf") or result["ncf"] == "None":
            campos_faltantes["NCF"] += 1
        if not result.get("rnc") or result["rnc"] == "None":
            campos_faltantes["RNC"] += 1
        if not result.get("empresa") or result["empresa"] == "None":
            campos_faltantes["Empresa"] += 1
        if not result.get("total") or result["total"] == "None":
            campos_faltantes["Total"] += 1
        if not result.get("subtotal") or result["subtotal"] == "None":
            campos_faltantes["Subtotal"] += 1
        if not result.get("itbis") or result["itbis"] == "None":
            campos_faltantes["ITBIS"] += 1
    
    print("\n" + "=" * 70)
    print("❌ CAMPOS NO DETECTADOS")
    print("=" * 70)
    print(f"{'Campo':<15} {'Faltantes':<12} {'Accuracy'}")
    print("─" * 70)
    for campo, count in campos_faltantes.items():
        success = total - count
        accuracy = (success / total * 100) if total > 0 else 0
        print(f"{campo:<15} {count:>3}/{total:<7} {accuracy:>6.1f}%")
    
    # Análisis de confianza OCR
    confidences = []
    for r in results:
        if r.get("confidence") and r["confidence"] != "None":
            try:
                confidences.append(float(r["confidence"]))
            except:
                pass
    
    if confidences:
        print("\n" + "=" * 70)
        print("📈 CONFIANZA OCR")
        print("=" * 70)
        print(f"Promedio:  {sum(confidences)/len(confidences):.2%}")
        print(f"Mínima:    {min(confidences):.2%}")
        print(f"Máxima:    {max(confidences):.2%}")
    
    # Tipos de errores más comunes
    error_types = []
    for result in results:
        if result.get("detalles_errores") and result["detalles_errores"].strip():
            errors = result["detalles_errores"].split("; ")
            error_types.extend(errors)
    
    if error_types:
        print("\n" + "=" * 70)
        print("🔍 ERRORES MÁS COMUNES")
        print("=" * 70)
        error_counter = Counter(error_types)
        for i, (error, count) in enumerate(error_counter.most_common(10), 1):
            print(f"{i:2}. [{count:2}x] {error}")
    
    # Análisis por tipo de NCF
    tipos_ncf = Counter()
    for result in results:
        tipo = result.get("tipo_ncf")
        if tipo and tipo != "None":
            tipos_ncf[tipo] += 1
    
    if tipos_ncf:
        print("\n" + "=" * 70)
        print("📋 TIPOS DE NCF DETECTADOS")
        print("=" * 70)
        for tipo, count in tipos_ncf.most_common():
            print(f"{tipo}: {count} factura(s)")
    
    print("\n" + "=" * 70)
    
    # Recomendaciones
    print("\n💡 RECOMENDACIONES:")
    print("─" * 70)
    
    if campos_faltantes["NCF"] > total * 0.2:
        print("⚠️ >20% de NCFs no detectados - Mejorar regex de NCF en ncf_parser.py")
    
    if campos_faltantes["Total"] > total * 0.2:
        print("⚠️ >20% de Totales no detectados - Mejorar extracción de montos")
    
    if campos_faltantes["RNC"] > total * 0.2:
        print("⚠️ >20% de RNCs no detectados - Mejorar regex de RNC")
    
    if not error_types:
        print("✅ ¡Excelente! No hay errores en las facturas con ground truth")
    
    print("=" * 70)


if __name__ == "__main__":
    analyze_errors()