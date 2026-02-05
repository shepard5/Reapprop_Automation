import pdfplumber
import pandas as pd
import re

def extract_reappropriation_chunks(pdf_path):
    records = []
    
    with pdfplumber.open(pdf_path) as pdf:
        all_lines = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_lines.extend(text.splitlines())

    current_chunk = []
    capturing = False
    chapter_header = ""  # Store the latest "By chapter..." line for reference

    for line in all_lines:
        line = line.strip()

        # Detect "By chapter XX, section Y, of the laws of ZZZZ" to start a new section
        chapter_match = re.search(r"(By\s+chapter\s+\d+,\s+section\s+\d+,?\s+of\s+the\s+laws\s+of\s+\d{4})", line, re.IGNORECASE)
        if chapter_match:
            chapter_header = chapter_match.group(1)  # Save latest chapter header
            current_chunk = [line]  # Start new section
            capturing = True
            continue  # Skip to next line

        if capturing:
            current_chunk.append(line)  # Add text to current chunk

            # Detect "re. $XXXX" (Reappropriation amount found)
            re_match = re.search(r"re\.\s?\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?", line)
            if re_match:
                # Ensure the stored text starts with "By chapter..." for each entry
                if not current_chunk[0].startswith("By chapter"):
                    current_chunk.insert(0, chapter_header)

                # Store the chunk in records and immediately start fresh for next reappropriation
                records.append({"Reappropriation": "\n".join(current_chunk)})
                current_chunk = [chapter_header]  # Reset chunk, retaining the chapter header

    return records

def main():
    pdf_path = "/Users/samscott/Desktop/Ways and Means/25-26/Reapprop Automation/Serves Purpose/Testing/HESC/HESCSTOPS2526.pdf"
    records = extract_reappropriation_chunks(pdf_path)

    # Debugging: Print extracted text before saving
    for i, chunk in enumerate(records):
        print(f"🔍 Extracted Chunk {i+1}:\n{chunk['Reappropriation']}\n{'-'*50}")

    # Create a DataFrame and save to CSV
    df = pd.DataFrame(records, columns=["Reappropriation"])
    df.to_csv("ReappropriationsHESCSTOPS2526.csv", index=False)

    print("✅ Extraction complete. Data saved to CSV.")

if __name__ == "__main__":
    main()