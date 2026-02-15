"""
Tests for OCR processor
"""
import pytest
from app.ocr_processor import OCRProcessor


class TestOCRProcessor:
    """Tests for OCR processor (requires Google Cloud credentials)"""
    
    @pytest.fixture
    def processor(self):
        """Create OCR processor instance"""
        return OCRProcessor()
    
    def test_processor_initialization(self, processor):
        """Test that processor initializes"""
        assert processor is not None
    
    # Note: Actual OCR tests require valid Google Cloud credentials
    # and real invoice images, so we only test initialization here
    
    def test_confidence_calculation_empty(self, processor):
        """Test confidence calculation with empty response"""
        class MockResponse:
            text_annotations = []
        
        confidence = processor._calculate_confidence(MockResponse())
        assert confidence == 0.0
    
    def test_confidence_calculation_default(self, processor):
        """Test confidence returns default when not available"""
        class MockResponse:
            text_annotations = [None, None]  # First is full text, second has no confidence
        
        confidence = processor._calculate_confidence(MockResponse())
        assert confidence == 0.85  # Default value
