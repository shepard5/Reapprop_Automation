import pandas as pd
import openai
import time
import json
import os

# Initialize OpenAI client - set OPENAI_API_KEY environment variable
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def extract_values_from_text(text):
    """
    Sends the reappropriation text chunk to GPT to extract key values.
    """
    prompt = f"""
    Extract the following details from this reappropriation text:

    1. **Reappropriation Amount** - The amount listed as a reappropriation (e.g., $5,000,000).
    2. **Appropriation Amount** - The original appropriation amount (if available).
    3. **Year of Appropriation** - The year when the original appropriation was made.
    4. **Appropriation ID** - If the text includes a unique ID associated with the appropriation.

    Example text:

    "
    By chapter 53, section 1, of the laws of 1998
    ....
    ....
    26 (302198C1) (15503) ... 1,000,000 .................... (re. $796,000)
    "

    Expected Output (valid JSON):
    {{
        "Reappropriation Amount": "$796,000",
        "Appropriation Amount": "$1,000,000",
        "Year of Appropriation": "1998",
        "Appropriation ID": "15503"
    }}

    If any field is missing, return "N/A".

    Text to analyze:
    {text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert at extracting structured financial and legislative data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        # Validate the response
        if not response.choices or not response.choices[0].message:
            print("⚠️ Warning: Empty response from OpenAI.")
            return {"Reappropriation Amount": "N/A", "Appropriation Amount": "N/A", "Year of Appropriation": "N/A", "Appropriation ID": "N/A"}

        extracted_data = response.choices[0].message.content.strip()

        # Remove unnecessary JSON formatting
        if extracted_data.startswith("```json"):
            extracted_data = extracted_data[7:-3].strip()

        # Parse JSON output
        return json.loads(extracted_data)

    except json.JSONDecodeError:
        print(f"❌ JSON Parsing Error – Unexpected response format: {extracted_data}")
        return {"Reappropriation Amount": "N/A", "Appropriation Amount": "N/A", "Year of Appropriation": "N/A", "Appropriation ID": "N/A"}
    except Exception as e:
        print(f"⚠️ OpenAI API Error: {e}")
        return {"Reappropriation Amount": "N/A", "Appropriation Amount": "N/A", "Year of Appropriation": "N/A", "Appropriation ID": "N/A"}

def process_csv(input_csv):
    """
    Reads the extracted reappropriation chunks, processes each through GPT API,
    and writes the structured results into the same CSV file.
    """
    df = pd.read_csv(input_csv)

    # Add new columns for extracted data
    df["Reappropriation Amount"] = "N/A"
    df["Appropriation Amount"] = "N/A"
    df["Year of Appropriation"] = "N/A"
    df["Appropriation ID"] = "N/A"

    i = 0

    for idx, row in df.iterrows():
        text = row["Reappropriation"]
        extracted_data = extract_values_from_text(text)

        # Store extracted values in the same row
        df.at[idx, "Reappropriation Amount"] = extracted_data["Reappropriation Amount"]
        df.at[idx, "Appropriation Amount"] = extracted_data["Appropriation Amount"]
        df.at[idx, "Year of Appropriation"] = extracted_data["Year of Appropriation"]
        df.at[idx, "Appropriation ID"] = extracted_data["Appropriation ID"]

        time.sleep(1.5)  # Avoid hitting API rate limits

        print(i)
        i+=1

    # Save back to the same CSV
    df.to_csv(input_csv, index=False)
    print(f"✅ Process complete. Data written back to {input_csv}")

# Run the processing on the same file
process_csv("ReappropriationsHESCSTOPS2526.csv")