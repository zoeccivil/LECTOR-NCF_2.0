"""
Tests for NCF parser
"""
import pytest
from app.ncf_parser import NCFParser
from app.models import InvoiceData


class TestNCFParser:
    """Tests for NCF invoice parser"""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance"""
        return NCFParser()
    
    def test_parse_complete_invoice(self, parser):
        """Test parsing a complete invoice"""
        ocr_text = """
        EMPRESA EJEMPLO SRL
        RNC: 101019921
        NCF: B0100000123
        
        Fecha: 10/02/2026
        
        Subtotal: RD$1,271.19
        ITBIS (18%): RD$228.81
        Total: RD$1,500.00
        """
        
        invoice = parser.parse_invoice(ocr_text, confidence=0.95, image_filename="test.jpg")
        
        assert invoice.ncf == "B0100000123"
        assert invoice.rnc == "101019921"
        assert invoice.montos.subtotal == 1271.19
        assert invoice.montos.itbis == 228.81
        assert invoice.montos.total == 1500.00
    
    def test_parse_partial_invoice(self, parser):
        """Test parsing invoice with missing data"""
        ocr_text = """
        FACTURA
        NCF: B1500000456
        Total: RD$2,350.00
        """
        
        invoice = parser.parse_invoice(ocr_text, 0.95, "test2.jpg")
        
        assert invoice.ncf == "B1500000456"
        assert invoice.montos.total == 2350.00
        assert invoice.rnc is None
    
    def test_extract_ncf(self, parser):
        """Test NCF extraction"""
        text = "Comprobante NCF: B0100000123"
        ncf = parser._extract_and_validate_ncf(text)
        assert ncf == "B0100000123"
    
    def test_extract_rnc(self, parser):
        """Test RNC extraction"""
        text = "RNC: 101019921"
        rnc, rnc_formatted = parser._extract_and_validate_rnc(text)
        assert rnc == "101019921"
    
    def test_extract_date(self, parser):
        """Test date extraction"""
        text = "Fecha: 10/02/2026"
        date = parser._extract_date(text)
        assert date == "2026-02-10" or date == "2026-10-02"  # Could be DD/MM or MM/DD
    
    def test_extract_amounts(self, parser):
        """Test amount extraction"""
        text = """
        Subtotal: 1,271.19
        ITBIS: 228.81
        Total: 1,500.00
        """
        lines = text.split('\n')
        amounts = parser._extract_amounts(text, lines)
        
        assert amounts.subtotal == 1271.19
        assert amounts.itbis == 228.81
        assert amounts.total == 1500.00
    
    def test_parse_amount_us_format(self, parser):
        """Test parsing amount in US format"""
        amount = parser._parse_amount("1,234.56")
        assert amount == 1234.56
    
    def test_parse_amount_european_format(self, parser):
        """Test parsing amount in European format"""
        amount = parser._parse_amount("1.234,56")
        assert amount == 1234.56
    
    def test_parse_amount_multiple_periods(self, parser):
        """Test parsing amount with multiple periods"""
        amount = parser._parse_amount("1.234.56")
        assert amount == 1234.56


class TestBusinessNameExtraction:
    """Tests for business name extraction"""
    
    @pytest.fixture
    def parser(self):
        return NCFParser()
    
    def test_extract_business_from_top(self, parser):
        """Test extraction from top of invoice (fallback)"""
        text = """
        FARMACIA CAROL SRL
        RNC: 101019921
        Dirección: Calle Principal
        """
        name = parser._extract_business_name(text, "101019921")
        assert "FARMACIA CAROL" in name
