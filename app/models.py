"""
Pydantic models for invoice data structures
Enhanced with dataclasses for better validation and compatibility
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum


class TipoNCF(str, Enum):
    """Tipos de NCF según DGII"""
    E31 = "E31"  # e-CF
    E32 = "E32"  # e-CF Gubernamental
    E33 = "E33"  # e-CF Regímenes Especiales
    E34 = "E34"  # e-CF Notas de Crédito
    B01 = "B01"  # Facturas Crédito Fiscal
    B02 = "B02"  # Facturas Consumidores Finales
    B14 = "B14"  # Notas de Crédito
    B15 = "B15"  # Notas de Débito


@dataclass
class Montos:
    """Montos con validaciones automáticas"""
    subtotal: Optional[float] = None
    itbis: Optional[float] = None
    total: Optional[float] = None
    descuento: Optional[float] = None
    propina: Optional[float] = None
    
    @property
    def is_complete(self) -> bool:
        """Tiene subtotal + itbis + total"""
        return all([self.subtotal, self.itbis, self.total])
    
    @property
    def calculated_total(self) -> Optional[float]:
        """Calcula total teórico: subtotal + itbis - descuento"""
        if self.subtotal is not None and self.itbis is not None:
            total = self.subtotal + self.itbis
            if self.descuento:
                total -= self.descuento
            if self.propina:
                total += self.propina
            return round(total, 2)
        return None
    
    @property
    def total_matches(self) -> bool:
        """Verifica coincidencia total extraído vs calculado"""
        if self.total and self.calculated_total:
            diff = abs(self.total - self.calculated_total)
            return diff < 1.00  # Tolerancia RD$1
        return False


@dataclass
class InvoiceData:
    """Factura completa con validaciones (dataclass version)"""
    # Identificadores
    image_filename: str
    firebase_id: Optional[str] = None
    
    # Datos fiscales
    ncf: Optional[str] = None
    tipo_ncf: Optional[TipoNCF] = None
    rnc: Optional[str] = None
    rnc_formatted: Optional[str] = None  # Con guiones (1-33-38726-3)
    cedula: Optional[str] = None
    
    # Empresa
    empresa: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    
    # Cliente
    cliente_nombre: Optional[str] = None
    cliente_rnc: Optional[str] = None
    
    # Fecha
    fecha: Optional[str] = None  # ISO YYYY-MM-DD
    
    # Montos
    montos: Montos = field(default_factory=Montos)
    
    # Metadatos OCR
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    
    # Calidad y validaciones
    confidence_score: Optional[float] = None
    audit_flags: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    
    # Source
    source: str = "whatsapp"
    user_phone: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Verifica si tiene campos mínimos válidos"""
        return all([
            self.ncf,
            self.rnc,
            self.montos.total,
            self.confidence_score and self.confidence_score >= 0.50
        ])
    
    def to_dict(self) -> dict:
        """Serialización para Firebase"""
        return {
            'image_filename': self.image_filename,
            'firebase_id': self.firebase_id,
            'ncf': self.ncf,
            'tipo_ncf': self.tipo_ncf.value if self.tipo_ncf else None,
            'rnc': self.rnc,
            'rnc_formatted': self.rnc_formatted,
            'cedula': self.cedula,
            'empresa': self.empresa,
            'direccion': self.direccion,
            'telefono': self.telefono,
            'cliente_nombre': self.cliente_nombre,
            'cliente_rnc': self.cliente_rnc,
            'fecha': self.fecha,
            'montos': {
                'subtotal': self.montos.subtotal,
                'itbis': self.montos.itbis,
                'total': self.montos.total,
                'descuento': self.montos.descuento,
                'propina': self.montos.propina,
                'is_complete': self.montos.is_complete,
                'calculated_total': self.montos.calculated_total,
                'total_matches': self.montos.total_matches
            },
            'ocr_confidence': self.ocr_confidence,
            'confidence_score': self.confidence_score,
            'audit_flags': self.audit_flags,
            'validation_errors': self.validation_errors,
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'source': self.source,
            'user_phone': self.user_phone,
            'is_valid': self.is_valid
        }


class InvoiceAmounts(BaseModel):
    """Invoice monetary amounts (Pydantic - for backward compatibility)"""
    subtotal: Optional[float] = Field(None, description="Amount before tax")
    itbis: Optional[float] = Field(None, description="ITBIS tax (18%)")
    total: Optional[float] = Field(None, description="Total amount")
    moneda: str = Field("DOP", description="Currency code")


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
    rnc: Optional[str] = Field(None, description="Registro Nacional del Contribuyente")
    razon_social: Optional[str] = Field(None, description="Business name")
    fecha_emision: Optional[str] = Field(None, description="Invoice issue date")
    montos: InvoiceAmounts = Field(default_factory=InvoiceAmounts, description="Invoice amounts")
    metadata: InvoiceMetadata = Field(default_factory=InvoiceMetadata, description="Processing metadata")
    texto_completo: Optional[str] = Field(None, description="Full OCR text (for debugging)")
    
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
