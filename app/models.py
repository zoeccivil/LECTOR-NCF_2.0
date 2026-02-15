"""
Pydantic models for invoice data structures
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import uuid4
from enum import Enum


class TipoNCF(str, Enum):
    """Tipos de NCF según DGII"""
    E31 = "E31"  # e-CF
    E32 = "E32"  # e-CF Gubernamental
    E33 = "E33"  # e-CF para Exportaciones
    E34 = "E34"  # e-CF para Pagos al Exterior
    E41 = "E41"  # e-CF Nota de Crédito
    E43 = "E43"  # e-CF Nota de Débito
    E44 = "E44"  # e-CF Regímenes Especiales
    E45 = "E45"  # e-CF Gubernamental Regímenes Especiales
    E47 = "E47"  # e-CF para Compras
    B01 = "B01"  # Facturas Crédito Fiscal
    B02 = "B02"  # Facturas Consumidores Finales
    B14 = "B14"  # Notas de Crédito
    B15 = "B15"  # Notas de Débito
    B16 = "B16"  # Facturas Regímenes Especiales


class Montos(BaseModel):
    """
    Montos de factura con validaciones automáticas
    Alias for InvoiceAmounts for backward compatibility
    """
    subtotal: Optional[float] = Field(None, description="Monto antes de impuesto")
    itbis: Optional[float] = Field(None, description="ITBIS (18%)")
    total: Optional[float] = Field(None, description="Monto total")
    descuento: Optional[float] = Field(None, description="Descuento aplicado")
    moneda: str = Field("DOP", description="Código de moneda")
    
    @property
    def is_complete(self) -> bool:
        """Verifica si todos los montos principales están presentes"""
        return all([self.subtotal is not None, self.itbis is not None, self.total is not None])
    
    @property
    def calculated_total(self) -> Optional[float]:
        """Calcula total teórico: subtotal + itbis - descuento"""
        if self.subtotal is not None and self.itbis is not None:
            calc = self.subtotal + self.itbis
            if self.descuento:
                calc -= self.descuento
            return round(calc, 2)
        return None
    
    @property
    def total_matches(self) -> bool:
        """Verifica coincidencia entre total declarado y calculado (tolerancia RD$1)"""
        if self.total and self.calculated_total:
            diff = abs(self.total - self.calculated_total)
            return diff < 1.00
        return False


# Alias for backward compatibility
class InvoiceAmounts(Montos):
    """Invoice monetary amounts (alias for Montos)"""
    pass


class InvoiceMetadata(BaseModel):
    """Invoice processing metadata"""
    imagen_original: Optional[str] = Field(None, description="Original image filename")
    confianza_ocr: Optional[float] = Field(None, description="OCR confidence score")
    origen: str = Field("whatsapp", description="Source of invoice")
    procesado_por: str = Field("LECTOR-NCF", description="Processing system")


class Invoice(BaseModel):
    """Complete invoice data model"""
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique invoice ID")
    fecha_procesamiento: datetime = Field(default_factory=lambda: datetime.now(), description="Processing timestamp")
    ncf: Optional[str] = Field(None, description="Número de Comprobante Fiscal")
    tipo_ncf: Optional[str] = Field(None, description="Tipo de NCF (E31, B01, etc.)")
    rnc: Optional[str] = Field(None, description="Registro Nacional del Contribuyente")
    razon_social: Optional[str] = Field(None, description="Business name")
    empresa: Optional[str] = Field(None, description="Business name (alias for razon_social)")
    fecha_emision: Optional[str] = Field(None, description="Invoice issue date")
    fecha: Optional[str] = Field(None, description="Invoice date (alias for fecha_emision)")
    montos: Montos = Field(default_factory=Montos, description="Invoice amounts")
    metadata: InvoiceMetadata = Field(default_factory=InvoiceMetadata, description="Processing metadata")
    texto_completo: Optional[str] = Field(None, description="Full OCR text (for debugging)")
    image_filename: Optional[str] = Field(None, description="Source image filename")
    ocr_confidence: Optional[float] = Field(None, description="OCR confidence score")
    
    @field_validator('ncf')
    @classmethod
    def validate_ncf_format(cls, v):
        """Validate NCF format if provided"""
        if v:
            # Basic validation - should be improved with validators.py
            v = v.strip().upper()
        return v
    
    @field_validator('rnc')
    @classmethod
    def validate_rnc_format(cls, v):
        """Validate RNC format if provided"""
        if v:
            # Basic validation - should be improved with validators.py
            v = v.strip()
        return v


class WhatsAppMessage(BaseModel):
    """WhatsApp message model"""
    from_number: str = Field(..., description="Sender's WhatsApp number")
    to_number: str = Field(..., description="Recipient's WhatsApp number")
    message_sid: str = Field(..., description="Twilio message SID")
    num_media: int = Field(0, description="Number of media attachments")
    media_url: Optional[str] = Field(None, description="Media URL")
    media_content_type: Optional[str] = Field(None, description="Media content type")
    body: Optional[str] = Field(None, description="Message body text")


class ProcessingResult(BaseModel):
    """Result of invoice processing"""
    success: bool = Field(..., description="Whether processing succeeded")
    invoice: Optional[Invoice] = Field(None, description="Extracted invoice data")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    warnings: list[str] = Field(default_factory=list, description="Processing warnings")
