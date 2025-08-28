import streamlit as st
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai
import tempfile
from PIL import Image
from ultralytics import YOLO

# -------------------------------
# API Key setup
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
# Streamlit UI
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

# Load YOLO model (use your trained model path)
MODEL_PATH = "yolo_substation.pt"  # change to your trained model
model = YOLO(MODEL_PATH)

detected_files = []

if uploaded_files:
    st.subheader("📸 Uploaded & Detected Images")

    cols = st.columns(3)
    for i, uploaded_file in enumerate(uploaded_files):
        img = Image.open(uploaded_file)

        # Save original temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            img.save(tmp.name)
            original_path = tmp.name

        # Run YOLO detection
        results = model.predict(original_path, save=False, conf=0.3)

        # Save detected image
        detected_path = original_path.replace(".png", "_detected.png")
        results[0].plot(save=True, filename=detected_path)

        detected_files.append(detected_path)

        # Show original and detected side by side
        with cols[i % 3]:
            st.image(img, caption=f"Original {i+1}", use_container_width=True)
            st.image(detected_path, caption=f"Detected {i+1}", use_container_width=True)

    if st.button("🔍 Generate Report"):
        with st.spinner("Analyzing images with Gemini..."):
            # Prepare inspection prompt
            prompt = f"""
            You are an inspection assistant. 
            Analyze the detected substation components. 
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

            try:
                model_gemini = genai.GenerativeModel("gemini-1.5-flash")
                response = model_gemini.generate_content(
                    [prompt] + [genai.upload_file(file) for file in detected_files]
                )
                report = response.text

                st.success("✅ Report generated successfully!")
                st.markdown(report)

                # Download option
                st.download_button(
                    label="📥 Download Report",
                    data=report,
                    file_name=f"inspection_report_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown"
                )
            except Exception as e:
                st.error(f"Error: {e}")
