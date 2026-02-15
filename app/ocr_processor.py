"""
Google Cloud Vision OCR processor for invoice text extraction
"""
from google.cloud import vision
from typing import Optional, Tuple
import os
from app.utils.logger import app_logger
from app.utils.config import settings


class OCRProcessor:
    """Handles OCR processing using Google Cloud Vision API"""
    
    def __init__(self):
        """Initialize Google Cloud Vision client"""
        try:
            # Set credentials from config
            if settings.google_application_credentials and os.path.exists(settings.google_application_credentials):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.google_application_credentials
            
            self.client = vision.ImageAnnotatorClient()
            app_logger.info("Google Cloud Vision client initialized successfully")
        except Exception as e:
            app_logger.error(f"Failed to initialize Google Cloud Vision client: {e}")
            self.client = None
    
    def extract_text_from_image(self, image_bytes: bytes) -> Tuple[Optional[str], Optional[float]]:
        """
        Extract text from image using Google Cloud Vision OCR
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        if not self.client:
            app_logger.error("Vision client not initialized")
            return None, None
        
        try:
            # Create vision image
            image = vision.Image(content=image_bytes)
            
            # Perform text detection
            app_logger.info("Sending image to Google Cloud Vision API...")
            response = self.client.text_detection(image=image)
            
            # Check for errors
            if response.error.message:
                app_logger.error(f"Vision API error: {response.error.message}")
                return None, None
            
            # Get text annotations
            texts = response.text_annotations
            
            if not texts:
                app_logger.warning("No text detected in image")
                return None, 0.0
            
            # First annotation contains full text
            full_text = texts[0].description
            
            # Calculate average confidence
            confidence = self._calculate_confidence(response)
            
            app_logger.info(f"Successfully extracted {len(full_text)} characters with confidence {confidence:.2f}")
            app_logger.debug(f"Extracted text preview: {full_text[:200]}...")
            
            return full_text, confidence
            
        except Exception as e:
            app_logger.error(f"Error during OCR processing: {e}")
            return None, None
    
    def extract_text_with_document_detection(self, image_bytes: bytes) -> Tuple[Optional[str], Optional[float]]:
        """
        Extract text using document text detection (better for dense text)
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        if not self.client:
            app_logger.error("Vision client not initialized")
            return None, None
        
        try:
            # Create vision image
            image = vision.Image(content=image_bytes)
            
            # Perform document text detection
            app_logger.info("Performing document text detection...")
            response = self.client.document_text_detection(image=image)
            
            # Check for errors
            if response.error.message:
                app_logger.error(f"Vision API error: {response.error.message}")
                return None, None
            
            # Get full text
            if not response.full_text_annotation:
                app_logger.warning("No text detected in document")
                return None, 0.0
            
            full_text = response.full_text_annotation.text
            
            # Calculate confidence
            confidence = self._calculate_document_confidence(response)
            
            app_logger.info(f"Successfully extracted {len(full_text)} characters with confidence {confidence:.2f}")
            
            return full_text, confidence
            
        except Exception as e:
            app_logger.error(f"Error during document OCR processing: {e}")
            return None, None
    
    def _calculate_confidence(self, response) -> float:
        """Calculate average confidence from text annotations"""
        if not response.text_annotations or len(response.text_annotations) <= 1:
            return 0.0
        
        # Skip first annotation (full text) and calculate average
        confidences = []
        for annotation in response.text_annotations[1:]:
            if hasattr(annotation, 'confidence'):
                confidences.append(annotation.confidence)
        
        if not confidences:
            return 0.85  # Default confidence if not available
        
        return sum(confidences) / len(confidences)
    
    def _calculate_document_confidence(self, response) -> float:
        """Calculate average confidence from document text detection"""
        if not response.full_text_annotation or not response.full_text_annotation.pages:
            return 0.0
        
        confidences = []
        for page in response.full_text_annotation.pages:
            if hasattr(page, 'confidence'):
                confidences.append(page.confidence)
        
        if not confidences:
            return 0.85  # Default confidence
        
        return sum(confidences) / len(confidences)
    
    def process_invoice_image(self, image_bytes: bytes, use_document_detection: bool = True) -> Tuple[Optional[str], Optional[float]]:
        """
        Process invoice image and extract text
        
        Args:
            image_bytes: Image data as bytes
            use_document_detection: Whether to use document text detection (better for invoices)
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        if use_document_detection:
            return self.extract_text_with_document_detection(image_bytes)
        else:
            return self.extract_text_from_image(image_bytes)


# Global OCR processor instance
ocr_processor = OCRProcessor()
