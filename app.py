import streamlit as st
import os
import fitz  # PyMuPDF
import docx
import pandas as pd
import re
from datetime import datetime
import google.generativeai as genai
from google.cloud import secretmanager


def get_gemini_api_key():
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    secret_name = "gemini-api-key"
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# Configure Gemini API key
# genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
genai.configure(api_key=get_gemini_api_key())

# Generate function using latest API
def generate(text):
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(text)

    return response.text  # response.text automatically gives full output


##############
##############


# --- File Text Extraction ---
def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    return "\n".join([page.get_text() for page in doc])

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_txt(file):
    return file.read().decode("utf-8")

def get_text(file, filename):
    if filename.endswith(".pdf"):
        return extract_text_from_pdf(file)
    elif filename.endswith(".docx"):
        return extract_text_from_docx(file)
    elif filename.endswith(".txt"):
        return extract_text_from_txt(file)
    else:
        return ""

# --- Parse LLM Output ---
def parse_llm_output(output, filename):
    errors = []
    lines = output.split('\n')
    current = {}
    for line in lines:
        if "Line Number" in line:
            nums = re.findall(r"\d+", line)
            current['Line Number'] = int(nums[0]) if nums else None
        elif "Error Type" in line:
            current['Error Type'] = line.split(":", 1)[-1].strip()
        elif "Description" in line:
            current['Error Description'] = line.split(":", 1)[-1].strip()
        elif "Suggested fix" in line:
            current['Suggested Change'] = line.split(":", 1)[-1].strip()
            current['Document Name'] = filename
            errors.append(current.copy())
            current = {}
    return errors

# --- Streamlit UI ---
st.title("📄Document Error Detector (Gemini LLM)")
st.write("Upload `.pdf`, `.docx`, or `.txt` files to analyze for common errors using LLM.")

uploaded_files = st.file_uploader("Upload Documents", type=["pdf", "docx", "txt"], accept_multiple_files=True)

if uploaded_files:
    all_errors = []
    for uploaded_file in uploaded_files:
        st.subheader(f"Analyzing: `{uploaded_file.name}`")
        text = get_text(uploaded_file, uploaded_file.name)

        prompt = f"""
You are an insurance document analyzer AI. Analyze the following text and identify any of the following types of errors:

1. Typographical Errors (spelling, grammar, punctuation)
2. Name Inconsistencies (e.g., John Smith vs. J. Smith)
3. Date Inconsistencies (e.g., mismatched or illogical dates)
4. Domain-Specific Mistakes:
   - Invalid or inconsistent policy numbers (e.g., format: POL-YYYY-XXXXX)
   - Unrealistic coverage amounts (e.g., $10 million for auto insurance)
   - Incorrect insurance terminology (e.g., "insured person" vs. "policyholder")
   - Missing required fields (e.g., no Start Date or Policy Number)

For each issue, provide:
- Line Number (if applicable)
- Error Type
- Description of the error
- Suggested fix

Document Name: {uploaded_file.name}

Text:
{text}
"""
        with st.spinner("Analyzing with Gemini..."):
            response = generate(prompt)
            parsed = parse_llm_output(response, uploaded_file.name)
            all_errors.extend(parsed)

    # Show and download results
    if all_errors:
        df = pd.DataFrame(all_errors)
        st.success("Analysis complete!")
        st.dataframe(df)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_file = f"errors_{timestamp}.xlsx"
        df.to_excel(excel_file, index=False)

        with open(excel_file, "rb") as f:
            st.download_button("📥 Download Excel", f, file_name=excel_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.warning("No errors found or unable to parse response.")
