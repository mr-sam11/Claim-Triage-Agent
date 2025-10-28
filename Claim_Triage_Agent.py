import streamlit as st
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import json
import os
import re
from datetime import datetime
from send_email import send_sns_email
from db_utils import save_claim_to_db

# ---------------- STREAMLIT UI ----------------
st.set_page_config(page_title="Claim Triage Agent", layout="wide")
st.title("🏦 Claim Triage Agent")

# Load environment variables
load_dotenv()

# Upload PDF
uploaded_file = st.file_uploader("📄 Upload Insurance Claim Document", type=["pdf"])
claim_number = st.text_input("Enter Claim Number", placeholder="e.g., CLAIM12345")

if uploaded_file is not None and claim_number:
    st.info("Processing claim document... Please wait ⏳")

    # Save uploaded file temporarily
    pdf_path = Path("temp_uploaded.pdf")
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.read())

    # Load the document
    loader = PyPDFLoader(file_path=pdf_path)
    docs = loader.load()
    all_text = " ".join([page.page_content for page in docs])

    # Initialize Gemini model
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)

    # Claim triage prompt
    prompt = f"""
You are an intelligent AI-powered *Claims Triage Agent* for an insurance company. 
Your primary objective is to automatically review and analyze insurance claim documents, 
categorize the claim type, assess its severity and risk, and recommend a priority level for processing. 

Follow these goals strictly:
1. Understand the document fully — it may contain claim forms, investigation reports, invoices, or communication logs.
2. Identify key details such as claimant information, claim type (Health, Auto, Property, Travel, etc.), amount claimed, and incident description.
3. Evaluate **Severity Level** based on the extent of damage, injury, or loss (Low, Medium, High, or Critical).
4. Evaluate **Risk Level** based on data completeness, possible fraud indicators, or inconsistencies (Low, Medium, High).
5. Recommend **Priority** for processing:
   - Critical → Immediate human review needed (e.g., severe injuries, large payouts)
   - High → Review within 24 hours
   - Medium → Process within SLA
   - Low → Routine automated handling
6. Detect and summarize any **Red Flags** (missing FIR, unverified documents, suspicious patterns).
7. Provide a **final Recommendation** for the claim handler (e.g., “Approve immediately”, “Send for investigation”, “Reject due to mismatch”).

Return **only valid JSON**, nothing else — no explanations, no markdown, no extra text. 
Output exactly in this format:
{{
    "Claim Type": "",
    "Claim Summary": "",
    "Severity Level": "",
    "Risk Level": "",
    "Priority": "",
    "Red Flags": "",
    "Recommendation": ""
}}

Claim Document:
{all_text}
"""

    # ---------------- RUN MODEL ----------------
    summary = llm.invoke(prompt)
    output_text = summary.content

    # Clean output to extract JSON block safely
    json_match = re.search(r"\{[\s\S]*\}", output_text)
    if json_match:
        output_text = json_match.group(0)

    # Try to parse clean JSON
    try:
        claim_data = json.loads(output_text)
        formatted_json = json.dumps(claim_data, indent=2)
    except Exception:
        st.error("⚠️ Could not parse model output as JSON. Showing raw text.")
        claim_data = {"RawOutput": output_text}
        formatted_json = output_text

    # ---------------- DISPLAY REPORT ----------------
    st.success("✅ Claim triage analysis completed!")
    st.subheader("📊 CLAIM TRIAGE REPORT")

    # Beautiful structured display
    if "RawOutput" in claim_data:
        st.text_area("Raw Output", formatted_json, height=200)
    else:
        st.json(claim_data)  # Pretty formatted, colorized JSON output

    # ---------------- SAVE REPORT AS PDF ----------------
    os.makedirs("claim_triage_reports", exist_ok=True)
    pdf_summary_path = f"claim_triage_reports/{claim_number}.pdf"

    c = canvas.Canvas(pdf_summary_path, pagesize=A4)
    text_object = c.beginText(50, 800)
    text_object.setFont("Helvetica", 12)
    for line in formatted_json.split("\n"):
        text_object.textLine(line)
    c.drawText(text_object)
    c.save()

    # ---------------- MONGODB SAVE ----------------
    record = {
        "_id": claim_number,
        "Claim Type": claim_data.get("Claim Type", ""),
        "Claim Summary": claim_data.get("Claim Summary", ""),
        "Severity Level": claim_data.get("Severity Level", ""),
        "Risk Level": claim_data.get("Risk Level", ""),
        "Priority": claim_data.get("Priority", ""),
        "Red Flags": claim_data.get("Red Flags", ""),
        "Recommendation": claim_data.get("Recommendation", ""),
        "Processed_On": datetime.utcnow().isoformat()
    }

    # Save to MongoDB
    save_claim_to_db(claim_number, record)
    st.success("📦 Data stored in MongoDB successfully!")

    # ---------------- PDF DOWNLOAD ----------------
    with open(pdf_summary_path, "rb") as pdf_file:
        st.download_button(
            label="⬇️ Download Claim Triage PDF Report",
            data=pdf_file,
            file_name=f"{claim_number}.pdf",
            mime="application/pdf",
        )

    # ---------------- SNS ALERT VIA EMAIL ----------------
    priority = record.get("Priority", "").lower()
    if priority in ["critical", "high"]:
        st.warning("⚠️ High Priority Claim detected! Sending SNS email alert...")
        subject = f"🚨 High Priority Claim Alert - {claim_number}"
        body = f"Claim {claim_number} requires immediate attention.\n\nSummary:\n{json.dumps(record, indent=2)}"
        send_sns_email(subject, body, "sachindawar05@gmail.com")

else:
    st.warning("Please upload a claim PDF and enter a claim number to start triage processing.")
