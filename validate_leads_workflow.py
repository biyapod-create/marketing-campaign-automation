#!/usr/bin/env python3
"""
Lead Validation Workflow - Automated lead screening
Validates emails and filters to only high-quality prospects
"""

import csv
import sys
from email_validator import EmailValidator

def validate_and_filter_leads(input_csv: str, output_csv: str = None, 
                               min_confidence: str = 'medium', 
                               check_smtp: bool = False):
    """
    Validate leads from CSV and create filtered output
    
    Args:
        input_csv: Path to input CSV with leads
        output_csv: Path for filtered output (default: input_validated_filtered.csv)
        min_confidence: Minimum confidence level (low/medium/high)
        check_smtp: Enable SMTP verification
    """
    
    if output_csv is None:
        output_csv = input_csv.replace('.csv', '_validated_filtered.csv')
    
    validator = EmailValidator()
    
    print("="*70)
    print("LEAD VALIDATION & FILTERING WORKFLOW")
    print("="*70)
    print(f"Input:           {input_csv}")
    print(f"Output:          {output_csv}")
    print(f"Min confidence:  {min_confidence}")
    print(f"SMTP check:      {'ON' if check_smtp else 'OFF'}")
    print("="*70)
    print()
    
    # Read leads
    leads = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames) if reader.fieldnames else []
        if not fieldnames:
            print("[ERROR] CSV file is empty or has no headers.")
            return
        for row in reader:
            leads.append(row)
    
    print(f"Loaded {len(leads)} leads from CSV")
    print()
    
    # Validate emails
    confidence_priority = {'high': 3, 'medium': 2, 'low': 1}
    min_score = confidence_priority[min_confidence]
    
    valid_leads = []
    invalid_leads = []
    
    for i, lead in enumerate(leads, 1):
        email = lead.get('email', '').strip()
        
        if not email:
            print(f"{i}/{len(leads)}: {lead.get('name', 'Unknown')} - SKIP (no email)")
            invalid_leads.append({**lead, 'validation_status': 'no_email'})
            continue
        
        # Validate
        result = validator.validate_email(email, check_smtp=check_smtp)
        
        # Check confidence threshold
        if result.valid and confidence_priority.get(result.confidence, 0) >= min_score:
            print(f"{i}/{len(leads)}: {email} - [OK] {result.confidence.upper()}")
            valid_leads.append({
                **lead, 
                'validation_status': f'valid_{result.confidence}',
                'validation_details': result.details
            })
        else:
            print(f"{i}/{len(leads)}: {email} - [FAIL] {result.confidence.upper()} - {result.details}")
            invalid_leads.append({
                **lead, 
                'validation_status': f'invalid_{result.confidence}',
                'validation_details': result.details
            })
    
    print()
    print("="*70)
    print("FILTERING RESULTS")
    print("="*70)
    print(f"Total leads:     {len(leads)}")
    print(f"Valid leads:     {len(valid_leads)} ({len(valid_leads)/len(leads)*100:.1f}%)")
    print(f"Invalid/skipped: {len(invalid_leads)} ({len(invalid_leads)/len(leads)*100:.1f}%)")
    print("="*70)
    print()
    
    # Write filtered output
    if valid_leads:
        # Add validation fields to fieldnames
        output_fieldnames = fieldnames + ['validation_status', 'validation_details']
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=output_fieldnames)
            writer.writeheader()
            writer.writerows(valid_leads)
        
        print(f"[OK] {len(valid_leads)} validated leads written to: {output_csv}")
    else:
        print("[WARN] No valid leads found - no output file created")
    
    # Write rejected leads to separate file
    rejected_csv = input_csv.replace('.csv', '_rejected.csv')
    if invalid_leads:
        output_fieldnames = fieldnames + ['validation_status', 'validation_details']
        
        with open(rejected_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=output_fieldnames)
            writer.writeheader()
            writer.writerows(invalid_leads)
        
        print(f"[INFO] {len(invalid_leads)} rejected leads written to: {rejected_csv}")
    
    print()
    print("="*70)
    print("NEXT STEPS")
    print("="*70)
    print(f"1. Review validated leads: {output_csv}")
    print(f"2. Import to lead database")
    print(f"3. Generate personalized emails")
    print(f"4. Send campaign")
    print("="*70)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python validate_leads_workflow.py <input.csv> [--high|--medium|--low] [--smtp]")
        print()
        print("Examples:")
        print("  python validate_leads_workflow.py leads.csv")
        print("  python validate_leads_workflow.py leads.csv --high")
        print("  python validate_leads_workflow.py leads.csv --medium --smtp")
        print()
        print("Options:")
        print("  --high     Only accept high confidence emails (SMTP verified)")
        print("  --medium   Accept medium and high confidence (default)")
        print("  --low      Accept all valid emails")
        print("  --smtp     Enable SMTP verification (slower)")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    
    # Parse options
    min_confidence = 'medium'  # default
    if '--high' in sys.argv:
        min_confidence = 'high'
    elif '--low' in sys.argv:
        min_confidence = 'low'
    
    check_smtp = '--smtp' in sys.argv
    
    validate_and_filter_leads(input_csv, min_confidence=min_confidence, check_smtp=check_smtp)
