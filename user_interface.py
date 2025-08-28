import streamlit as st
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai
import tempfile
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# -------------------------------
# API Key Setup
# -------------------------------
api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("No API key found. Please set GEMINI_API_KEY in secrets or .env file.")
else:
    genai.configure(api_key=api_key)

# -------------------------------
# Streamlit App UI
# -------------------------------
st.set_page_config(page_title="Substation Inspection", layout="wide")

st.title("⚡ Substation Inspection Report Generator")

with st.sidebar:
    st.header("🔧 Settings")
    inspection_days = st.number_input(
        "Next Inspection in (days)",
        min_value=1,
        max_value=30,
        value=7,
        step=1
    )

uploaded_files = st.file_uploader(
    "📂 Upload Substation Images",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files:
    st.subheader("📸 Uploaded Images")
    cols = st.columns(3)
    for i, uploaded_file in enumerate(uploaded_files):
        img = Image.open(uploaded_file)
        with cols[i % 3]:
            st.image(img, caption=f"Image {i+1}", use_container_width=True)

    # Save images temporarily
    temp_files = []
    for file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(file.getvalue())
            temp_files.append(tmp.name)

    if st.button("🔍 Generate Report"):
        with st.spinner("Analyzing images..."):
            # Prepare prompt
            prompt = f"""
            You are an inspection assistant. 
            Analyze the uploaded images of a substation. 
            Detect the components (Insulators, Towers) and classify each as Damaged or Intact.
            Then generate a structured inspection report in clean Markdown.

            Today's date: {datetime.now().strftime("%Y-%m-%d")}
            Next inspection date: {(datetime.now() + timedelta(days=inspection_days)).strftime("%Y-%m-%d")}

            Format the report like this:

            ## Substation Inspection Summary

            **Date of Inspection:** YYYY-MM-DD  
            **Substation Name/ID:** Auto-generated if not available  

            **Components Inspected:** Insulators, Towers  

            **Inspection Results:**

            | Component   | Quantity Detected | Intact | Damaged |
            |-------------|------------------:|-------:|--------:|
            | Towers      | X                 | Y      | Z       |
            | Insulators  | X                 | Y      | Z       |

            **Summary of Findings:**  
            (Write findings clearly here.)

            **Maintenance Recommendations:**  
            (Give actionable advice.)

            **Next Inspection Date:** YYYY-MM-DD
            """

            model = genai.GenerativeModel("gemini-1.5-flash")

            try:
                response = model.generate_content(
                    [prompt] + [genai.upload_file(file) for file in temp_files]
                )
                report = response.text

                st.success("✅ Report generated successfully!")
                st.markdown(report)

                # -------------------------------
                # Convert Report to PDF
                # -------------------------------
                pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                c = canvas.Canvas(pdf_file.name, pagesize=A4)
                width, height = A4

                # Add title
                c.setFont("Helvetica-Bold", 14)
                c.drawString(1 * inch, height - 1 * inch, "Substation Inspection Report")

                # Add report text
                c.setFont("Helvetica", 10)
                text_obj = c.beginText(1 * inch, height - 1.5 * inch)
                for line in report.split("\n"):
                    text_obj.textLine(line)
                c.drawText(text_obj)
                c.save()

                # Download button for PDF
                with open(pdf_file.name, "rb") as f:
                    st.download_button(
                        label="📥 Download Report (PDF)",
                        data=f,
                        file_name=f"inspection_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error(f"Error: {e}")
