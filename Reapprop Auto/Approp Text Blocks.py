import pdfplumber
import pandas as pd
import re
import tkinter as tk
from tkinter import filedialog

### 📌 SELECT PDF FILE ###
def select_file():
    """
    Open a file dialog to select a PDF file and return its path.
    """
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="Select a PDF File", filetypes=[("PDF Files", "*.pdf")])
    return file_path

### 📌 SPLIT BUDGET INTO SECTIONS ###
def split_budget_into_sections(pdf_path):
    """
    Reads the budget PDF and splits it into sections based on agency, budget type, and fiscal year.
    """
    sections = []
    current_section = []
    current_agency = None
    current_budget_type = None
    current_fiscal_year = None

    header_pattern = re.compile(r"^(AID TO LOCALITIES|STATE OPERATIONS|CAPITAL PROJECTS)", re.IGNORECASE)
    fiscal_year_pattern = re.compile(r"(\d{4}-\d{2})")
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.splitlines()
            if len(lines) < 3:
                continue
            
            # Extract agency, budget type, and fiscal year from header
            agency = lines[1].strip()
            budget_info = lines[2].strip()
            
            budget_match = header_pattern.search(budget_info)
            fiscal_match = fiscal_year_pattern.search(budget_info)

            budget_type = budget_match.group(1) if budget_match else current_budget_type
            fiscal_year = fiscal_match.group(1) if fiscal_match else current_fiscal_year

            # Detect if we've hit a new section
            if agency != current_agency or budget_type != current_budget_type:
                if current_section:
                    sections.append({
                        "agency": current_agency,
                        "budget_type": current_budget_type,
                        "fiscal_year": current_fiscal_year,
                        "content": "\n".join(current_section),
                        "page_start": page_num - len(current_section) + 1,
                        "page_end": page_num
                    })
                    current_section = []

                # Update current tracking variables
                current_agency = agency
                current_budget_type = budget_type
                current_fiscal_year = fiscal_year

            # Append page content to current section
            current_section.append(text)

        # Add the last section
        if current_section:
            sections.append({
                "agency": current_agency,
                "budget_type": current_budget_type,
                "fiscal_year": current_fiscal_year,
                "content": "\n".join(current_section),
                "page_start": len(pdf.pages) - len(current_section) + 1,
                "page_end": len(pdf.pages)
            })

    return sections

### 📌 PROCESS SECTIONS & IDENTIFY APPROPRIATIONS ###
def process_appropriations(content):
    """
    Extract detailed information from appropriations sections and return structured records.
    """
    appropriation_pattern = re.compile(r"\((\d{5})\)\s+\.{3,}\s+\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?")
    fund_pattern = re.compile(r"(General Fund|Special Revenue Funds - Federal|Special Revenue Funds - Other|Fiduciary Funds)", re.IGNORECASE)

    lines = content.split("\n")
    current_chunk = []
    records = []

    fund_type = "Unknown"
    confidence_flag = "High Confidence"

    for line in lines:
        line = line.strip()

        # Check for appropriation match (start of a new block)
        appropriation_match = appropriation_pattern.search(line)
        fund_match = fund_pattern.search(line)

        if fund_match:
            fund_type = fund_match.group(1)  # Update fund type when found

        if appropriation_match:
            # If we were already capturing a block, save it before starting a new one
            if current_chunk:
                records.append({
                    "Fund Type": fund_type,
                    "Appropriation Code": appropriation_match.group(1),
                    "Appropriation": "\n".join(current_chunk),
                    "Dollar Amount": appropriation_match.group(0),
                    "Confidence Flag": confidence_flag
                })
                current_chunk = []

            # Start new appropriation block
            current_chunk.append(line)
        else:
            current_chunk.append(line)

    # Handle any remaining chunk
    if current_chunk:
        records.append({
            "Fund Type": fund_type,
            "Appropriation Code": "N/A",
            "Appropriation": "\n".join(current_chunk),
            "Dollar Amount": "N/A",
            "Confidence Flag": "Needs Review"
        })

    return records

### 📌 PROCESS REAPPROPRIATIONS ###
def process_reappropriations(content):
    """
    Extract detailed information from reappropriations sections and return structured records.
    """
    reappropriation_pattern = re.compile(r"\(re\.\s?\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)")
    records = []

    lines = content.split("\n")
    current_chunk = []

    for line in lines:
        line = line.strip()

        if reappropriation_pattern.search(line):  
            # Found a reappropriation, store previous chunk if any
            if current_chunk:
                records.append({"Reappropriation": "\n".join(current_chunk)})
                current_chunk = []
            
            current_chunk.append(line)  # Start a new reappropriation block
        else:
            current_chunk.append(line)

    if current_chunk:
        records.append({"Reappropriation": "\n".join(current_chunk)})

    return records

### 📌 MAIN FUNCTION ###
def main():
    """
    Main function to execute the PDF selection and extraction.
    """
    print("📂 Please select a PDF file containing the budget data.")
    pdf_path = select_file()

    if pdf_path:
        print(f"📄 Selected PDF: {pdf_path}")

        # Split budget into sections
        sections = split_budget_into_sections(pdf_path)
        print(f"✅ Identified {len(sections)} sections.")

        appropriation_records = []
        reappropriation_records = []

        for section in sections:
            agency = section["agency"]
            budget_type = section["budget_type"]
            fiscal_year = section["fiscal_year"]
            content = section["content"]

            print(f"🔍 Processing Section: {agency} ({budget_type}) - Pages {section['page_start']} to {section['page_end']}")

            if "REAPPROPRIATIONS" in budget_type:
                records = process_reappropriations(content)
                reappropriation_records.extend(records)
            else:
                records = process_appropriations(content)
                appropriation_records.extend(records)

        # Save Appropriations to a CSV
        if appropriation_records:
            df = pd.DataFrame(appropriation_records, columns=["Fund Type", "Appropriation Code", "Appropriation", "Dollar Amount", "Confidence Flag"])
            output_file = "Appropriations.csv"
            df.to_csv(output_file, index=False)
            print(f"✅ Appropriations extraction complete. Data saved to {output_file}")

        # Save Reappropriations to a CSV
        if reappropriation_records:
            df = pd.DataFrame(reappropriation_records, columns=["Reappropriation"])
            output_file = "Reappropriations.csv"
            df.to_csv(output_file, index=False)
            print(f"✅ Reappropriations extraction complete. Data saved to {output_file}")

        print("✅ Processing complete.")
    else:
        print("No file selected. Exiting.")

if __name__ == "__main__":
    main()