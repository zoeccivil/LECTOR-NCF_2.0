"""
NCF Parser with python-stdnum validation
Improved accuracy for Dominican Republic invoices
"""
import re
from typing import Optional
from datetime import datetime
from loguru import logger

# Validación robusta con python-stdnum
from stdnum.do import ncf as stdnum_ncf
from stdnum.do import rnc as stdnum_rnc
from stdnum.do import cedula as stdnum_cedula
from stdnum.exceptions import ValidationError, InvalidFormat, InvalidChecksum, InvalidLength

from app.models import Invoice, Montos


class NCFParser:
    """Parser for Dominican Republic NCF invoices with validation"""
    
    def __init__(self):
        self.invoice = None
        
    def parse_invoice(self, ocr_text: str, confidence: float, image_filename: str) -> Invoice:
        """
        Parse invoice from OCR text with python-stdnum validation
        
        Args:
            ocr_text: Raw OCR text from image
            confidence: OCR confidence score
            image_filename: Source image filename
            
        Returns:
            Invoice object with extracted and validated data
        """
        logger.info("Starting invoice parsing with python-stdnum validation")
        
        # Create invoice object
        self.invoice = Invoice(
            image_filename=image_filename,
            ocr_confidence=confidence
        )
        
        # Extract and validate fields
        self.invoice.ncf = self._extract_and_validate_ncf(ocr_text)
        self.invoice.tipo_ncf = self._extract_ncf_type(self.invoice.ncf)
        self.invoice.rnc = self._extract_and_validate_rnc(ocr_text)
        self.invoice.empresa = self._extract_business_name(ocr_text, self.invoice.rnc)
        self.invoice.fecha = self._extract_date(ocr_text)
        self.invoice.montos = self._extract_amounts(ocr_text)
        
        # Log results
        self._log_extraction_summary()
        
        return self.invoice
    
    def _extract_and_validate_ncf(self, text: str) -> Optional[str]:
        """
        Extract and validate NCF using python-stdnum
        
        Formatos soportados:
        - E31 (13 dígitos) - e-CF desde 2019
        - B01 (11 dígitos) - Formato desde 2018
        - A02001021010 (19 dígitos) - Formato antiguo
        """
        logger.info("Extracting NCF with validation...")
        
        # Patrones de búsqueda ordenados por especificidad
        patterns = [
            # Formato con etiqueta "NCF:"
            r'NCF[:\s]+([ABE]\d{2}\d{8,17})',
            r'N[°o]?\s*NCF[:\s]+([ABE]\d{10,19})',
            
            # Formato e-CF (E31...)
            r'\b(E\d{2}\d{10})\b',
            
            # Formato B (B01...)
            r'\b(B\d{2}\d{8})\b',
            
            # Formato A o P antiguo
            r'\b([AP]\d{18})\b',
            
            # Con separadores
            r'([ABE]\d{2}[- ]?\d{4}[- ]?\d{4,11})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Limpiar separadores
                ncf_candidate = re.sub(r'[- ]', '', match).upper()
                
                logger.debug(f"Testing NCF candidate: {ncf_candidate}")
                
                # VALIDAR con python-stdnum
                try:
                    validated_ncf = stdnum_ncf.validate(ncf_candidate)
                    logger.info(f"✅ NCF VÁLIDO: {validated_ncf}")
                    return validated_ncf
                    
                except InvalidFormat as e:
                    logger.warning(f"❌ NCF formato inválido: {ncf_candidate}")
                    continue
                    
                except InvalidLength as e:
                    logger.warning(f"❌ NCF longitud incorrecta: {ncf_candidate}")
                    continue
                    
                except ValidationError as e:
                    logger.warning(f"❌ NCF validación fallida: {ncf_candidate} - {e}")
                    continue
        
        logger.error("❌ No se encontró NCF válido")
        return None
    
    def _extract_ncf_type(self, ncf: Optional[str]) -> Optional[str]:
        """
        Extract NCF type from validated NCF
        
        Tipos:
        - E31, E32, E33, etc. (e-CF)
        - B01, B02, B14, B15, etc.
        - A02, P02, etc. (antiguo)
        """
        if not ncf:
            return None
        
        # Primeros 3 caracteres para formato nuevo (E31, B01)
        # Primeros 3 caracteres para formato antiguo (A02, P02)
        if len(ncf) >= 3:
            tipo = ncf[:3].upper()
            logger.info(f"Tipo NCF extraído: {tipo}")
            return tipo
        
        return None
    
    def _extract_and_validate_rnc(self, text: str) -> Optional[str]:
        """
        Extract and validate RNC using python-stdnum
        
        Formatos soportados:
        - 101019921 (9 dígitos sin guiones)
        - 1-01-85004-3 (con guiones)
        - 1-8311147-2
        - 133-387263
        """
        logger.info("Extracting RNC with validation...")
        
        patterns = [
            # Con guiones (varios formatos)
            r'RNC[:\s]+(\d{1,3}-\d{5,9}-\d{1})',       # 1-01-85004-3
            r'RNC[:\s]+(\d{3}-\d{6})',                 # 133-387263
            r'RNC[:\s]*:?\s*(\d{1,3}-\d{7}-\d{1})',   # 1-8311147-2
            
            # Sin guiones
            r'RNC[:\s]+(\d{9,11})',
            r'R\.N\.C\.?\s*:?\s*(\d{9,11})',
            
            # Cerca de "Registro" o "Contribuyente"
            r'(?:Registro|Contribuyente)[^\d]{0,20}(\d{9,11})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                rnc_candidate = match.strip()
                
                logger.debug(f"Testing RNC candidate: {rnc_candidate}")
                
                # VALIDAR con python-stdnum
                try:
                    # python-stdnum acepta guiones y los limpia automáticamente
                    validated_rnc = stdnum_rnc.validate(rnc_candidate)
                    
                    # Formatear para consistencia
                    formatted_rnc = stdnum_rnc.format(validated_rnc)
                    
                    logger.info(f"✅ RNC VÁLIDO: {validated_rnc} (formateado: {formatted_rnc})")
                    return validated_rnc
                    
                except InvalidFormat as e:
                    logger.warning(f"❌ RNC formato inválido: {rnc_candidate}")
                    continue
                    
                except InvalidChecksum as e:
                    # Verificar si está en whitelist
                    try:
                        # python-stdnum maneja whitelist internamente
                        clean_rnc = rnc_candidate.replace('-', '').replace(' ', '')
                        if stdnum_rnc.validate(clean_rnc):
                            logger.info(f"✅ RNC VÁLIDO (whitelist): {clean_rnc}")
                            return clean_rnc
                    except:
                        logger.warning(f"❌ RNC checksum inválido: {rnc_candidate}")
                        continue
                    
                except InvalidLength as e:
                    logger.warning(f"❌ RNC longitud incorrecta: {rnc_candidate}")
                    continue
                    
                except ValidationError as e:
                    logger.warning(f"❌ RNC validación fallida: {rnc_candidate} - {e}")
                    continue
        
        logger.error("❌ No se encontró RNC válido")
        return None
    
    def _extract_business_name(self, text: str, rnc: Optional[str] = None) -> Optional[str]:
        """
        Extract business name
        
        Estrategias:
        1. Buscar cerca del RNC
        2. Buscar en líneas superiores (encabezado)
        3. Buscar patrones de empresa (SRL, SA, EIRL, etc.)
        """
        lines = text.split('\n')
        
        # Estrategia 1: Buscar cerca del RNC
        if rnc:
            for i, line in enumerate(lines):
                if rnc in line or 'RNC' in line.upper():
                    # Buscar en líneas anteriores (nombre suele estar arriba del RNC)
                    for j in range(max(0, i-5), i):
                        candidate = lines[j].strip()
                        # Filtrar líneas que parecen nombres de empresa
                        if len(candidate) > 5 and not re.match(r'^[\d\s\-:]+$', candidate):
                            # Verificar que no sea dirección o teléfono
                            if not re.search(r'(?:tel|phone|calle|ave|dirección)', candidate, re.IGNORECASE):
                                logger.info(f"Empresa encontrada cerca de RNC: {candidate}")
                                return candidate.upper()
        
        # Estrategia 2: Buscar en primeras 10 líneas (encabezado)
        for line in lines[:10]:
            line = line.strip()
            # Buscar líneas con indicadores de empresa
            if re.search(r'\b(SRL|S\.R\.L\.|SA|S\.A\.|EIRL|CIA|LTDA|INC)\b', line, re.IGNORECASE):
                if len(line) > 5:
                    logger.info(f"Empresa encontrada por patrón SRL/SA: {line}")
                    return line.upper()
        
        # Estrategia 3: Línea más larga en encabezado (suele ser el nombre)
        header_lines = [l.strip() for l in lines[:5] if len(l.strip()) > 10]
        if header_lines:
            empresa = max(header_lines, key=len)
            logger.info(f"Empresa encontrada por heurística: {empresa}")
            return empresa.upper()
        
        logger.warning("❌ No se pudo extraer nombre de empresa")
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """
        Extract invoice date
        
        Formatos soportados:
        - DD/MM/YYYY
        - YYYY-MM-DD
        - DD-MM-YYYY
        - Month DD, YYYY
        """
        patterns = [
            # DD/MM/YYYY o DD-MM-YYYY
            r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b',
            
            # YYYY-MM-DD
            r'\b(\d{4}-\d{2}-\d{2})\b',
            
            # Con etiqueta "Fecha:"
            r'Fecha[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
            
            # Con etiqueta "Date:"
            r'Date[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                
                # Intentar parsear y normalizar
                try:
                    # Probar formato DD/MM/YYYY
                    if '/' in date_str or '-' in date_str:
                        parts = re.split(r'[/-]', date_str)
                        if len(parts) == 3:
                            # Si año está al final (DD/MM/YYYY)
                            if len(parts[2]) == 4:
                                day, month, year = parts
                                normalized = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                                
                                # Validar fecha
                                datetime.strptime(normalized, '%Y-%m-%d')
                                logger.info(f"Fecha encontrada: {normalized}")
                                return normalized
                            # Si año está al inicio (YYYY-MM-DD)
                            elif len(parts[0]) == 4:
                                logger.info(f"Fecha encontrada: {date_str}")
                                return date_str
                                
                except ValueError as e:
                    logger.warning(f"Fecha inválida: {date_str}")
                    continue
        
        logger.warning("❌ No se pudo extraer fecha")
        return None
    
    def _extract_amounts(self, text: str) -> Montos:
        """Extract monetary amounts from invoice text"""
        montos = Montos()
        lines = text.split('\n')
        
        # ESTRATEGIA 1: TOTAL en la misma línea
        total_patterns = [
            r'TOTAL[:\s]+(?:RD\$|RD|[$]|DOP)?\s*([\d,\.]+)',
            r'(?:TOTAL\s+A\s+PAGAR)[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'(?:MONTO\s+TOTAL)[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                total_str = match.group(1)
                # Limpiar comas
                total_str = total_str.replace(',', '')
                
                # Manejar punto como separador de miles (ej: 1.804.80)
                if total_str.count('.') > 1:
                    # Remover todos los puntos excepto el último (decimal)
                    parts = total_str.split('.')
                    if len(parts) > 1:
                        # Unir todos excepto el último con nada, último es decimal
                        total_str = ''.join(parts[:-1]) + '.' + parts[-1]
                
                try:
                    montos.total = float(total_str)
                    logger.info(f"✅ Total encontrado (inline): RD${montos.total:,.2f}")
                    break
                except ValueError:
                    continue
        
        # ESTRATEGIA 2: TOTAL en múltiples líneas
        if not montos.total:
            for i, line in enumerate(lines):
                if re.search(r'\bTOTAL\b', line, re.IGNORECASE):
                    # Buscar monto en las siguientes 3 líneas
                    for j in range(i, min(i + 4, len(lines))):
                        next_line = lines[j]
                        # Buscar patrón de monto
                        amount_patterns = [
                            r'(?:RD\$|RD|[$]|DOP)\s*([\d,\.]+)',
                            r'^\s*([\d,\.]+)\s*$',
                            r'Monto\s*\$?([\d,\.]+)',
                        ]
                        
                        for pattern in amount_patterns:
                            match = re.search(pattern, next_line)
                            if match:
                                total_str = match.group(1)
                                # Limpiar comas
                                total_str = total_str.replace(',', '')
                                
                                # Manejar punto como separador de miles
                                if total_str.count('.') > 1:
                                    parts = total_str.split('.')
                                    if len(parts) > 1:
                                        total_str = ''.join(parts[:-1]) + '.' + parts[-1]
                                
                                try:
                                    total = float(total_str)
                                    # Validar que sea un monto razonable (> 10)
                                    if total > 10:
                                        montos.total = total
                                        logger.info(f"✅ Total encontrado (multiline): RD${montos.total:,.2f}")
                                        break
                                except ValueError:
                                    continue
                        
                        if montos.total:
                            break
                    
                    if montos.total:
                        break
        
        # SUBTOTAL
        subtotal_patterns = [
            r'SUBTOTAL[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'Sub\s*Total[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
        ]
        
        for pattern in subtotal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                subtotal_str = match.group(1).replace(',', '')
                try:
                    montos.subtotal = float(subtotal_str)
                    logger.info(f"✅ Subtotal encontrado: RD${montos.subtotal:,.2f}")
                    break
                except ValueError:
                    continue
        
        # ITBIS
        itbis_patterns = [
            r'ITBIS[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'(?:18|16)%?\s*ITBIS[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'(?:IMPUESTO|TAX)[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
        ]
        
        for pattern in itbis_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                itbis_str = match.group(1).replace(',', '')
                try:
                    montos.itbis = float(itbis_str)
                    logger.info(f"✅ ITBIS encontrado: RD${montos.itbis:,.2f}")
                    break
                except ValueError:
                    continue
        
        return montos
    
    def _log_extraction_summary(self):
        """Log summary of extraction results"""
        logger.info("=" * 70)
        logger.info("RESUMEN DE EXTRACCIÓN:")
        logger.info("=" * 70)
        logger.info(f"NCF:      {self.invoice.ncf or '❌ NO ENCONTRADO'}")
        logger.info(f"Tipo NCF: {self.invoice.tipo_ncf or '❌ NO ENCONTRADO'}")
        logger.info(f"RNC:      {self.invoice.rnc or '❌ NO ENCONTRADO'}")
        logger.info(f"Empresa:  {self.invoice.empresa or '❌ NO ENCONTRADO'}")
        logger.info(f"Fecha:    {self.invoice.fecha or '❌ NO ENCONTRADO'}")
        logger.info(f"Subtotal: RD${self.invoice.montos.subtotal:,.2f}" if self.invoice.montos.subtotal else "Subtotal: ❌ NO ENCONTRADO")
        logger.info(f"ITBIS:    RD${self.invoice.montos.itbis:,.2f}" if self.invoice.montos.itbis else "ITBIS:    ❌ NO ENCONTRADO")
        logger.info(f"Total:    RD${self.invoice.montos.total:,.2f}" if self.invoice.montos.total else "Total:    ❌ NO ENCONTRADO")
        logger.info("=" * 70)


# Global parser instance
ncf_parser = NCFParser()