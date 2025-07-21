# PDF Translation App

A tool for translating PDF documents into multiple Indian languages using the Azure Translator API, with preservation of layout and font support for Indic scripts. Includes a Streamlit web interface for easy use and a modular Python backend for batch or CLI processing.

---

## Features
- **PDF to PDF translation**: Translates the text in a PDF and outputs a new PDF with the same layout.
- **Indic font support**: Uses Noto fonts for accurate rendering of Indian languages.
- **Streamlit web app**: Upload a PDF, select a target language, and download the translated PDF.
- **Batch/CLI usage**: Run translation from the command line for automation or scripting.
- **Detailed logging/reporting**: Logs translation statistics, timing, and text counts for each run.

---

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/anindyamitra2002/pdf-translation.git
   cd pdf-translation
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root with your Azure Translator credentials:
   ```env
   AZURE_TRANSLATOR_KEY=your_azure_key
   AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com/
   AZURE_TRANSLATOR_REGION=your_region
   ```

4. **Download Noto fonts**
   Place the required Noto fonts in the `indic-fonts/` directory (see code for font file names).

---

## Usage

### Streamlit Web App

1. Start the app:
   ```bash
   streamlit run app.py
   ```
2. Open the web browser (usually at http://localhost:8501)
3. Upload a PDF, select the target language, and click "Translate PDF".
4. View original and translated PDFs side by side. Download the translated PDF.

### Command Line (Batch) Usage

You can also use the translation pipeline directly from Python or the command line:

```python
from translate import translate_pdf, translate_api
translate_pdf(
    input_pdf="input.pdf",
    output_pdf="output_hi.pdf",
    translate_api=translate_api,
    target_language="hi",  # Hindi
    fontfile="indic-fonts/NotoSansDevanagari-VariableFont_wdth,wght.ttf"
)
```

---

## Environment Variables
- `AZURE_TRANSLATOR_KEY`: Your Azure Translator API key
- `AZURE_TRANSLATOR_ENDPOINT`: API endpoint (default: https://api.cognitive.microsofttranslator.com/)
- `AZURE_TRANSLATOR_REGION`: Azure region (e.g., centralindia)

---

## PDF Translation Report

After each translation, a detailed report is logged. Example:

```
========= PDF TRANSLATION REPORT =========
[INFO] Total blocks translated: 45
[INFO] Original text: 2235 chars, 334 words
[INFO] Translated text: 2254 chars, 369 words
[INFO] Total translation API latency: 11.75 sec
[INFO] Step timings (sec): open=0.00, font=0.00, pages=12.38, save=0.15
[INFO] Total pipeline time: 12.55 sec
[INFO] ==========================================
```

- **Total blocks translated**: Number of text groups processed in the PDF.
- **Original/Translated text**: Character and word counts before and after translation.
- **Total translation API latency**: Time spent waiting for the translation API.
- **Step timings**: Time taken for each pipeline step (open, font, pages, save).
- **Total pipeline time**: End-to-end time for the translation process.

---

## Notes
- For best results, use high-quality, text-based PDFs (not scanned images).
- The app supports major Indian languages and scripts (see font mapping in code).
- For troubleshooting, check the logs for detailed error and timing information.
