"""
Tests for NCF and RNC validators
"""
import pytest
from app.utils.validators import (
    validate_ncf,
    validate_rnc,
    extract_ncf_from_text,
    extract_rnc_from_text,
    validate_amount_coherence
)


class TestNCFValidation:
    """Tests for NCF validation"""
    
    def test_valid_ncf_formats(self):
        """Test valid NCF formats"""
        valid_ncfs = [
            "B0100000001",
            "B0200000123",
            "B1400001234",
            "B1500123456",
            "E3100000001",
            "A0100000001",
        ]
        
        for ncf in valid_ncfs:
            assert validate_ncf(ncf), f"NCF {ncf} should be valid"
    
    def test_invalid_ncf_formats(self):
        """Test invalid NCF formats"""
        invalid_ncfs = [
            "X0100000001",  # Invalid letter
            "B0000000001",  # Invalid series
            "B1700000001",  # Invalid series
            "B010000000",   # Too short
            "B01000000001", # Too long
            "B01XXXXXXX",   # Non-numeric
            "",             # Empty
            None,           # None
        ]
        
        for ncf in invalid_ncfs:
            assert not validate_ncf(ncf), f"NCF {ncf} should be invalid"
    
    def test_ncf_case_insensitive(self):
        """Test that NCF validation is case insensitive"""
        assert validate_ncf("b0100000001")
        assert validate_ncf("B0100000001")
        assert validate_ncf("B0100000001".upper())
    
    def test_ncf_with_spaces(self):
        """Test NCF extraction handles spaces"""
        assert extract_ncf_from_text("NCF: B01 00000001") == "B0100000001"
        assert extract_ncf_from_text("B 01 00000001") == "B0100000001"


class TestRNCValidation:
    """Tests for RNC validation"""
    
    def test_valid_rnc_9_digits(self):
        """Test valid 9-digit RNC"""
        assert validate_rnc("123456789")
        assert validate_rnc("101234567")
    
    def test_valid_rnc_11_digits(self):
        """Test valid 11-digit RNC"""
        assert validate_rnc("12345678901")
        assert validate_rnc("10123456789")
    
    def test_invalid_rnc_formats(self):
        """Test invalid RNC formats"""
        invalid_rncs = [
            "12345678",     # Too short
            "1234567890",   # 10 digits (invalid)
            "123456789012", # Too long
            "12345678X",    # Non-numeric
            "",             # Empty
            None,           # None
        ]
        
        for rnc in invalid_rncs:
            assert not validate_rnc(rnc), f"RNC {rnc} should be invalid"
    
    def test_rnc_with_dashes(self):
        """Test RNC validation with dashes"""
        assert validate_rnc("123-456-789")
        assert validate_rnc("123-456-789-01")


class TestNCFExtraction:
    """Tests for NCF extraction from text"""
    
    def test_extract_ncf_from_invoice_text(self):
        """Test NCF extraction from typical invoice text"""
        text = """
        FACTURA
        NCF: B0100000123
        RNC: 123456789
        Total: RD$1,500.00
        """
        
        ncf = extract_ncf_from_text(text)
        assert ncf == "B0100000123"
    
    def test_extract_ncf_with_spaces(self):
        """Test NCF extraction with spaces"""
        text = "NCF B 01 00000123"
        ncf = extract_ncf_from_text(text)
        assert ncf == "B0100000123"
    
    def test_extract_ncf_no_match(self):
        """Test NCF extraction when no NCF present"""
        text = "This is a random text without NCF"
        ncf = extract_ncf_from_text(text)
        assert ncf is None


class TestRNCExtraction:
    """Tests for RNC extraction from text"""
    
    def test_extract_rnc_from_text(self):
        """Test RNC extraction from invoice text"""
        text = """
        EMPRESA EJEMPLO SRL
        RNC: 123456789
        NCF: B0100000123
        """
        
        rnc = extract_rnc_from_text(text)
        assert rnc == "123456789"
    
    def test_extract_rnc_with_dashes(self):
        """Test RNC extraction with dashes"""
        text = "RNC: 123-456-789"
        rnc = extract_rnc_from_text(text)
        assert rnc == "123456789"


class TestAmountCoherence:
    """Tests for amount coherence validation"""
    
    def test_coherent_amounts(self):
        """Test that coherent amounts pass validation"""
        assert validate_amount_coherence(1271.19, 228.81, 1500.00)
        assert validate_amount_coherence(1000.00, 180.00, 1180.00)
    
    def test_incoherent_amounts(self):
        """Test that incoherent amounts fail validation"""
        assert not validate_amount_coherence(1000.00, 100.00, 1500.00)
        assert not validate_amount_coherence(1271.19, 228.81, 2000.00)
    
    def test_rounding_tolerance(self):
        """Test that small rounding differences are tolerated"""
        # Small difference due to rounding
        assert validate_amount_coherence(1271.19, 228.81, 1500.01)
        assert validate_amount_coherence(1271.19, 228.80, 1500.00)
