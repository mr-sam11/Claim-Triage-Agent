import streamlit as st
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from textwrap import wrap
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

if uploaded_file is not None:
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
    

    # ----------- Combined and Optimized Prompt -----------
    prompt = f"""
You are an intelligent AI-powered *Claims Triage Agent* for an insurance company. 
Your job is to automatically review and analyze insurance claim documents, 
categorize the claim type, assess severity and risk, and recommend a priority level for processing. 

Follow these goals strictly:

1. Understand the document fully — it may contain claim forms, investigation reports, invoices, or communication logs.
2. Identify key details such as:
   - Claim Number
   - Insured Name
   - Policy Number
   - Claim Type (Health, Auto, Property, Travel, etc.)
   - Claim Summary
3. Evaluate **Severity Level** based on extent of damage, injury, or loss (Low, Medium, High, Critical).
4. Evaluate **Risk Level** based on data completeness, fraud indicators, or inconsistencies (Low, Medium, High).
5. Recommend **Priority** for processing:
   - Critical → Immediate human review needed (severe injuries or large payouts)
   - High → Review within 24 hours
   - Medium → Process within SLA
   - Low → Routine automated handling
6. Detect and summarize any **Red Flags** (missing FIR, unverified documents, suspicious patterns).
7. Provide a **final Recommendation** for the claim handler (e.g., “Approve immediately”, “Send for investigation”, “Reject due to mismatch”).

Return **only valid JSON**, no extra text, markdown, or explanations.

Output strictly in this format:
{{
    "Claim Number": "",
    "Insured Name": "",
    "Policy Number": "",
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

    # Clean output to extract JSON safely
    json_match = re.search(r"\{[\s\S]*\}", output_text)
    if json_match:
        output_text = json_match.group(0)

    try:
        claim_data = json.loads(output_text)
    except Exception:
        st.error("⚠️ Could not parse model output as JSON. Showing raw text.")
        claim_data = {"RawOutput": output_text}

    # ---------------- DISPLAY REPORT (clean text) ----------------
    st.success("✅ Claim triage analysis completed!")
    st.subheader("📊 CLAIM TRIAGE REPORT")

    if "RawOutput" in claim_data:
        st.text_area("Raw Output", claim_data["RawOutput"], height=200)
    else:
        clean_text = "\n".join([f"{k}: {v}" for k, v in claim_data.items()])
        st.text_area("Processed Claim Details", clean_text, height=300)

    # ---------------- SAVE TO MONGODB ----------------
    record = {
        "_id": claim_data.get("Claim Number", "Unknown"),
        "Claim ID": claim_data.get("Claim Number", "Unknown"),
        "Insured Name": claim_data.get("Insured Name", ""),
        "Policy Number": claim_data.get("Policy Number", ""),
        "Claim Type": claim_data.get("Claim Type", ""),
        "Claim Summary": claim_data.get("Claim Summary", ""),
        "Severity Level": claim_data.get("Severity Level", ""),
        "Risk Level": claim_data.get("Risk Level", ""),
        "Priority": claim_data.get("Priority", ""),
        "Red Flags": claim_data.get("Red Flags", ""),
        "Recommendation": claim_data.get("Recommendation", ""),
        "Processed_On": datetime.utcnow().isoformat()
    }

    save_claim_to_db(record["_id"], record)
    st.success("📦 Data stored in MongoDB successfully!")

    # ---------------- CREATE PDF REPORT (line wrap fixed) ----------------
    os.makedirs("claim_triage_reports", exist_ok=True)
    pdf_summary_path = f"claim_triage_reports/{record['_id']}.pdf"

    c = canvas.Canvas(pdf_summary_path, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 14)
    c.drawString(180, height - 40, "CLAIM TRIAGE REPORT")

    c.setFont("Helvetica", 11)
    y = height - 80

    for key, value in record.items():
        lines = wrap(f"{key}: {value}", width=100)
        for line in lines:
            c.drawString(50, y, line)
            y -= 15
            if y < 50:
                c.showPage()
                c.setFont("Helvetica", 11)
                y = height - 50
    c.save()

    # ---------------- EMAIL ALERT (clean text) ----------------
    priority = record.get("Priority", "").lower()
    if priority in ["critical", "high"]:
        st.warning("⚠️ High Priority Claim detected! Sending SNS email alert...")

        subject = f"🚨 High Priority Claim Alert - {record['_id']}"
        body_lines = [f"{k}: {v}" for k, v in record.items()]
        body = f"Claim {record['_id']} requires immediate attention.\n\nSummary:\n\n" + "\n".join(body_lines)

        send_sns_email(subject, body, "sachindawar05@gmail.com")

    # ---------------- PDF DOWNLOAD ----------------
    with open(pdf_summary_path, "rb") as pdf_file:
        st.download_button(
            label="⬇️ Download Claim Triage PDF Report",
            data=pdf_file,
            file_name=f"{record['_id']}.pdf",
            mime="application/pdf",
        )

else:
    st.warning("Please upload a claim PDF to begin triage.")
