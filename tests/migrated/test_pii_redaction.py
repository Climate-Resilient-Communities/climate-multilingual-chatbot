#!/usr/bin/env python3
"""
Test script for PII redaction functionality.
Tests various PII patterns to ensure they are properly redacted.
"""

import re
import sys

def redact_pii(text: str) -> str:
    """
    Redact personally identifiable information from text.
    
    This function identifies and replaces common PII patterns with redacted placeholders.
    Patterns include: emails, phone numbers, credit cards, SSNs, names, addresses, etc.
    """
    if not text or not isinstance(text, str):
        return text
    
    # Email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
    
    # Credit card numbers (16, 15, 14, or 13 digits with optional spaces/dashes) - Check FIRST before phone numbers
    text = re.sub(r'\b(?:\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}|\d{4}[-\s]?\d{6}[-\s]?\d{5}|\d{4}[-\s]?\d{6}[-\s]?\d{4}|\d{4}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{3})\b', '[CREDIT_CARD_REDACTED]', text)
    
    # Phone numbers (various formats) - Check AFTER credit cards to avoid conflicts
    # US formats: (123) 456-7890, 123-456-7890, 123.456.7890, 123 456 7890, +1 123 456 7890
    phone_patterns = [
        r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',  # US phone numbers
        r'\b\d{3}-\d{3}-\d{4}\b',  # XXX-XXX-XXXX
        r'\b\d{3}\.\d{3}\.\d{4}\b',  # XXX.XXX.XXXX  
        r'\(\d{3}\)\s?\d{3}-\d{4}',  # (XXX) XXX-XXXX
        r'\b(?<!\d)\d{10}(?!\d)\b',  # 10 consecutive digits not part of longer number
    ]
    for pattern in phone_patterns:
        text = re.sub(pattern, '[PHONE_REDACTED]', text)
    
    # Social Security Numbers (XXX-XX-XXXX or 9 consecutive digits)
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
    text = re.sub(r'\b(?<!\d)\d{9}(?!\d)\b', '[SSN_REDACTED]', text)  # 9 digits not part of longer number
    
    # IP addresses
    text = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP_REDACTED]', text)
    
    # Common name patterns (basic - catches "My name is X" or "I'm X")
    text = re.sub(r'\b(?:my name is|i\'?m|call me)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b', r'my name is [NAME_REDACTED]', text, flags=re.IGNORECASE)
    
    # Address patterns (basic street addresses)
    text = re.sub(r'\b\d+\s+[A-Za-z\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|way|court|ct|place|pl)\b', '[ADDRESS_REDACTED]', text, flags=re.IGNORECASE)
    
    # Date of birth patterns (MM/DD/YYYY, MM-DD-YYYY, YYYY/MM/DD, YYYY-MM-DD)
    text = re.sub(r'\b(?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])[-/](?:19|20)\d{2}\b', '[DOB_REDACTED]', text)
    text = re.sub(r'\b(?:19|20)\d{2}[-/](?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])\b', '[DOB_REDACTED]', text)
    
    # Government ID patterns (basic - alphanumeric IDs)
    text = re.sub(r'\b[A-Z]{1,2}\d{6,8}\b', '[ID_REDACTED]', text)
    
    # Bank account patterns (8-17 digits, but be careful not to redact legitimate numbers)
    text = re.sub(r'\b(?:account|acct)[\s#:]*(\d{8,17})\b', r'account [ACCOUNT_REDACTED]', text, flags=re.IGNORECASE)
    
    # License plate patterns (basic - 2-3 letters followed by 3-4 numbers)
    text = re.sub(r'\b[A-Z]{2,3}[-\s]?[0-9]{3,4}\b', '[LICENSE_PLATE_REDACTED]', text)
    
    return text

def test_pii_redaction():
    """Test various PII patterns to ensure proper redaction."""
    print("🔒 Testing PII Redaction Functionality")
    print("=" * 50)
    
    # Test cases: (input, expected_pattern_in_output)
    test_cases = [
        # Email addresses
        ("Contact me at john.doe@example.com for more info", "[EMAIL_REDACTED]"),
        ("My emails are test@gmail.com and work@company.org", "[EMAIL_REDACTED]"),
        
        # Phone numbers
        ("Call me at (555) 123-4567", "[PHONE_REDACTED]"),
        ("My number is 555-123-4567 or 555.123.4567", "[PHONE_REDACTED]"),
        ("You can reach me at +1 555 123 4567", "[PHONE_REDACTED]"),
        ("Phone: 5551234567", "[PHONE_REDACTED]"),
        
        # Credit cards
        ("My card number is 4532 1234 5678 9012", "[CREDIT_CARD_REDACTED]"),
        ("Card: 4532123456789012", "[CREDIT_CARD_REDACTED]"),
        
        # SSN
        ("My SSN is 123-45-6789", "[SSN_REDACTED]"),
        ("SSN: 123456789", "[SSN_REDACTED]"),
        
        # Names
        ("My name is John Smith", "[NAME_REDACTED]"),
        ("I'm Jane Doe", "[NAME_REDACTED]"),
        ("Call me Michael Johnson", "[NAME_REDACTED]"),
        
        # Addresses
        ("I live at 123 Main Street", "[ADDRESS_REDACTED]"),
        ("Address: 456 Oak Avenue", "[ADDRESS_REDACTED]"),
        
        # Dates
        ("Born on 12/25/1990", "[DOB_REDACTED]"),
        ("DOB: 1990-12-25", "[DOB_REDACTED]"),
        
        # IP addresses  
        ("My IP is 192.168.1.1", "[IP_REDACTED]"),
        
        # Account numbers (13+ digits may be treated as credit cards for safety)
        ("My account 12345678", "[ACCOUNT_REDACTED]"),
        
        # License plates
        ("My car is ABC 123", "[LICENSE_PLATE_REDACTED]"),
        
        # Mixed PII
        ("Hi, I'm John Smith, email john@test.com, phone (555) 123-4567, SSN 123-45-6789", 
         "[NAME_REDACTED]" and "[EMAIL_REDACTED]" and "[PHONE_REDACTED]" and "[SSN_REDACTED]"),
    ]
    
    passed = 0
    failed = 0
    
    for i, (input_text, expected_pattern) in enumerate(test_cases, 1):
        result = redact_pii(input_text)
        
        # Check if expected pattern is in result
        if isinstance(expected_pattern, str):
            pattern_found = expected_pattern in result
        else:
            # For boolean expressions (like multiple patterns)
            pattern_found = eval(expected_pattern.replace("and", "and").replace("or", "or"))
            
        status = "✅ PASS" if pattern_found else "❌ FAIL"
        
        print(f"\nTest {i}: {status}")
        print(f"Input:    {input_text}")
        print(f"Output:   {result}")
        print(f"Expected: {expected_pattern}")
        
        if pattern_found:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All PII redaction tests PASSED!")
        return True
    else:
        print("⚠️  Some PII redaction tests FAILED!")
        return False

if __name__ == "__main__":
    success = test_pii_redaction()
    sys.exit(0 if success else 1)
