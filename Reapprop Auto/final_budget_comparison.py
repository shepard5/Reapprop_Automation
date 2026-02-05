#!/usr/bin/env python3
"""
NYS Budget Reappropriation Analysis Tool
Compares enacted budget vs executive budget to identify missing reappropriations.

Logic: Items from enacted budget (both appropriations and reappropriations) 
should appear as reappropriations in the executive budget.
"""

import pdfplumber
import pandas as pd
import re
from collections import defaultdict
import json
import sys

class BudgetAnalyzer:
    def __init__(self):
        self.enacted_data = []
        self.executive_data = []
        
    def extract_budget_data(self, pdf_path, budget_type="unknown"):
        """Extract appropriations and reappropriations from budget PDF."""
        print(f"📄 Processing {budget_type} budget: {pdf_path}")
        
        records = []
        current_agency = "N/A"
        current_budget_type = "N/A"
        current_year = "Unknown"
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text:
                    continue
                
                lines = text.splitlines()
                
                # Update current agency and budget type
                agency_match = self._find_agency(text)
                if agency_match:
                    current_agency = agency_match
                
                budget_type_match = re.search(r"(STATE OPERATIONS|AID TO LOCALITIES|CAPITAL PROJECTS)", text)
                if budget_type_match:
                    current_budget_type = budget_type_match.group(0).strip()
                
                # Extract year information from page text
                page_year = self._extract_year_from_text(text)
                if page_year != "Unknown":
                    current_year = page_year
                
                # Process each line for appropriations and reappropriations
                for line in lines:
                    line = line.strip()
                    
                    # Extract year from individual line if available
                    line_year = self._extract_year_from_text(line)
                    year_to_use = line_year if line_year != "Unknown" else current_year
                    
                    # Find appropriations: (XXXXX) followed by amount
                    approp_patterns = [
                        r'\((\d{5})\)\s*[.\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                        r'\((\d{5})\)[^(]*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                        r'(\d{5})\)\s*[.\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
                    ]
                    
                    for pattern in approp_patterns:
                        for match in re.finditer(pattern, line):
                            approp_id = match.group(1)
                            amount_str = match.group(2).replace(',', '')
                            
                            try:
                                amount = float(amount_str)
                                records.append({
                                    'type': 'appropriation',
                                    'agency': current_agency,
                                    'budget_type': current_budget_type,
                                    'appropriation_id': approp_id,
                                    'amount': amount,
                                    'text': line,
                                    'page': page_num + 1,
                                    'source': budget_type,
                                    'year': year_to_use
                                })
                            except ValueError:
                                continue
                    
                    # Find reappropriations: re. $XXXXX
                    reapprop_patterns = [
                        r're\.\s?\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                        r'\(re\.\s?\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\)',
                        r'reappropriation[:\s]+\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
                    ]
                    
                    for pattern in reapprop_patterns:
                        for match in re.finditer(pattern, line, re.IGNORECASE):
                            amount_str = match.group(1).replace(',', '')
                            
                            try:
                                amount = float(amount_str)
                                approp_id = self._find_appropriation_id_in_line(line)
                                
                                records.append({
                                    'type': 'reappropriation',
                                    'agency': current_agency,
                                    'budget_type': current_budget_type,
                                    'appropriation_id': approp_id,
                                    'amount': amount,
                                    'text': line,
                                    'page': page_num + 1,
                                    'source': budget_type,
                                    'year': year_to_use
                                })
                            except ValueError:
                                continue
                
                # Progress indicator
                if (page_num + 1) % 100 == 0:
                    progress = (page_num + 1) / total_pages * 100
                    print(f"  Progress: {page_num + 1}/{total_pages} pages ({progress:.1f}%)")
        
        print(f"✅ Extracted {len(records)} records from {budget_type} budget")
        return records
    
    def _extract_year_from_text(self, text):
        """Extract year information from budget text."""
        # Look for year patterns in the text
        year_patterns = [
            r'(\d{4})-(\d{2})',  # 2024-25 format
            r'(\d{4})-\d{2}',    # Extract first year from 2024-25
            r'year (\d{4})',     # "year 2024"
            r'(\d{4}) school year',  # "2024 school year"
            r'April 1, (\d{4})',     # "April 1, 2024"
            r'March 31, (\d{4})'     # "March 31, 2025"
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, text)
            if match:
                year = match.group(1)
                # Convert to int and validate it's a reasonable year
                try:
                    year_int = int(year)
                    if 2020 <= year_int <= 2030:  # Reasonable range for budget years
                        return year
                except ValueError:
                    continue
        
        return "Unknown"
    
    def _find_agency(self, text):
        """Find agency name in page text."""
        agency_patterns = [
            r'^([A-Z][A-Z ]{15,}[A-Z])$',
            r'([A-Z][A-Z ]{10,}[A-Z])\n\s*(STATE OPERATIONS|AID TO LOCALITIES|CAPITAL PROJECTS)',
            r'^([A-Z][A-Z ]{8,}[A-Z])\s*$'
        ]
        
        for pattern in agency_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                agency = match.group(1).strip()
                exclude_words = ['APPROPRIATIONS', 'REAPPROPRIATIONS', 'BUDGET', 'SCHEDULE', 'GENERAL FUND', 'SPECIAL REVENUE']
                if not any(word in agency for word in exclude_words):
                    return agency
        return None
    
    def _find_appropriation_id_in_line(self, line):
        """Find appropriation ID in a line."""
        id_patterns = [r'\((\d{5})\)', r'(\d{5})\)', r'\[(\d{5})\]', r'(\d{5})[^\d]']
        
        for pattern in id_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        return "N/A"
    
    def analyze_budgets(self, enacted_pdf, executive_pdf):
        """Main analysis function."""
        print("🔍 Starting NYS Budget Reappropriation Analysis...")
        print("="*60)
        
        # Extract data from both PDFs
        self.enacted_data = self.extract_budget_data(enacted_pdf, "enacted")
        self.executive_data = self.extract_budget_data(executive_pdf, "executive")
        
        # Convert to DataFrames
        enacted_df = pd.DataFrame(self.enacted_data)
        executive_df = pd.DataFrame(self.executive_data)
        
        # Save extracted data
        enacted_df.to_csv("enacted_budget_data.csv", index=False)
        executive_df.to_csv("executive_budget_data.csv", index=False)
        
        print("\n📊 Finding discrepancies...")
        
        # Find discrepancies: enacted items missing as reappropriations in executive
        discrepancies = self._find_discrepancies(enacted_df, executive_df)
        
        # Generate report
        self._generate_report(discrepancies)
        
        return discrepancies
    
    def _find_discrepancies(self, enacted_df, executive_df):
        """Find enacted items missing as reappropriations in executive budget."""
        discrepancies = []
        
        # Create lookup for executive reappropriations only
        executive_reappropriations = set()
        for _, row in executive_df.iterrows():
            if row['type'] == 'reappropriation':
                key = (row['agency'], row['appropriation_id'])
                executive_reappropriations.add(key)
        
        print(f"📋 Executive budget has {len(executive_reappropriations)} reappropriations")
        
        # Check enacted items against executive reappropriations
        for _, row in enacted_df.iterrows():
            if row['appropriation_id'] == "N/A":
                continue
                
            key = (row['agency'], row['appropriation_id'])
            
            if key not in executive_reappropriations:
                discrepancies.append({
                    'agency': row['agency'],
                    'budget_type': row['budget_type'],
                    'appropriation_id': row['appropriation_id'],
                    'enacted_amount': row['amount'],
                    'enacted_type': row['type'],
                    'text': row['text'],
                    'page': row['page'],
                    'description': f'Enacted {row["type"]} should appear as reappropriation in executive budget',
                    'year': row['year']
                })
        
        print(f"🚨 Found {len(discrepancies)} missing reappropriations")
        return discrepancies
    
    def _generate_report(self, discrepancies):
        """Generate comprehensive discrepancy report."""
        print(f"\n📋 Generating report...")
        
        if len(discrepancies) == 0:
            print("✅ No discrepancies found!")
            return
        
        # Save detailed discrepancies
        discrepancy_df = pd.DataFrame(discrepancies)
        discrepancy_df.to_csv("budget_discrepancies.csv", index=False)
        
        # Calculate summary statistics
        from_appropriations = [d for d in discrepancies if d['enacted_type'] == 'appropriation']
        from_reappropriations = [d for d in discrepancies if d['enacted_type'] == 'reappropriation']
        
        summary = {
            'total_discrepancies': len(discrepancies),
            'from_enacted_appropriations': len(from_appropriations),
            'from_enacted_reappropriations': len(from_reappropriations),
            'agencies_affected': len(set(d['agency'] for d in discrepancies)),
            'total_amount_missing': sum(d['enacted_amount'] for d in discrepancies)
        }
        
        # Print summary
        print("\n" + "="*80)
        print("📊 NYS BUDGET REAPPROPRIATION ANALYSIS RESULTS")
        print("="*80)
        print(f"Total Missing Reappropriations: {summary['total_discrepancies']:,}")
        print(f"From Enacted Appropriations: {summary['from_enacted_appropriations']:,}")
        print(f"From Enacted Reappropriations: {summary['from_enacted_reappropriations']:,}")
        print(f"Agencies Affected: {summary['agencies_affected']}")
        print(f"Total Amount Missing: ${summary['total_amount_missing']:,.2f}")
        
        # Show top discrepancies
        print(f"\n🔝 TOP 10 LARGEST MISSING REAPPROPRIATIONS:")
        top_discrepancies = sorted(discrepancies, key=lambda x: x['enacted_amount'], reverse=True)[:10]
        
        for i, disc in enumerate(top_discrepancies, 1):
            print(f"{i:2d}. {disc['agency']}")
            print(f"    ID: {disc['appropriation_id']} | Amount: ${disc['enacted_amount']:,.2f}")
            print(f"    Type: {disc['enacted_type'].title()} | Budget: {disc['budget_type']} | Year: {disc['year']}")
            print()
        
        # Group by agency
        print(f"📋 SUMMARY BY AGENCY:")
        agency_groups = defaultdict(list)
        for disc in discrepancies:
            agency_groups[disc['agency']].append(disc)
        
        for agency, agency_discs in sorted(agency_groups.items()):
            total_amount = sum(d['enacted_amount'] for d in agency_discs)
            approp_count = len([d for d in agency_discs if d['enacted_type'] == 'appropriation'])
            reapprop_count = len([d for d in agency_discs if d['enacted_type'] == 'reappropriation'])
            
            print(f"\n{agency}")
            print(f"  Items: {len(agency_discs)} | Amount: ${total_amount:,.2f}")
            print(f"  From Appropriations: {approp_count} | From Reappropriations: {reapprop_count}")
        
        # Save summary
        with open("analysis_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📁 Files Generated:")
        print(f"  • budget_discrepancies.csv - Detailed list of all missing reappropriations")
        print(f"  • enacted_budget_data.csv - All data extracted from enacted budget")
        print(f"  • executive_budget_data.csv - All data extracted from executive budget")
        print(f"  • analysis_summary.json - Summary statistics")
        
        print(f"\n💡 Analysis Complete!")
        print(f"   Items from enacted budget missing as reappropriations in executive budget have been identified.")

def main():
    if len(sys.argv) != 3:
        print("Usage: python final_budget_comparison.py <enacted_pdf> <executive_pdf>")
        print("Example: python final_budget_comparison.py '2025 Enacted.pdf' '2026 Executive.pdf'")
        return
    
    enacted_pdf = sys.argv[1]
    executive_pdf = sys.argv[2]
    
    try:
        analyzer = BudgetAnalyzer()
        analyzer.analyze_budgets(enacted_pdf, executive_pdf)
        
    except FileNotFoundError as e:
        print(f"❌ Error: Could not find file - {e}")
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # If no command line arguments, use default files
    if len(sys.argv) == 1:
        enacted_pdf = "2025 Enacted.pdf"
        executive_pdf = "2026 Executive.pdf"
        
        try:
            analyzer = BudgetAnalyzer()
            analyzer.analyze_budgets(enacted_pdf, executive_pdf)
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        main()
