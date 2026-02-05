import pdfplumber
import pandas as pd
import openai
import json
import re
import tkinter as tk
from tkinter import filedialog

### 📌 OpenAI API Key (Replace with your own) ###
API_KEY = "your_openai_api_key"

### 📌 SELECT PDF FILE ###
def select_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="Select a PDF File", filetypes=[("PDF Files", "*.pdf")])
    return file_path

### 📌 DETECT HEADERS & SPLIT PDF INTO SECTIONS ###
def split_pdf_into_sections(pdf_path):
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

### 📌 GPT PARSING FUNCTION ###
def parse_budget_section_with_gpt(section):
    """
    Sends a budget section to GPT for structured extraction.
    """
    prompt = f"""
    You are an expert in financial document analysis, tasked with extracting structured budget data 
    from legislative appropriations documents.

    **Instructions:**
    - Identify the **Agency/Department**, **Budget Type**, **Fiscal Year** from the header.
    - Detect and extract **Appropriations and Reappropriations**.
    - Appropriations contain:
      - A **five-digit appropriation code** in parentheses: (#####)
      - A **dollar amount** formatted as: $X,XXX,XXX
      - A **detailed description spanning multiple lines**
    - Reappropriations:
      - Always include "(re.)" at the end of the listing.
      - Extract relevant metadata around the "(re.)".
    
    **Data Format for Each Extracted Record:**
    Return the results as a JSON array following this structure:
    ```json
    [
      {
        "Agency": "<Extracted Agency Name>",
        "Budget Type": "<Aid to Localities / State Ops / Capital Projects>",
        "Section Type": "<Appropriations / Reappropriations>",
        "Fiscal Year": "<Extracted Year>",
        "Page Start": "<Starting Page>",
        "Page End": "<Ending Page>",
        "Appropriation Code": "<5-digit Code>",
        "Description": "<Multi-line text for appropriation>",
        "Dollar Amount": "<Extracted amount>",
        "Confidence Flag": "<High Confidence / Needs Review>"
      }
    ]
    ```
    
    **Budget Text to Analyze:**
    {section["content"]}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a budget analyst specializing in financial appropriations."},
                      {"role": "user", "content": prompt}],
            api_key=API_KEY,
            temperature=0
        )

        extracted_data = response["choices"][0]["message"]["content"].strip()

        # Remove unnecessary JSON formatting if present
        if extracted_data.startswith("```json"):
            extracted_data = extracted_data[7:-3].strip()

        # Parse JSON output
        return json.loads(extracted_data)

    except json.JSONDecodeError:
        print(f"❌ JSON Parsing Error – Unexpected response format: {extracted_data}")
        return []
    except Exception as e:
        print(f"⚠️ OpenAI API Error: {e}")
        return []

### 📌 PROCESS BUDGET PDF ###
def process_budget_pdf(pdf_path):
    """
    Process the budget PDF by splitting it into sections and sending each to GPT.
    """
    sections = split_pdf_into_sections(pdf_path)
    all_records = []

    for section in sections:
        print(f"🔍 Processing {section['agency']} ({section['budget_type']}) - Pages {section['page_start']} to {section['page_end']}...")

        records = parse_budget_section_with_gpt(section)

        for record in records:
            all_records.append(record)

    return all_records

### 📌 MAIN FUNCTION ###
def main():
    """
    Main function to execute the PDF selection and extraction.
    """
    print("📂 Please select a PDF file containing the budget data.")
    pdf_path = select_file()

    if pdf_path:
        print(f"📄 Selected PDF: {pdf_path}")

        budget_data = process_budget_pdf(pdf_path)

        if not budget_data:
            print("⚠️ No appropriations found. Please check the PDF formatting.")
            return

        df = pd.DataFrame(budget_data, columns=[
            "Agency", "Budget Type", "Section Type", "Fiscal Year", "Page Start", "Page End",
            "Appropriation Code", "Description", "Dollar Amount", "Confidence Flag"
        ])
        
        output_file = f"{pdf_path.split('/')[-1].replace('.pdf', '')}_Processed.csv"
        df.to_csv(output_file, index=False)

        print(f"✅ Extraction complete. Data saved to {output_file}")

if __name__ == "__main__":
    main()