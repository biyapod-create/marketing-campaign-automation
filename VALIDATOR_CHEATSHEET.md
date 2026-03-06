# Email Validator - Quick Reference Card

## 🎯 Purpose
Prevent 71% bounce rate by validating emails BEFORE sending

## ⚡ Quick Commands

### Validate Single Email
```bash
python email_validator.py info@allennetic.com
```

### Validate Multiple
```bash
python email_validator.py email1@domain.com email2@domain.com email3@domain.com
```

### Validate from CSV
```bash
python validate_leads_workflow.py leads.csv
```

### High Confidence Only (with SMTP)
```bash
python validate_leads_workflow.py leads.csv --high --smtp
```

---

## 📊 Confidence Levels

| Level | Meaning | Action |
|-------|---------|--------|
| **HIGH** | SMTP verified + MX records | ✓ Send |
| **MEDIUM** | MX records found | ✓ Send |
| **LOW** | Failed checks | ✗ Skip |

---

## 🔄 Standard Workflow

1. **Get leads** → LinkedIn, Vconnect, Google Maps
2. **Export to CSV** → Include 'email' column
3. **Validate** → `python validate_leads_workflow.py leads.csv`
4. **Review** → Check `leads_validated_filtered.csv`
5. **Import** → Only validated leads to database
6. **Send** → Generate + send campaign

---

## 📁 Output Files

**Input:** `leads.csv`

**Outputs:**
- `leads_validated_filtered.csv` - Valid leads only
- `leads_rejected.csv` - Invalid/low confidence
- Both include validation status + details

---

## ⚙️ Options

| Flag | Effect |
|------|--------|
| `--high` | Only HIGH confidence emails |
| `--medium` | MEDIUM + HIGH (default) |
| `--low` | All valid emails |
| `--smtp` | Enable SMTP verification (slower) |

---

## 🚨 Red Flags from Last Campaign

❌ firstname@domain.com patterns
❌ No MX record verification  
❌ No pre-send validation

**Result:** 71% bounce rate (12/17 emails)

---

## ✅ New Standard

✓ Every email validated before import
✓ MX records verified
✓ Confidence scoring enforced
✓ Target: <5% bounce rate

---

## 📍 Files Location

`C:\Users\Allen\Desktop\Marketing Campaign\`

- `email_validator.py` - Core engine
- `validate_leads_workflow.py` - Automation
- `EMAIL_VALIDATOR_GUIDE.md` - Full docs
- `RESET_COMPLETE_README.md` - System overview

---

## 💡 Pro Tips

1. **LinkedIn exports** → Usually high quality, still validate
2. **Manual construction** → firstname@domain fails often, use Apollo
3. **Batch processing** → Validate in bulk, save time
4. **SMTP flag** → Use for VIP prospects only (slow)
5. **Review rejects** → Sometimes fixable (typos, wrong domain)

---

## 🎬 Example Session

```bash
# Get 50 leads from LinkedIn Sales Navigator
# Export to linkedin_prospects.csv

# Validate
python validate_leads_workflow.py linkedin_prospects.csv --medium

# Results
# Total: 50
# Valid (HIGH): 12
# Valid (MEDIUM): 26
# Invalid: 12

# Import 38 validated leads
# Generate personalized emails
# Send campaign with <5% bounce rate
```

---

**Questions?** Read EMAIL_VALIDATOR_GUIDE.md
**Issues?** Test with lead_intake_template.csv first
