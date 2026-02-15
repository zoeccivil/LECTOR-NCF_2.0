"""
NCF Parser with python-stdnum validation
Improved accuracy for Dominican Republic invoices
Enhanced with patterns from facturas-opensource
"""
import re
from typing import Optional, List, Tuple
from datetime import datetime
from loguru import logger

# Validación robusta con python-stdnum
from stdnum.do import ncf as stdnum_ncf
from stdnum.do import rnc as stdnum_rnc
from stdnum.do import cedula as stdnum_cedula
from stdnum.exceptions import ValidationError, InvalidFormat, InvalidChecksum, InvalidLength

from app.models import InvoiceData, Montos, TipoNCF


class NCFParser:
    """Parser for Dominican Republic NCF invoices with validation"""
    
    def __init__(self):
        self.invoice = None
        
    def parse_invoice(self, ocr_text: str, confidence: float, image_filename: str) -> InvoiceData:
        """
        Parse invoice from OCR text with python-stdnum validation
        
        Args:
            ocr_text: Raw OCR text from image
            confidence: OCR confidence score
            image_filename: Source image filename
            
        Returns:
            InvoiceData object with extracted and validated data
        """
        logger.info("Starting invoice parsing with python-stdnum validation")
        
        # Create invoice object
        self.invoice = InvoiceData(
            image_filename=image_filename,
            ocr_confidence=confidence,
            ocr_text=ocr_text
        )
        
        # Extract and validate fields
        self.invoice.ncf = self._extract_and_validate_ncf(ocr_text)
        self.invoice.tipo_ncf = self._extract_ncf_type(self.invoice.ncf)
        self.invoice.rnc, self.invoice.rnc_formatted = self._extract_and_validate_rnc(ocr_text)
        self.invoice.cedula = self._extract_cedula(ocr_text)
        self.invoice.empresa = self._extract_business_name(ocr_text, self.invoice.rnc)
        self.invoice.fecha = self._extract_date(ocr_text)
        
        # Extract amounts
        lines = ocr_text.split('\n')
        self.invoice.montos = self._extract_amounts(ocr_text, lines)
        
        # Calculate confidence and detect anomalies
        self.invoice.confidence_score = self._calculate_confidence_score()
        self.invoice.audit_flags = self._detect_anomalies()
        self.invoice.processed_at = datetime.now()
        
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
    
    def _extract_ncf_type(self, ncf: Optional[str]) -> Optional[TipoNCF]:
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
            try:
                tipo_enum = TipoNCF(tipo)
                logger.info(f"Tipo NCF extraído: {tipo}")
                return tipo_enum
            except ValueError:
                logger.warning(f"Tipo NCF desconocido: {tipo}")
                return None
        
        return None
    
    def _extract_and_validate_rnc(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract and validate RNC - RETORNA (rnc_limpio, rnc_formateado)
        
        Mejoras:
        - Busca RNC con Y sin guiones
        - Valida con python-stdnum
        - Retorna ambas versiones (limpia y formateada)
        
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
                    
                    logger.success(f"✅ RNC válido: {validated_rnc} ({formatted_rnc})")
                    return validated_rnc, formatted_rnc
                    
                except InvalidFormat as e:
                    logger.warning(f"❌ RNC formato inválido: {rnc_candidate}")
                    continue
                    
                except InvalidChecksum as e:
                    # Verificar si está en whitelist
                    try:
                        # python-stdnum maneja whitelist internamente
                        clean_rnc = rnc_candidate.replace('-', '').replace(' ', '')
                        if stdnum_rnc.validate(clean_rnc):
                            formatted = stdnum_rnc.format(clean_rnc)
                            logger.success(f"✅ RNC válido (whitelist): {clean_rnc} ({formatted})")
                            return clean_rnc, formatted
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
        return None, None
    
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
    
    def _extract_cedula(self, text: str) -> Optional[str]:
        """
        Extracción de Cédula (documento de identidad dominicano)
        
        Formatos:
        - 402-1234567-8
        - 40212345678
        """
        patterns = [
            r'C[ée]dula[:\s]+(\d{3}-\d{7}-\d{1})',
            r'C[ée]dula[:\s]+(\d{11})',
            r'ID[:\s]+(\d{3}-\d{7}-\d{1})',
            r'ID[:\s]+(\d{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    validated = stdnum_cedula.validate(match.group(1))
                    logger.success(f"✅ Cédula válida: {validated}")
                    return validated
                except ValidationError:
                    continue
        
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
    
    def _extract_amounts(self, text: str, lines: List[str]) -> Montos:
        """
        Extracción ROBUSTA de montos
        
        Estrategias:
        1. Inline: "TOTAL RD$1,804.80"
        2. Multi-línea: "TOTAL\nRD$ 1,804.80"
        3. Con etiquetas variadas: "TOTAL A PAGAR", "MONTO TOTAL"
        4. Ultimo número grande en factura (fallback)
        """
        montos = Montos()
        
        # ESTRATEGIA 1: TOTAL en la misma línea
        total_patterns = [
            r'\bTOTAL[:\s]+(?:RD\$|RD|[$]|DOP)?\s*([\d,\.]+)',
            r'(?:TOTAL\s+A\s+PAGAR)[:\s]*(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'(?:MONTO\s+TOTAL)[:\s]*(?:RD\$|RD|[$])?\s*([\d,\.]+)',
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount = self._parse_amount(match.group(1))
                    if amount > 10:
                        logger.success(f"✅ Total (inline): RD${amount:,.2f}")
                        montos.total = amount
                        break
                except:
                    continue
        
        # ESTRATEGIA 2: TOTAL en múltiples líneas
        if not montos.total:
            for i, line in enumerate(lines):
                if re.search(r'\bTOTAL\b', line, re.IGNORECASE):
                    # Buscar monto en las siguientes 3 líneas
                    for j in range(i, min(i + 4, len(lines))):
                        next_line = lines[j]
                        
                        # Buscar patrón de monto
                        amount_match = re.search(r'(?:RD\$|RD|[$]|DOP)?\s*([\d,\.]+)', next_line)
                        if amount_match:
                            try:
                                amount = self._parse_amount(amount_match.group(1))
                                if amount > 10:
                                    logger.success(f"✅ Total (multiline): RD${amount:,.2f}")
                                    montos.total = amount
                                    break
                            except:
                                continue
                    
                    if montos.total:
                        break
        
        # ESTRATEGIA 3: Fallback - número más grande
        if not montos.total:
            all_amounts = re.findall(r'[\d,\.]+', text)
            amounts_parsed = []
            for amt_str in all_amounts:
                try:
                    amount = self._parse_amount(amt_str)
                    if 100 < amount < 1000000:  # Rango razonable
                        amounts_parsed.append(amount)
                except:
                    continue
            
            if amounts_parsed:
                max_amount = max(amounts_parsed)
                logger.warning(f"⚠️ Total por fallback (mayor monto): RD${max_amount:,.2f}")
                montos.total = max_amount
        
        # SUBTOTAL
        subtotal_patterns = [
            r'SUBTOTAL[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'Sub\s*Total[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
        ]
        
        for pattern in subtotal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    montos.subtotal = self._parse_amount(match.group(1))
                    logger.success(f"✅ Subtotal encontrado: RD${montos.subtotal:,.2f}")
                    break
                except ValueError:
                    continue
        
        # ITBIS
        itbis_patterns = [
            r'ITBIS[:\s\(]*(?:\d+%\))?[:\s]*(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'(?:18|16)%?\s*ITBIS[:\s]*(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'(?:IMPUESTO|TAX)[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
        ]
        
        for pattern in itbis_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    montos.itbis = self._parse_amount(match.group(1))
                    logger.success(f"✅ ITBIS encontrado: RD${montos.itbis:,.2f}")
                    break
                except ValueError:
                    continue
        
        return montos
    
    def _parse_amount(self, amount_str: str) -> float:
        """
        Parse monto con manejo inteligente de separadores
        
        Casos:
        - 1,804.80 → 1804.80 (coma miles, punto decimal)
        - 1.804,80 → 1804.80 (punto miles, coma decimal) 
        - 1.804.80 → 1804.80 (punto miles, punto decimal)
        - 1804.80 → 1804.80 (sin separador de miles)
        """
        # Quitar espacios
        amount_str = amount_str.strip()
        
        # Caso 1: Formato europeo (1.804,80)
        if ',' in amount_str and '.' in amount_str:
            # Si la coma viene después del punto → europeo
            if amount_str.rindex(',') > amount_str.rindex('.'):
                # Reemplazar punto por nada, coma por punto
                amount_str = amount_str.replace('.', '').replace(',', '.')
            # Si el punto viene después → americano estándar
            else:
                amount_str = amount_str.replace(',', '')
        
        # Caso 2: Solo comas (puede ser miles o decimal)
        elif ',' in amount_str:
            # Si hay solo una coma y está en las últimas 3 posiciones → decimal europeo
            comma_pos = amount_str.index(',')
            if comma_pos >= len(amount_str) - 3:
                amount_str = amount_str.replace(',', '.')
            # Si hay múltiples comas o está lejos del final → separador de miles
            else:
                amount_str = amount_str.replace(',', '')
        
        # Caso 3: Múltiples puntos (1.804.80) → quitar todos excepto último
        elif amount_str.count('.') > 1:
            parts = amount_str.split('.')
            amount_str = ''.join(parts[:-1]) + '.' + parts[-1]
        
        return float(amount_str)
    
    def _calculate_confidence_score(self) -> float:
        """
        Calcula score de confianza basado en campos extraídos
        
        Pesos:
        - NCF: 30%
        - RNC: 25%
        - Total: 25%
        - Empresa: 10%
        - Fecha: 10%
        """
        score = 0.0
        weights = {
            'ncf': 0.30,
            'rnc': 0.25,
            'total': 0.25,
            'empresa': 0.10,
            'fecha': 0.10,
        }
        
        if self.invoice.ncf:
            score += weights['ncf']
        if self.invoice.rnc:
            score += weights['rnc']
        if self.invoice.montos.total:
            score += weights['total']
        if self.invoice.empresa:
            score += weights['empresa']
        if self.invoice.fecha:
            score += weights['fecha']
        
        return round(score, 2)
    
    def _detect_anomalies(self) -> List[str]:
        """
        Detecta anomalías en factura
        
        Flags:
        - total_mismatch: Total extraído ≠ calculado
        - itbis_anomaly: ITBIS no es ~18% del subtotal
        - low_confidence: Score < 50%
        - missing_required: Falta NCF o RNC
        """
        flags = []
        
        # Total no coincide con cálculo
        if self.invoice.montos.total and not self.invoice.montos.total_matches:
            flags.append("total_mismatch")
            logger.warning(f"⚠️ Total extraído ({self.invoice.montos.total}) ≠ calculado ({self.invoice.montos.calculated_total})")
        
        # ITBIS anómalo (debe ser ~18%)
        if self.invoice.montos.subtotal and self.invoice.montos.itbis:
            expected_itbis = self.invoice.montos.subtotal * 0.18
            diff = abs(self.invoice.montos.itbis - expected_itbis)
            if diff > 5:  # Más de RD$5 de diferencia
                flags.append("itbis_anomaly")
                logger.warning(f"⚠️ ITBIS anómalo: esperado {expected_itbis:.2f}, encontrado {self.invoice.montos.itbis:.2f}")
        
        # Confidence muy bajo
        if self.invoice.confidence_score and self.invoice.confidence_score < 0.50:
            flags.append("low_confidence")
            logger.warning(f"⚠️ Confianza baja: {self.invoice.confidence_score:.0%}")
        
        # Campos requeridos faltantes
        if not self.invoice.ncf:
            flags.append("missing_ncf")
        if not self.invoice.rnc:
            flags.append("missing_rnc")
        
        return flags
    
    def _log_extraction_summary(self):
        """Log summary of extraction results"""
        logger.info("=" * 70)
        logger.info("RESUMEN DE EXTRACCIÓN:")
        logger.info("=" * 70)
        logger.info(f"NCF:               {self.invoice.ncf or '❌ NO ENCONTRADO'}")
        logger.info(f"Tipo NCF:          {self.invoice.tipo_ncf.value if self.invoice.tipo_ncf else '❌ NO ENCONTRADO'}")
        logger.info(f"RNC:               {self.invoice.rnc or '❌ NO ENCONTRADO'}")
        logger.info(f"RNC (formateado):  {self.invoice.rnc_formatted or '❌'}")
        logger.info(f"Cédula:            {self.invoice.cedula or '-'}")
        logger.info(f"Empresa:           {self.invoice.empresa or '❌ NO ENCONTRADO'}")
        logger.info(f"Fecha:             {self.invoice.fecha or '❌ NO ENCONTRADO'}")
        logger.info(f"Subtotal:          RD${self.invoice.montos.subtotal:,.2f}" if self.invoice.montos.subtotal else "Subtotal:          ❌")
        logger.info(f"ITBIS:             RD${self.invoice.montos.itbis:,.2f}" if self.invoice.montos.itbis else "ITBIS:             ❌")
        logger.info(f"Total:             RD${self.invoice.montos.total:,.2f}" if self.invoice.montos.total else "Total:             ❌")
        logger.info(f"\n🎯 CONFIANZA:      {self.invoice.confidence_score:.0%}" if self.invoice.confidence_score else "\n🎯 CONFIANZA:      N/A")
        logger.info(f"✅ VÁLIDA:         {'SÍ' if self.invoice.is_valid else 'NO'}")
        if self.invoice.audit_flags:
            logger.info(f"⚠️ ALERTAS:        {', '.join(self.invoice.audit_flags)}")
        logger.info("=" * 70)


# Global parser instance
ncf_parser = NCFParser()