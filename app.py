import streamlit as st
import tempfile
import os
import shutil
from pathlib import Path
from translate import translate_pdf, translate_api
import base64
st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 2 rem;
                    padding-left: 2rem;
                    padding-right: 2rem;
                }
        </style>
        """, unsafe_allow_html=True)
# Helper to save uploaded file to a temp location
def save_uploaded_file(uploaded_file, suffix=""):
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.read())
        return tmp_file.name

# Helper to save uploaded font folder (as zip or files)
def save_uploaded_font_folder(uploaded_files):
    temp_dir = tempfile.mkdtemp()
    for uploaded_file in uploaded_files:
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
    return temp_dir

# Dictionary mapping language codes to font file paths
LANG_FONT_FILES = {
    "en": "indic-fonts/NotoSans-VariableFont_wdth,wght.ttf",
    "hi": "indic-fonts/NotoSansDevanagari-VariableFont_wdth,wght.ttf",
    "bn": "indic-fonts/NotoSansBengali-VariableFont_wdth,wght.ttf",
    "kn": "indic-fonts/NotoSansKannada-VariableFont_wdth,wght.ttf",
    "mr": "indic-fonts/NotoSansDevanagari-VariableFont_wdth,wght.ttf",  # Marathi uses Devanagari
    "ta": "indic-fonts/NotoSansTamil-VariableFont_wdth,wght.ttf",
    "te": "indic-fonts/NotoSansTelugu-VariableFont_wdth,wght.ttf",
    "gu": "indic-fonts/NotoSansGujarati-VariableFont_wdth,wght.ttf",
    "pa": "indic-fonts/NotoSansGurmukhi-VariableFont_wdth,wght.ttf",
    "or": "indic-fonts/NotoSansOriya-VariableFont_wdth,wght.ttf",
    "ml": "indic-fonts/NotoSansMalayalam-VariableFont_wdth,wght.ttf",
    "as": "indic-fonts/NotoSansBengali-VariableFont_wdth,wght.ttf",  # Assamese uses Bengali script
}

def displayPDF(file):
    # Opening file from file path
    with open(file, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    # Embedding PDF in HTML
    pdf_display = F'<iframe src="data:application/pdf;base64,{base64_pdf}" width="500" height="800" type="application/pdf"></iframe>'
    # Displaying File
    st.markdown(pdf_display, unsafe_allow_html=True)

st.set_page_config(page_title="PDF Translator", layout="wide")
st.title("PDF Translator App")

# Remove previous PDF display logic and use columns for side-by-side display
col1, col2 = st.columns(2)

with st.sidebar:
    st.header("Configuration")
    uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"])
    target_language = st.selectbox("Select Target Language", [
        ("hi", "Hindi"),
        ("en", "English"),
        ("bn", "Bengali"),
        ("kn", "Kannada"),
        ("mr", "Marathi"),
        ("ta", "Tamil"),
        ("te", "Telugu"),
        ("gu", "Gujarati"),
        ("pa", "Punjabi"),
        ("or", "Odia"),
        ("ml", "Malayalam"),
        ("as", "Assamese")
    ], format_func=lambda x: x[1])
    target_language_code = target_language[0]
    font_files = None  # Remove font file uploader, use dictionary
    start_button = st.button("Translate PDF")

uploaded_pdf_bytes = None
if uploaded_pdf:
    uploaded_pdf_bytes = uploaded_pdf.read()

# Prepare temp files for both PDFs
original_pdf_path = None
if uploaded_pdf_bytes:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_pdf_bytes)
        original_pdf_path = tmp_file.name

translated_pdf_ready = False
output_pdf_path = None

if start_button and uploaded_pdf_bytes:
    with st.spinner("Translating PDF, please wait..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_pdf_bytes)
            input_pdf_path = tmp_file.name
        font_file_path = LANG_FONT_FILES.get(target_language_code)
        if not font_file_path or not os.path.exists(font_file_path):
            st.error(f"Font file for language '{target_language_code}' not found: {font_file_path}")
            output_pdf_path = None
        else:
            output_pdf_path = tempfile.mktemp(suffix="_translated.pdf")
            progress_bar = st.progress(0)
            def progress_callback(current, total):
                progress_bar.progress(min(int(current/total*100), 100))
            import types
            orig_translate_pdf = translate_pdf
            def translate_pdf_with_progress(*args, **kwargs):
                kwargs['progress_callback'] = progress_callback
                return orig_translate_pdf(*args, **kwargs)
            try:
                translate_pdf(
                    input_pdf_path,
                    output_pdf_path,
                    translate_api,
                    target_language_code,
                    font_file_path
                )
                progress_bar.progress(100)
                st.success("Translation complete!")
                translated_pdf_ready = True
            except Exception as e:
                st.error(f"Translation failed: {e}")
                output_pdf_path = None
                translated_pdf_ready = False
else:
    translated_pdf_ready = False

# Show PDFs side by side in columns
with col1:
    st.subheader("Original PDF")
    if original_pdf_path and os.path.exists(original_pdf_path):
        displayPDF(original_pdf_path)
    else:
        st.info("Please upload a PDF to view it here.")

with col2:
    st.subheader("Translated PDF")
    if output_pdf_path and os.path.exists(output_pdf_path):
        displayPDF(output_pdf_path)
    else:
        st.info("The translated PDF will appear here after translation.")

# Clean up temp files on session end
@st.cache_resource
def cleanup_temp_files(paths):
    for p in paths:
        try:
            if p and os.path.isdir(p):
                shutil.rmtree(p)
            elif p and os.path.isfile(p):
                os.remove(p)
        except Exception:
            pass
    return True

# Only clean up if paths are defined
if 'original_pdf_path' in locals() and 'output_pdf_path' in locals() and original_pdf_path and output_pdf_path:
    cleanup_temp_files([original_pdf_path, output_pdf_path]) 