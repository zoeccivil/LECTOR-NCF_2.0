"""
Validators for NCF and RNC formats according to Dominican Republic standards
"""
import re
from typing import Optional


def validate_ncf(ncf: str) -> bool:
    """
    Validate NCF (Número de Comprobante Fiscal) format
    
    Format: Letter + 2 digits + 8 digits
    Examples: B0100000001, B1500123456, E310000001
    
    Valid types: A, B, E (for comprobantes)
    Valid series: 01-16, 31-47
    
    Args:
        ncf: NCF string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not ncf:
        return False
    
    # Remove spaces and convert to uppercase
    ncf = ncf.strip().upper()
    
    # Pattern: 1 letter + 2 digits + 8 digits (total 11 characters)
    pattern = r'^[ABE]\d{10}$'
    
    if not re.match(pattern, ncf):
        return False
    
    # Extract series (2nd and 3rd characters)
    series = int(ncf[1:3])
    
    # Valid series according to DGII
    valid_series = list(range(1, 17)) + list(range(31, 48))
    
    return series in valid_series


def validate_rnc(rnc: str) -> bool:
    """
    Validate RNC (Registro Nacional del Contribuyente) format
    
    Format: 9 or 11 digits
    Examples: 123456789, 12345678901
    
    Args:
        rnc: RNC string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not rnc:
        return False
    
    # Remove spaces and hyphens
    rnc = re.sub(r'[-\s]', '', rnc.strip())
    
    # Must be 9 or 11 digits
    if not re.match(r'^\d{9}$|^\d{11}$', rnc):
        return False
    
    return True


def extract_ncf_from_text(text: str) -> Optional[str]:
    """
    Extract NCF from text using pattern matching
    
    Args:
        text: Text containing potential NCF
        
    Returns:
        Extracted NCF if found, None otherwise
    """
    if not text:
        return None
    
    # Pattern for NCF: Letter + 2 digits + 8 digits
    # May have spaces or dashes between groups
    pattern = r'[ABE]\s*\d{2}\s*\d{8}'
    
    matches = re.findall(pattern, text.upper())
    
    for match in matches:
        # Remove spaces
        ncf = re.sub(r'\s', '', match)
        if validate_ncf(ncf):
            return ncf
    
    return None


def extract_rnc_from_text(text: str) -> Optional[str]:
    """
    Extract RNC from text using pattern matching
    
    Args:
        text: Text containing potential RNC
        
    Returns:
        Extracted RNC if found, None otherwise
    """
    if not text:
        return None
    
    # Look for 9 or 11 digit sequences with optional dashes/spaces
    # Pattern for 9 digits: 123-456-789 or 123456789
    # Pattern for 11 digits: 123-456-789-01 or 12345678901
    patterns = [
        r'\b\d{3}[-\s]\d{3}[-\s]\d{3}\b',           # 123-456-789
        r'\b\d{3}[-\s]\d{3}[-\s]\d{3}[-\s]\d{2}\b', # 123-456-789-01
        r'\b\d{9}\b',                                 # 123456789
        r'\b\d{11}\b'                                 # 12345678901
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # Remove spaces and dashes
            rnc = re.sub(r'[-\s]', '', match)
            if validate_rnc(rnc):
                return rnc
    
    return None


def validate_amount_coherence(subtotal: float, itbis: float, total: float, tolerance: float = 0.02) -> bool:
    """
    Validate that Subtotal + ITBIS = Total (with tolerance for rounding)
    
    Args:
        subtotal: Subtotal amount
        itbis: ITBIS (tax) amount
        total: Total amount
        tolerance: Allowed difference for rounding errors
        
    Returns:
        True if coherent, False otherwise
    """
    calculated_total = subtotal + itbis
    difference = abs(calculated_total - total)
    
    return difference <= tolerance
