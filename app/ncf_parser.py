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
        Extract and validate RNC of the COMPANY (not the customer)
        
        CRITICAL: Distinguishes between company RNC (in header) and customer RNC (in body)
        
        Formatos soportados:
        - 101019921 (9 dígitos sin guiones)
        - 1-01-85004-3 (con guiones)
        - 1-8311147-2
        - 133-387263
        """
        logger.info("Extracting RNC with validation (company RNC only)...")
        
        lines = text.split('\n')
        
        # STRATEGY 1: Search in header (first 15 lines = company info)
        header_text = '\n'.join(lines[:15])
        
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
        
        # Try to find RNC in header first (highest priority)
        for pattern in patterns:
            matches = re.findall(pattern, header_text, re.IGNORECASE)
            for match in matches:
                rnc_candidate = match.strip()
                
                logger.debug(f"Testing RNC candidate (header): {rnc_candidate}")
                
                # VALIDATE with python-stdnum
                try:
                    validated_rnc = stdnum_rnc.validate(rnc_candidate)
                    formatted_rnc = stdnum_rnc.format(validated_rnc)
                    
                    logger.info(f"✅ RNC EMPRESA (header): {validated_rnc} (formatted: {formatted_rnc})")
                    return validated_rnc
                    
                except InvalidChecksum as e:
                    # Check whitelist
                    try:
                        clean_rnc = rnc_candidate.replace('-', '').replace(' ', '')
                        if stdnum_rnc.validate(clean_rnc):
                            logger.info(f"✅ RNC VÁLIDO (whitelist): {clean_rnc}")
                            return clean_rnc
                    except:
                        logger.warning(f"❌ RNC checksum inválido: {rnc_candidate}")
                        continue
                except Exception as e:
                    logger.debug(f"RNC validation failed: {rnc_candidate} - {e}")
                    continue
        
        # STRATEGY 2: Search in full text but SKIP customer RNC lines
        for i, line in enumerate(lines):
            # IGNORE lines with customer keywords
            if re.search(r'(Cliente|Comprador|Raz[óo]n\s+Social\s+(?:del\s+)?Cliente|RNC\s+Comprador)', 
                        line, re.IGNORECASE):
                logger.debug(f"Skipping customer RNC line: {line[:50]}")
                continue
            
            # Search for RNC in lines that are NOT customer-related
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    rnc_candidate = match.group(1).strip()
                    
                    logger.debug(f"Testing RNC candidate (body): {rnc_candidate}")
                    
                    # VALIDATE with python-stdnum
                    try:
                        validated_rnc = stdnum_rnc.validate(rnc_candidate)
                        formatted_rnc = stdnum_rnc.format(validated_rnc)
                        
                        logger.info(f"✅ RNC EMPRESA (body): {validated_rnc} (formatted: {formatted_rnc})")
                        return validated_rnc
                        
                    except InvalidChecksum as e:
                        try:
                            clean_rnc = rnc_candidate.replace('-', '').replace(' ', '')
                            if stdnum_rnc.validate(clean_rnc):
                                logger.info(f"✅ RNC VÁLIDO (whitelist): {clean_rnc}")
                                return clean_rnc
                        except:
                            continue
                    except Exception as e:
                        continue
        
        logger.error("❌ No se encontró RNC de la empresa")
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
        Extract invoice issue date (NOT NCF expiration date)
        
        CRITICAL: Ignores NCF expiration dates that are commonly mislabeled
        
        Formatos soportados:
        - DD/MM/YYYY with time: 04/Dic./2025 08:50 AM
        - DD/MM/YY with time: 16/01/26 19:21:15
        - Spanish month names: Dic., Ene., Feb., etc.
        - Standard formats: DD/MM/YYYY, YYYY-MM-DD
        """
        # Spanish month names mapping
        spanish_months = {
            'ene': '01', 'enero': '01',
            'feb': '02', 'febrero': '02',
            'mar': '03', 'marzo': '03',
            'abr': '04', 'abril': '04',
            'may': '05', 'mayo': '05',
            'jun': '06', 'junio': '06',
            'jul': '07', 'julio': '07',
            'ago': '08', 'agosto': '08',
            'sep': '09', 'sept': '09', 'septiembre': '09',
            'oct': '10', 'octubre': '10',
            'nov': '11', 'noviembre': '11',
            'dic': '12', 'diciembre': '12',
        }
        
        # STEP 1: Remove NCF expiration dates to avoid false positives
        # These patterns indicate NCF expiration, NOT invoice dates
        ignore_patterns = [
            r'V[aá]lida?\s+Hasta[:\s]+\d{2}[/-]\d{2}[/-]\d{4}',
            r'Vencimiento\s+NCF[:\s]+\d{2}[/-]\d{2}[/-]\d{4}',
            r'Fecha\s+Venc(?:imiento)?\.?\s+NCF[:\s]+\d{2}[/-]\d{2}[/-]\d{4}',
            r'e-NCF\s+Val[ií]do?\s+Hasta[:\s]+\d{2}[/-]\d{2}[/-]\d{4}',
            r'NCF\s+V[aá]lido?\s+Hasta[:\s]+\d{2}[/-]\d{2}[/-]\d{4}',
        ]
        
        cleaned_text = text
        for ignore_pattern in ignore_patterns:
            cleaned_text = re.sub(ignore_pattern, '', cleaned_text, flags=re.IGNORECASE)
        
        # STEP 2: Prioritized patterns (in order of priority)
        patterns = [
            # 1. Fecha de emisión explícita (máxima prioridad)
            (r'Fecha\s+(?:de\s+)?Emisi[óo]n[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{2,4})', 1),
            (r'Fecha\s+Firma\s+Digital[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})', 1),
            
            # 2. Fecha con hora (indica fecha de transacción)
            (r'Fecha[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{2,4}\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)', 2),
            (r'(\d{2}[/\-]\d{2}[/\-]\d{2,4}\s+\d{1,2}:\d{2}:\d{2})', 2),
            
            # 3. Fecha con palabra del mes (español) - muy específica
            (r'(\d{1,2}[/\-](?:' + '|'.join(spanish_months.keys()) + r')\.?[/\-]\d{2,4})', 3),
            
            # 4. Timestamp completo ISO
            (r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', 4),
            
            # 5. Fecha simple con "Fecha:" (pero no "Vencimiento")
            (r'Fecha[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{2,4})(?!\s*Venc)', 5),
            
            # 6. YYYY-MM-DD format
            (r'\b(\d{4}-\d{2}-\d{2})\b', 6),
            
            # 7. DD/MM/YYYY o DD-MM-YYYY (lowest priority)
            (r'\b(\d{2}[/-]\d{2}[/-]\d{2,4})\b', 7),
        ]
        
        for pattern, priority in patterns:
            matches = re.finditer(pattern, cleaned_text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(1).strip()
                
                logger.debug(f"Testing date candidate (priority {priority}): {date_str}")
                
                # Parse and normalize date
                try:
                    normalized_date = self._parse_and_normalize_date(date_str, spanish_months)
                    
                    if normalized_date:
                        # Validate year (reject dates before 2020 - old DGII resolutions)
                        year = int(normalized_date.split('-')[0])
                        if year < 2020:
                            logger.warning(f"Fecha rechazada (muy antigua): {date_str} -> {normalized_date}")
                            continue
                        
                        # Reject future dates (more than 1 year ahead)
                        if year > datetime.now().year + 1:
                            logger.warning(f"Fecha rechazada (muy futura): {date_str} -> {normalized_date}")
                            continue
                        
                        logger.info(f"✅ Fecha encontrada (priority {priority}): {normalized_date}")
                        return normalized_date
                        
                except Exception as e:
                    logger.debug(f"Error parsing date {date_str}: {e}")
                    continue
        
        logger.warning("❌ No se pudo extraer fecha de emisión")
        return None
    
    def _parse_and_normalize_date(self, date_str: str, spanish_months: dict) -> Optional[str]:
        """Parse various date formats and normalize to YYYY-MM-DD"""
        
        # Remove time portion if present (keep only date)
        date_only = re.split(r'\s+\d{1,2}:', date_str)[0]
        
        # Handle Spanish month names
        for month_name, month_num in spanish_months.items():
            if month_name in date_only.lower():
                # Replace month name with number and clean up
                # Pattern: DD/Month./YYYY or DD-Month-YYYY
                date_only = re.sub(
                    r'(\d{1,2})[/\-]' + month_name + r'\.?[/\-](\d{2,4})',
                    r'\1/' + month_num + r'/\2',
                    date_only,
                    flags=re.IGNORECASE
                )
                break
        
        # Clean up multiple slashes
        date_only = re.sub(r'/+', '/', date_only)
        
        # Split date parts
        if '/' in date_only or '-' in date_only:
            parts = re.split(r'[/-]', date_only)
            
            # Filter out empty parts
            parts = [p for p in parts if p]
            
            if len(parts) == 3:
                # Determine format
                if len(parts[0]) == 4:
                    # YYYY-MM-DD or YYYY/MM/DD
                    year, month, day = parts
                elif len(parts[2]) == 4:
                    # DD/MM/YYYY or DD-MM-YYYY
                    day, month, year = parts
                elif len(parts[2]) == 2:
                    # DD/MM/YY or DD-MM-YY
                    day, month, year = parts
                    # Convert 2-digit year to 4-digit
                    year_int = int(year)
                    if year_int >= 0 and year_int <= 50:
                        year = f"20{year}"
                    else:
                        year = f"19{year}"
                else:
                    return None
                
                # Normalize and validate
                normalized = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                datetime.strptime(normalized, '%Y-%m-%d')  # Validate
                return normalized
        
        return None
    
    def _extract_amounts(self, text: str) -> Montos:
        """
        Extract monetary amounts from invoice text
        
        IMPROVEMENTS:
        - Filters invoice numbers to avoid confusion with totals
        - Prioritizes RD$ over foreign currencies
        - Detects ITBIS in tables and rejects percentages
        - Supports ellipsis format in tables
        - Calculates missing subtotal when possible
        """
        montos = Montos()
        lines = text.split('\n')
        
        # STEP 1: Identify invoice numbers to avoid confusion with totals
        invoice_numbers = set()
        invoice_num_matches = re.findall(r'(?:Factura|Invoice)\s+No?\.?[:\s]+(\d+)', text, re.IGNORECASE)
        for num in invoice_num_matches:
            invoice_numbers.add(float(num))
            logger.debug(f"Identified invoice number to ignore: {num}")
        
        # STEP 2: Extract TOTAL (with filters for foreign currency and invoice numbers)
        # Prioritized patterns for TOTAL
        total_patterns = [
            # 1. TOTAL in RD$ (highest priority) - explicit currency
            # Use \b for word boundary to avoid matching "Subtotal"
            (r'\bTOTAL\s+en\s+RD\$\s*:\s*RD\$\s*([\d,\.]+)', 1),
            (r'\bTOTAL\s*[:\s]+RD\$\s*([\d,\.]+)', 1),
            (r'\bTOTAL\s*[:\s]+RD\s+([\d,\.]+)', 1),
            (r'\bTOTAL\s+A\s+PAGAR\s*[:\s]+(?:RD\$|RD)\s*([\d,\.]+)', 1),
            
            # 2. TOTAL with ellipsis (table format) - must not be Subtotal
            (r'(?<!Sub)Total\s*[.:]+\s*([\d,\.]+)', 2),
            
            # 3. NETO in RD$ (for gas stations)
            (r'NETO\s+en\s+RD\$\s*[:\s]*([\d,\.]+)', 3),
            
            # 4. T/Credito (simple invoices)
            (r'T[/\s]?Cr[ée]dito\s*[:\s]*([\d,\.]+)', 4),
            
            # 5. MONTO TOTAL
            (r'MONTO\s+TOTAL\s*[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)', 5),
            
            # 6. TOTAL without currency (lowest priority) - must not be followed by "en" for foreign currency
            (r'\bTOTAL\s*[:\s]+(?!en\s+(?:d[óo]lar|euro|USD|EUR))([\d,\.]+)', 6),
        ]
        
        # Patterns to explicitly ignore (foreign currencies)
        ignore_total_patterns = [
            r'Total\s+en\s+d[óo]lar',
            r'Total\s+en\s+euro',
            r'USD\s*[:\s]+[\d,\.]+',
            r'EUR\s*[:\s]+[\d,\.]+',
        ]
        
        for pattern, priority in total_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                total_str = match.group(1)
                
                # Check if this match is preceded by foreign currency indicator
                context_start = max(0, match.start() - 50)
                context = text[context_start:match.end()]
                skip = False
                for ignore_pattern in ignore_total_patterns:
                    if re.search(ignore_pattern, context, re.IGNORECASE):
                        logger.debug(f"Skipping total in foreign currency: {total_str}")
                        skip = True
                        break
                
                if skip:
                    continue
                
                # Clean and parse
                total_str = self._clean_amount(total_str)
                
                try:
                    total = float(total_str)
                    
                    # Validate: reject if it's an invoice number
                    if total in invoice_numbers:
                        logger.warning(f"Total rechazado (es número de factura): {total}")
                        continue
                    
                    # Validate: reject if unreasonably small or large
                    if total < 10 or total > 999999999:
                        logger.debug(f"Total rechazado (fuera de rango): {total}")
                        continue
                    
                    montos.total = total
                    logger.info(f"✅ Total encontrado (priority {priority}): RD${montos.total:,.2f}")
                    break
                except ValueError:
                    continue
            
            if montos.total:
                break
        
        # STEP 3: Extract SUBTOTAL (with table format support)
        subtotal_patterns = [
            r'SUBTOTAL\s*[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'Sub\s*Total\s*[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            
            # Table format with ellipsis
            r'Subtotal\s*[.:]+\s*([\d,\.]+)',
            
            # Alternative labels
            r'Monto\s+Gravado\s*[:\s]+([\d,\.]+)',
            r'Base\s+Imponible\s*[:\s]+([\d,\.]+)',
            r'Base\s*[:\s]+([\d,\.]+)',
        ]
        
        for pattern in subtotal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                subtotal_str = self._clean_amount(match.group(1))
                try:
                    montos.subtotal = float(subtotal_str)
                    logger.info(f"✅ Subtotal encontrado: RD${montos.subtotal:,.2f}")
                    break
                except ValueError:
                    continue
        
        # STEP 4: Extract ITBIS (with percentage rejection and table support)
        itbis_patterns = [
            # 1. With clear label and amount
            (r'ITBIS\s*[.:]+\s*(?:RD\$|RD|[$])?\s*([\d,\.]+)', 1),
            (r'Total\s+ITBIS\s*[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)', 1),
            
            # 2. With percentage in parentheses: ITBIS (18%): RD$228.81
            (r'ITBIS\s*\((?:18|16)%?\)\s*[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)', 2),
            
            # 3. With percentage BEFORE amount (capture amount, not percentage)
            (r'(?:18|16)%?\s*ITBIS\s*[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)', 3),
            (r'ITBIS\s+(?:18|16)%\s+(?:RD\$|RD)?\s*([\d,\.]+)', 3),
            
            # 4. In table with "Cuota" (separate from "Base")
            (r'(?:Cuota|ITBIS)(?:\s+\d{2}%)?\s*[:\s]+(?:RD\$|RD)?\s*([\d,\.]+)', 4),
            
            # 5. Table format with ellipsis
            (r'Itbis\s*[.:]+\s*([\d,\.]+)', 5),
            
            # 6. Generic tax/impuesto
            (r'(?:Impuesto|Tax)\s*[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)', 6),
        ]
        
        for pattern, priority in itbis_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                itbis_str = self._clean_amount(match.group(1))
                try:
                    itbis_candidate = float(itbis_str)
                    
                    # VALIDATION: Reject if it looks like a percentage
                    if itbis_candidate < 100:
                        # Check if this could be a percentage (typically 16-18)
                        if 15 <= itbis_candidate <= 20:
                            logger.warning(f"ITBIS rechazado (parece porcentaje): {itbis_candidate}")
                            continue
                        
                        # Check ratio to total (ITBIS shouldn't be more than 50% of total)
                        if montos.total and itbis_candidate / montos.total > 0.5:
                            logger.warning(f"ITBIS rechazado (ratio sospechoso vs total): {itbis_candidate}")
                            continue
                    
                    montos.itbis = itbis_candidate
                    logger.info(f"✅ ITBIS encontrado (priority {priority}): RD${montos.itbis:,.2f}")
                    break
                except ValueError:
                    continue
        
        # STEP 5: Try to extract ITBIS from product table if not found
        if not montos.itbis:
            table_itbis = self._extract_itbis_from_product_table(text)
            if table_itbis:
                montos.itbis = table_itbis
        
        # STEP 6: Calculate missing values
        # Calculate subtotal if missing: subtotal = total - itbis
        if not montos.subtotal and montos.total and montos.itbis:
            montos.subtotal = round(montos.total - montos.itbis, 2)
            logger.info(f"✅ Subtotal CALCULADO: RD${montos.subtotal:,.2f}")
        
        # Calculate ITBIS if missing: itbis = total - subtotal
        if not montos.itbis and montos.total and montos.subtotal:
            montos.itbis = round(montos.total - montos.subtotal, 2)
            logger.info(f"✅ ITBIS CALCULADO: RD${montos.itbis:,.2f}")
        
        return montos
    
    def _clean_amount(self, amount_str: str) -> str:
        """Clean amount string for parsing"""
        # Remove commas
        amount_str = amount_str.replace(',', '')
        
        # Handle European format (1.234.567,89 or 1.234,89)
        # If there are multiple dots and last group has 2 digits, it's likely decimal separator
        if amount_str.count('.') > 1:
            parts = amount_str.split('.')
            # Rejoin all but last, then add last with decimal point
            amount_str = ''.join(parts[:-1]) + '.' + parts[-1]
        
        return amount_str
    
    def _extract_itbis_from_product_table(self, text: str) -> Optional[float]:
        """
        Sum ITBIS from individual product lines if total ITBIS not found
        
        Typical table format:
        PRODUCTO    CANTIDAD    PRECIO    ITBIS    TOTAL
        Item 1      1           100.00    18.00    118.00
        """
        lines = text.split('\n')
        itbis_sum = 0.0
        found_items = 0
        
        for line in lines:
            # Look for lines with ITBIS values in table format
            # Pattern: multiple numbers with likely ITBIS value
            # Common indicators: "E" followed by numbers (tax code)
            match = re.search(r'([\d,\.]+)\s+([\d,\.]+)\s+([EI]\d{0,2})', line)
            if match:
                # Second number is likely ITBIS
                try:
                    itbis_item = float(self._clean_amount(match.group(2)))
                    # Sanity check: ITBIS per item should be reasonable
                    if 0.01 < itbis_item < 10000:
                        itbis_sum += itbis_item
                        found_items += 1
                except ValueError:
                    continue
        
        if found_items > 0:
            logger.info(f"✅ ITBIS calculado desde {found_items} productos: RD${itbis_sum:,.2f}")
            return itbis_sum
        
        return None
    
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