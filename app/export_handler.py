"""
Export handler for CSV and JSON formats
"""
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from app.models import Invoice
from app.utils.logger import app_logger
from app.utils.config import settings


class ExportHandler:
    """Handles exporting invoice data to CSV and JSON formats"""
    
    def __init__(self, export_dir: str = "data/exports"):
        """
        Initialize export handler
        
        Args:
            export_dir: Directory for exported files
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        app_logger.info(f"Export handler initialized. Export directory: {self.export_dir}")
    
    def export_to_csv(self, invoices: List[Invoice], filename: Optional[str] = None) -> str:
        """
        Export invoices to CSV format
        
        Args:
            invoices: List of Invoice objects
            filename: Optional custom filename (auto-generated if not provided)
            
        Returns:
            Path to exported CSV file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"facturas_{timestamp}.csv"
        
        filepath = self.export_dir / filename
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'fecha_procesamiento',
                    'ncf',
                    'rnc',
                    'razon_social',
                    'fecha_emision',
                    'subtotal',
                    'itbis',
                    'total',
                    'imagen_original'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=settings.csv_delimiter)
                writer.writeheader()
                
                for invoice in invoices:
                    writer.writerow({
                        'fecha_procesamiento': invoice.fecha_procesamiento.strftime('%Y-%m-%d %H:%M:%S'),
                        'ncf': invoice.ncf or '',
                        'rnc': invoice.rnc or '',
                        'razon_social': invoice.razon_social or '',
                        'fecha_emision': invoice.fecha_emision or '',
                        'subtotal': invoice.montos.subtotal or '',
                        'itbis': invoice.montos.itbis or '',
                        'total': invoice.montos.total or '',
                        'imagen_original': invoice.metadata.imagen_original or ''
                    })
            
            app_logger.info(f"Exported {len(invoices)} invoices to CSV: {filepath}")
            return str(filepath)
            
        except Exception as e:
            app_logger.error(f"Error exporting to CSV: {e}")
            raise
    
    def export_to_json(self, invoices: List[Invoice], filename: Optional[str] = None) -> str:
        """
        Export invoices to JSON format
        
        Args:
            invoices: List of Invoice objects
            filename: Optional custom filename (auto-generated if not provided)
            
        Returns:
            Path to exported JSON file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"facturas_{timestamp}.json"
        
        filepath = self.export_dir / filename
        
        try:
            # Convert invoices to dict format
            invoices_data = {
                "facturas": [
                    {
                        "id": invoice.id,
                        "fecha_procesamiento": invoice.fecha_procesamiento.isoformat(),
                        "ncf": invoice.ncf,
                        "rnc": invoice.rnc,
                        "razon_social": invoice.razon_social,
                        "fecha_emision": invoice.fecha_emision,
                        "montos": {
                            "subtotal": invoice.montos.subtotal,
                            "itbis": invoice.montos.itbis,
                            "total": invoice.montos.total,
                            "moneda": invoice.montos.moneda
                        },
                        "metadata": {
                            "imagen_original": invoice.metadata.imagen_original,
                            "confianza_ocr": invoice.metadata.confianza_ocr,
                            "origen": invoice.metadata.origen
                        }
                    }
                    for invoice in invoices
                ]
            }
            
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(invoices_data, jsonfile, indent=2, ensure_ascii=False)
            
            app_logger.info(f"Exported {len(invoices)} invoices to JSON: {filepath}")
            return str(filepath)
            
        except Exception as e:
            app_logger.error(f"Error exporting to JSON: {e}")
            raise
    
    def export(self, invoices: List[Invoice], format_type: Optional[str] = None) -> dict:
        """
        Export invoices based on configured format
        
        Args:
            invoices: List of Invoice objects
            format_type: Export format ('csv', 'json', or 'both'). Uses settings.export_format if not provided
            
        Returns:
            Dictionary with exported file paths
        """
        if not invoices:
            app_logger.warning("No invoices to export")
            return {}
        
        format_type = format_type or settings.export_format
        result = {}
        
        try:
            if format_type in ('csv', 'both'):
                csv_path = self.export_to_csv(invoices)
                result['csv'] = csv_path
            
            if format_type in ('json', 'both'):
                json_path = self.export_to_json(invoices)
                result['json'] = json_path
            
            app_logger.info(f"Export completed. Files: {result}")
            return result
            
        except Exception as e:
            app_logger.error(f"Error during export: {e}")
            raise
    
    def append_to_csv(self, invoice: Invoice, filename: str = "facturas_historico.csv") -> str:
        """
        Append single invoice to historical CSV file
        
        Args:
            invoice: Invoice object to append
            filename: CSV filename (default: facturas_historico.csv)
            
        Returns:
            Path to CSV file
        """
        filepath = self.export_dir / filename
        file_exists = filepath.exists()
        
        try:
            with open(filepath, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'fecha_procesamiento',
                    'ncf',
                    'rnc',
                    'razon_social',
                    'fecha_emision',
                    'subtotal',
                    'itbis',
                    'total',
                    'imagen_original'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=settings.csv_delimiter)
                
                # Write header if file doesn't exist
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow({
                    'fecha_procesamiento': invoice.fecha_procesamiento.strftime('%Y-%m-%d %H:%M:%S'),
                    'ncf': invoice.ncf or '',
                    'rnc': invoice.rnc or '',
                    'razon_social': invoice.razon_social or '',
                    'fecha_emision': invoice.fecha_emision or '',
                    'subtotal': invoice.montos.subtotal or '',
                    'itbis': invoice.montos.itbis or '',
                    'total': invoice.montos.total or '',
                    'imagen_original': invoice.metadata.imagen_original or ''
                })
            
            app_logger.info(f"Appended invoice to CSV: {filepath}")
            return str(filepath)
            
        except Exception as e:
            app_logger.error(f"Error appending to CSV: {e}")
            raise


# Global export handler instance
export_handler = ExportHandler()
