    def _extract_amounts(self, text: str, lines: List[str]) -> Montos:
        """
        Extracción MEJORADA de montos con patrones avanzados
        
        FIXES:
        - No confunde ITBIS con Total
        - Detecta propina legal (10% de ley)
        - Mejor detección de múltiples monedas
        - Validación de montos antes de asignarlos
        
        Estrategias:
        1. TOTAL primero (prioridad máxima)
        2. SUBTOTAL
        3. ITBIS (con validación vs Total)
        4. PROPINA LEGAL
        5. Calcular campos faltantes
        """
        montos = Montos()
        
        # ==========================================
        # PASO 1: EXTRAER TOTAL (PRIORIDAD MÁXIMA)
        # ==========================================
        total_patterns = [
            r'TOTAL\s+PESOS[:\s]*(?:RD\$|[$])?\s*([\d,\.]+)',  # "TOTAL PESOS"
            r'TOTAL\s+A\s+PAGAR[:\s]*(?:RD\$|[$])?\s*([\d,\.]+)',  # "TOTAL A PAGAR"
            r'TOTAL[:\s]+(?:RD\$|RD|[$]|DOP)?\s*([\d,\.]+)',  # "TOTAL: 1234.56"
            r'(?:^|\n)TOTAL\s+([\d,\.]+)',  # "TOTAL 1234.56"
        ]
        
        for pattern in total_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                try:
                    amount = self._parse_amount(match)
                    if amount > 10:  # Sanity check
                        logger.success(f"✅ Total encontrado: RD${{amount:,.2f}}")
                        montos.total = amount
                        break
                except:
                    continue
            if montos.total:
                break
        
        # Fallback: Buscar TOTAL en múltiples líneas
        if not montos.total:
            for i, line in enumerate(lines):
                if re.search(r'\bTOTAL\b', line, re.IGNORECASE):
                    # Buscar monto en las siguientes 3 líneas
                    for j in range(i, min(i + 4, len(lines))):
                        next_line = lines[j]
                        amount_match = re.search(r'(?:RD\$|RD|[$]|DOP)?\s*([\d,\.]+)', next_line)
                        if amount_match:
                            try:
                                amount = self._parse_amount(amount_match.group(1))
                                if amount > 10:
                                    # VALIDACIÓN: No debe ser un número de línea o cantidad pequeña
                                    if amount > 50:  # Total razonable
                                        logger.success(f"✅ Total (multiline): RD${{amount:,.2f}}")
                                        montos.total = amount
                                        break
                            except:
                                continue
                    if montos.total:
                        break
        
        # ==========================================
        # PASO 2: EXTRAER SUBTOTAL
        # ==========================================
        subtotal_patterns = [
            r'SUBTOTAL[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'Sub\s*Total[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'BASE[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',  # Algunos usan "BASE"
        ]
        
        for pattern in subtotal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount = self._parse_amount(match.group(1))
                    # VALIDACIÓN: Subtotal debe ser menor que Total
                    if montos.total and amount >= montos.total:
                        logger.warning(f"⚠️ Subtotal ({{amount}}) >= Total ({{montos.total}}), descartando")
                        continue
                    montos.subtotal = amount
                    logger.success(f"✅ Subtotal encontrado: RD${{montos.subtotal:,.2f}}")
                    break
                except ValueError:
                    continue
        
        # ==========================================
        # PASO 3: EXTRAER ITBIS (CON VALIDACIÓN)
        # ==========================================
        itbis_patterns = [
            r'(?:TOTAL\s+)?ITBIS[:\s\(]*(?:\d+%\))?[:\s]*(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'(?:18|16)%?\s*ITBIS[:\s]*(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'(?:IMPUESTO|TAX|CUOTA)[:\s]+(?:RD\$|RD|[$])?\s*([\d,\.]+)',
            r'Total\s+de\s+Impuestos[:\s]*(?:RD\$|[$])?\s*([\d,\.]+)',
        ]
        
        for pattern in itbis_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    itbis_candidate = self._parse_amount(match.group(1))
                    
                    # ⚠️ VALIDACIÓN CRÍTICA: ITBIS NO PUEDE SER IGUAL AL TOTAL
                    if montos.total and abs(itbis_candidate - montos.total) < 1.0:
                        logger.warning(f"⚠️ ITBIS ({{itbis_candidate}}) muy cercano a Total ({{montos.total}}), DESCARTANDO")
                        continue
                    
                    # VALIDACIÓN: ITBIS debe ser razonable (10-20% del subtotal si existe)
                    if montos.subtotal:
                        expected_itbis_range = (montos.subtotal * 0.10, montos.subtotal * 0.20)
                        if not (expected_itbis_range[0] <= itbis_candidate <= expected_itbis_range[1] * 1.5):
                            logger.warning(f"⚠️ ITBIS ({{itbis_candidate}}) fuera de rango esperado {{expected_itbis_range}}")
                            continue
                    
                    # VALIDACIÓN: ITBIS debe ser menor que Total
                    if montos.total and itbis_candidate >= montos.total:
                        logger.warning(f"⚠️ ITBIS ({{itbis_candidate}}) >= Total ({{montos.total}}), descartando")
                        continue
                    
                    montos.itbis = itbis_candidate
                    logger.success(f"✅ ITBIS encontrado: RD${{montos.itbis:,.2f}}")
                    break
                except ValueError:
                    continue
        
        # ==========================================
        # PASO 4: EXTRAER PROPINA LEGAL (10% de ley)
        # ==========================================
        propina_patterns = [
            r'(?:10%\s*de\s*ley)[:\s]*(?:RD\$|[$])?\s*([\d,\.]+)',
            r'PROPINA[:\s]+(?:RD\$|[$])?\s*([\d,\.]+)',
            r'TIP[:\s]+(?:RD\$|[$])?\s*([\d,\.]+)',
        ]
        
        for pattern in propina_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    propina_candidate = self._parse_amount(match.group(1))
                    # Validar que sea razonable (típicamente 10% del subtotal)
                    if montos.subtotal:
                        expected_propina = montos.subtotal * 0.10
                        if abs(propina_candidate - expected_propina) / expected_propina < 0.2:  # ±20%
                            montos.propina = propina_candidate
                            logger.success(f"✅ Propina legal encontrada: RD${{montos.propina:,.2f}}")
                            break
                    else:
                        montos.propina = propina_candidate
                        logger.success(f"✅ Propina encontrada: RD${{montos.propina:,.2f}}")
                        break
                except ValueError:
                    continue
        
        # ==========================================
        # PASO 5: CALCULAR CAMPOS FALTANTES
        # ==========================================
        if montos.total and montos.itbis and not montos.subtotal:
            # Calcular: Subtotal = Total - ITBIS - Propina
            montos.subtotal = montos.total - montos.itbis
            if montos.propina:
                montos.subtotal -= montos.propina
            logger.info(f"💡 Subtotal calculado: RD${{montos.subtotal:,.2f}}")
        
        if montos.subtotal and montos.total and not montos.itbis:
            # Calcular: ITBIS = Total - Subtotal - Propina
            montos.itbis = montos.total - montos.subtotal
            if montos.propina:
                montos.itbis -= montos.propina
            logger.info(f"💡 ITBIS calculado: RD${{montos.itbis:,.2f}}")
        
        # ==========================================
        # PASO 6: FALLBACK - Mayor monto (SOLO SI NO HAY TOTAL)
        # ==========================================
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
                logger.warning(f"⚠️ Total por fallback (mayor monto): RD${{max_amount:,.2f}}")
                montos.total = max_amount
        
        return montos
