# Email Validator - Quick Start Guide

## System Reset Complete ✓

**Database:** Cleared (0 leads, 0 emails, 0 tasks)
**CSV Files:** Reset to headers only
**Campaign:** Ready for fresh start

---

## Email Validator Usage

### Why This Matters
71% bounce rate on last campaign = deliverability crisis.
This validator prevents that by checking emails BEFORE sending.

### Validation Levels

**HIGH Confidence** - Syntax valid + MX records + SMTP verified
**MEDIUM Confidence** - Syntax valid + MX records (no SMTP check)
**LOW Confidence** - Syntax issues or no MX records

---

## Usage Examples

### 1. Validate Single Email
```bash
python email_validator.py info@allennetic.com
```

### 2. Validate Multiple Emails
```bash
python email_validator.py email1@domain.com email2@domain.com email3@domain.com
```

### 3. Validate from CSV File
```bash
python email_validator.py leads/leads_database.csv
```

### 4. Deep Validation with SMTP (slower but thorough)
```bash
python email_validator.py leads/leads_database.csv --smtp
```

---

## CSV Validation Workflow

**Input:** CSV file with 'email' column
**Output:** `filename_validated.csv` with full results

Example output columns:
- email
- valid (True/False)
- confidence (high/medium/low)
- syntax_valid
- domain_exists
- mx_records_found
- smtp_verified
- details
- validated_at

---

## Recommended Workflow

### Before Adding Leads:
1. Get leads from source (LinkedIn, Vconnect, etc.)
2. Export to CSV with email column
3. Run: `python email_validator.py leads.csv`
4. Review `leads_validated.csv`
5. Only import HIGH + MEDIUM confidence emails

### Email Construction Patterns to Avoid:
Based on last campaign failures:

❌ firstname@domain.com (10/17 bounced)
❌ firstname.lastname@domain.com (if unverified)

✓ Use Apollo.io enrichment
✓ Use Hunter.io verification
✓ Use validator before sending

---

## Integration with Lead System

### Option 1: Manual Filter
```bash
python email_validator.py new_leads.csv
# Review new_leads_validated.csv
# Import only valid=True rows
```

### Option 2: Automated Pipeline
```python
from email_validator import EmailValidator

validator = EmailValidator()

# Validate before adding to database
result = validator.validate_email('prospect@company.com')

if result.valid and result.confidence in ['high', 'medium']:
    # Add to lead database
    pass
else:
    # Skip or flag for manual review
    print(f"Skipping: {result.details}")
```

---

## Performance Notes

**Without --smtp flag:**
- Speed: ~1-2 seconds per email
- Accuracy: Catches syntax errors + dead domains
- Use for: Bulk screening (100+ emails)

**With --smtp flag:**
- Speed: ~5-10 seconds per email
- Accuracy: Highest (verifies mailbox exists)
- Use for: High-value prospects only
- Note: Some servers block SMTP verification

---

## Next Steps

1. **Source Fresh Leads**
   - LinkedIn Sales Navigator
   - Vconnect directory
   - Google Maps scraping
   - CAC registrations

2. **Validate Before Import**
   - Run validator on all new leads
   - Filter to HIGH + MEDIUM confidence only
   - Save validation results for reference

3. **Campaign Execution**
   - Only send to validated emails
   - Monitor bounce rate (target: <5%)
   - Use follow-up sequence for non-responders

---

## Files Created

- `email_validator.py` - Core validation system
- `requirements.txt` - Dependencies (dnspython)
- This guide - Usage instructions

## Dependencies Installed

- dnspython >= 2.4.0 ✓

---

## Campaign Status

**Current State:** Clean slate
**Deliverability:** Protected by validation system
**Ready for:** Fresh lead intake with verification
