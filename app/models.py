"""
Pydantic models for invoice data structures
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import uuid4


class InvoiceAmounts(BaseModel):
    """Invoice monetary amounts"""
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
