def _extract_amounts(self, text):
    amounts = {}
    # Define patterns to search for
    total_pattern = r'TOTAL PESOS\s*?([\d,.]+)'
    subtotal_pattern = r'BASE\s*?([\d,.]+)'
    itbis_pattern = r'CUOTA\s*?([\d,.]+)'
    legal_tip_pattern = r'(?:(10% de ley|PROPINA|TIP)[\s:]*(\d+\.?\d*)?)'

    # Extract totals, subtotal, and ITBIS with validation
    total_match = re.search(total_pattern, text)
    if total_match:
        amounts['total'] = float(total_match.group(1).replace(',', ''))
    
    subtotal_match = re.search(subtotal_pattern, text)
    if subtotal_match:
        amounts['subtotal'] = float(subtotal_match.group(1).replace(',', ''))
    
    itbis_match = re.search(itbis_pattern, text)
    if itbis_match:
        itbis_amount = float(itbis_match.group(1).replace(',', ''))
        # Validate ITBIS
        if abs(itbis_amount - amounts.get('total', 0)) > 0.01:
            amounts['itbis'] = itbis_amount

    # Detect legal tips
    legal_tip_match = re.search(legal_tip_pattern, text)
    if legal_tip_match:
        amounts['legal_tip'] = legal_tip_match.group(1)

    # Calculate missing fields if necessary
    if 'subtotal' not in amounts and 'total' in amounts:
        amounts['subtotal'] = amounts['total'] * 0.9  # Assuming 10% for legal tips
    
    return amounts
