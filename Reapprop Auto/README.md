# NYS Budget Reappropriation Analysis Tool

Automated tool to compare enacted budget vs executive budget and identify missing reappropriations.

## Purpose
Identifies items from the prior year's enacted budget that should appear as reappropriations in the current year's executive budget but are missing.

## Key Logic
- **Enacted appropriations** from last year → should appear as **executive reappropriations** this year
- **Enacted reappropriations** from last year → should appear as **executive reappropriations** this year  
- **Executive appropriations** are new money (ignored for comparison)

## Features
- **Year Extraction**: Automatically identifies the original appropriation year from budget text
- **Enhanced Pattern Matching**: Robust extraction of appropriation IDs and amounts
- **Progress Tracking**: Real-time progress indicators for large PDF processing
- **Comprehensive Reporting**: Detailed CSV output with agency, amount, year, and context

## Usage

### Quick Start
```bash
python final_budget_comparison.py
```
Uses default files: `2025 Enacted.pdf` and `2026 Executive.pdf`

### Custom Files
```bash
python final_budget_comparison.py "path/to/enacted.pdf" "path/to/executive.pdf"
```

## Output Files

### Main Results
- **`budget_discrepancies.csv`** - Detailed list of all missing reappropriations with year information
- **`analysis_summary.json`** - Summary statistics

### Supporting Data
- **`enacted_budget_data.csv`** - All data extracted from enacted budget
- **`executive_budget_data.csv`** - All data extracted from executive budget

## Latest Results Summary

**2,481 total missing reappropriations identified**
- From enacted appropriations: 2,021
- From enacted reappropriations: 460
- Agencies affected: 38
- **Total amount missing: $245.4 billion**

### Year Distribution of Missing Items
- **2024**: 2,475 items (majority from FY 2024-25 enacted budget)
- **2025**: 3 items (items with April 1, 2025 start dates)
- **2026**: 3 items (items with March 31, 2026 end dates)

### Top Agencies with Missing Reappropriations
1. **Education Department**: $135.9B missing
2. **Department of Mental Hygiene**: $30.5B missing  
3. **Department of Family Assistance**: $29.3B missing
4. **Department of Transportation**: $15.5B missing
5. **Department of Health**: $12.1B missing

## CSV Output Format
The `budget_discrepancies.csv` file contains:
- `agency`: Agency name
- `budget_type`: STATE OPERATIONS, AID TO LOCALITIES, or CAPITAL PROJECTS
- `appropriation_id`: 5-digit appropriation identifier
- `enacted_amount`: Dollar amount from enacted budget
- `enacted_type`: Whether it was an appropriation or reappropriation in enacted budget
- `text`: Original budget text line
- `page`: PDF page number where found
- `description`: Explanation of the discrepancy
- **`year`: Original appropriation year (NEW)**

## Requirements
- Python 3.x
- pdfplumber (`pip install pdfplumber`)
- pandas (`pip install pandas`)

## Legacy Files (for reference)
- `BudgetParseV2.py` - Original PDF parser
- `ModularBudgetParse.py` - Modular PDF parser
- `Extract Reapprop Details.py` - OpenAI-powered detail extraction
- `Reappropriations.py` - Focused reappropriation extraction

## How It Works
1. **Extracts** appropriations and reappropriations from both PDFs using enhanced pattern matching
2. **Identifies** agency names, budget types, and **original appropriation years**
3. **Compares** enacted budget items against executive budget reappropriations
4. **Flags** missing items with appropriation ID, amounts, year, and context
5. **Generates** comprehensive reports organized by agency and amount

The tool provides full automation for identifying budget discrepancies and potential oversights in reappropriation planning, now with enhanced year tracking for better historical context.
