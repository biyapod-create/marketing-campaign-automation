#!/usr/bin/env python3
"""
Email Validator & Verification System
Prevents bounce rates by validating emails before sending
"""

import re
import dns.resolver
import socket
import smtplib
import csv
import json
from typing import Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class EmailValidation:
    email: str
    valid: bool
    confidence: str  # high, medium, low
    syntax_valid: bool
    domain_exists: bool
    mx_records_found: bool
    smtp_verified: bool
    details: str
    validated_at: str

class EmailValidator:
    """
    Multi-layer email validation system
    """
    
    def __init__(self):
        self.email_regex = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
    def validate_syntax(self, email: str) -> bool:
        """Check if email matches valid format"""
        return bool(self.email_regex.match(email))
    
    def check_domain_mx(self, domain: str) -> Tuple[bool, List[str]]:
        """Check if domain has MX records configured"""
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_hosts = [str(r.exchange) for r in mx_records]
            return True, mx_hosts
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
            return False, []
        except Exception as e:
            return False, []
    
    def verify_smtp(self, email: str, mx_host: str) -> Tuple[bool, str]:
        """
        Attempt SMTP verification (optional - can be blocked by servers)
        This is conservative - only marks as invalid if definitively rejected
        Returns (True/False/None, detail_string). None means inconclusive.
        """
        try:
            # Connect to mail server
            server = smtplib.SMTP(timeout=10)
            server.connect(mx_host)
            server.helo('allennetic.com')
            server.mail('info@allennetic.com')
            code, message = server.rcpt(email)
            server.quit()
            
            # 250 = accepted, 251 = user not local (forwarding)
            if code in [250, 251]:
                return True, f"SMTP accepted (code {code})"
            else:
                return False, f"SMTP rejected (code {code})"
                
        except smtplib.SMTPServerDisconnected:
            return None, "SMTP verification unavailable"
        except smtplib.SMTPConnectError:
            return None, "Could not connect to mail server"
        except Exception as e:
            return None, f"SMTP check failed: {str(e)[:50]}"
    
    def validate_email(self, email: str, check_smtp: bool = False) -> EmailValidation:
        """
        Complete email validation with confidence scoring
        
        Confidence levels:
        - HIGH: Syntax valid + MX records found + (SMTP verified OR skipped)
        - MEDIUM: Syntax valid + MX records found + SMTP inconclusive
        - LOW: Syntax valid only OR any check failed
        """
        email = email.strip().lower()
        
        # Step 1: Syntax validation
        syntax_valid = self.validate_syntax(email)
        if not syntax_valid:
            return EmailValidation(
                email=email,
                valid=False,
                confidence="low",
                syntax_valid=False,
                domain_exists=False,
                mx_records_found=False,
                smtp_verified=False,
                details="Invalid email format",
                validated_at=datetime.now().isoformat()
            )
        
        # Step 2: Extract domain and check MX records
        domain = email.split('@')[1]
        mx_found, mx_hosts = self.check_domain_mx(domain)
        
        if not mx_found:
            return EmailValidation(
                email=email,
                valid=False,
                confidence="low",
                syntax_valid=True,
                domain_exists=False,
                mx_records_found=False,
                smtp_verified=False,
                details=f"No MX records for domain {domain}",
                validated_at=datetime.now().isoformat()
            )
        
        # Step 3: Optional SMTP verification
        smtp_result = None
        smtp_details = "SMTP check skipped"
        
        if check_smtp and mx_hosts:
            # Try first MX host
            smtp_result, smtp_details = self.verify_smtp(email, mx_hosts[0])
        
        # Determine final confidence
        if smtp_result is True:
            confidence = "high"
            valid = True
            details = f"Fully verified via SMTP on {mx_hosts[0]}"
        elif smtp_result is False:
            confidence = "low"
            valid = False
            details = smtp_details
        else:
            # SMTP inconclusive or skipped
            confidence = "medium"
            valid = True
            details = f"MX records found ({len(mx_hosts)} servers). {smtp_details}"
        
        return EmailValidation(
            email=email,
            valid=valid,
            confidence=confidence,
            syntax_valid=True,
            domain_exists=True,
            mx_records_found=True,
            smtp_verified=(smtp_result is True),
            details=details,
            validated_at=datetime.now().isoformat()
        )
    
    def validate_batch(self, emails: List[str], check_smtp: bool = False) -> List[EmailValidation]:
        """Validate multiple emails"""
        results = []
        total = len(emails)
        
        for i, email in enumerate(emails, 1):
            print(f"Validating {i}/{total}: {email}")
            result = self.validate_email(email, check_smtp=check_smtp)
            results.append(result)
            
            # Print immediate feedback
            status = "[OK]" if result.valid else "[FAIL]"
            print(f"  {status} {result.confidence.upper()} - {result.details}\n")
        
        return results
    
    def validate_from_csv(self, csv_path: str, email_column: str = 'email', 
                         check_smtp: bool = False) -> Tuple[List[EmailValidation], Dict]:
        """
        Validate emails from CSV file
        Returns results and summary stats
        """
        emails = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if email_column in row and row[email_column]:
                    emails.append(row[email_column])
        
        results = self.validate_batch(emails, check_smtp=check_smtp)
        
        # Calculate summary
        summary = {
            'total': len(results),
            'valid': sum(1 for r in results if r.valid),
            'invalid': sum(1 for r in results if not r.valid),
            'high_confidence': sum(1 for r in results if r.confidence == 'high'),
            'medium_confidence': sum(1 for r in results if r.confidence == 'medium'),
            'low_confidence': sum(1 for r in results if r.confidence == 'low'),
            'syntax_failures': sum(1 for r in results if not r.syntax_valid),
            'mx_failures': sum(1 for r in results if r.syntax_valid and not r.mx_records_found),
            'smtp_verified': sum(1 for r in results if r.smtp_verified)
        }
        
        return results, summary
    
    def export_results(self, results: List[EmailValidation], output_path: str):
        """Export validation results to CSV"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            if not results:
                return
            
            fieldnames = list(asdict(results[0]).keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                writer.writerow(asdict(result))
        
        print(f"[OK] Results exported to {output_path}")


def main():
    """CLI interface for email validation"""
    import sys
    
    validator = EmailValidator()
    
    print("="*70)
    print("EMAIL VALIDATOR - Allennetic Marketing System")
    print("="*70)
    print()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single email:  python email_validator.py <email>")
        print("  Batch CSV:     python email_validator.py <csv_file> [--smtp]")
        print("  Multiple:      python email_validator.py email1 email2 email3")
        print()
        print("Options:")
        print("  --smtp         Enable SMTP verification (slower, more thorough)")
        print()
        return
    
    check_smtp = '--smtp' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--smtp']
    
    # Check if first arg is a CSV file
    if len(args) == 1 and args[0].endswith('.csv'):
        csv_path = args[0]
        print(f"Validating emails from: {csv_path}")
        print(f"SMTP verification: {'ON' if check_smtp else 'OFF'}")
        print("="*70)
        print()
        
        results, summary = validator.validate_from_csv(csv_path, check_smtp=check_smtp)
        
        # Print summary
        print("="*70)
        print("VALIDATION SUMMARY")
        print("="*70)
        print(f"Total emails:        {summary['total']}")
        print(f"Valid:               {summary['valid']} ({summary['valid']/summary['total']*100:.1f}%)")
        print(f"Invalid:             {summary['invalid']} ({summary['invalid']/summary['total']*100:.1f}%)")
        print()
        print(f"High confidence:     {summary['high_confidence']}")
        print(f"Medium confidence:   {summary['medium_confidence']}")
        print(f"Low confidence:      {summary['low_confidence']}")
        print()
        print(f"Syntax failures:     {summary['syntax_failures']}")
        print(f"MX record failures:  {summary['mx_failures']}")
        if check_smtp:
            print(f"SMTP verified:       {summary['smtp_verified']}")
        print("="*70)
        
        # Export results
        output_path = csv_path.replace('.csv', '_validated.csv')
        validator.export_results(results, output_path)
        
    else:
        # Validate individual emails
        results = validator.validate_batch(args, check_smtp=check_smtp)
        
        # Print summary
        valid_count = sum(1 for r in results if r.valid)
        print("="*70)
        print(f"RESULTS: {valid_count}/{len(results)} valid")
        print("="*70)


if __name__ == '__main__':
    main()
