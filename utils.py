import os
import glob
from pathlib import Path
import requests
from dotenv import load_dotenv

# Import the translate_pdf function from the other script
from translate import translate_pdf

# Load environment variables
load_dotenv()

# Azure Translator configuration
AZURE_KEY = os.getenv("AZURE_TRANSLATOR_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_TRANSLATOR_ENDPOINT", 'https://api.cognitive.microsofttranslator.com/')
AZURE_REGION = os.getenv("AZURE_TRANSLATOR_REGION", "centralindia")

def translate_api(text: str, target_lang: str) -> str:
    """
    Translate a piece of text via Azure Translator.
    - text: the source text string
    - target_lang: two‑letter target language code, e.g. 'fr', 'hi', 'kn'
    Returns the translated string (or original text on failure).
    """
    # Build request URL
    url = f"{AZURE_ENDPOINT}/translate?api-version=3.0&to={target_lang}"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Ocp-Apim-Subscription-Region": AZURE_REGION,
        "Content-Type": "application/json"
    }
    payload = [{"Text": text}]
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # Azure returns a list-of-list structure; grab the first translation
        translated = data[0]["translations"][0]["text"]
        return translated
    except Exception as e:
        # Log or print if you like:
        print(f"[translate_api] warning, falling back to original text: {e}")
        return text

def get_font_name_from_path(font_path):
    """
    Extract font name from font file path.
    Takes the filename, removes extension, splits by '-' and takes the first element.
    """
    font_filename = os.path.basename(font_path)
    font_name_without_ext = os.path.splitext(font_filename)[0]
    font_name = font_name_without_ext.split('-')[0]
    return font_name

def generate_output_filename(input_filename, lang_code):
    """
    Generate output filename based on input filename and language code.
    If input filename ends with '_org', replace with '_{lang_code}'
    Otherwise, add '_{lang_code}' at the end.
    """
    name_without_ext = os.path.splitext(input_filename)[0]
    extension = os.path.splitext(input_filename)[1]
    
    if name_without_ext.endswith('_org'):
        # Replace _org with _{lang_code}
        output_name = name_without_ext[:-4] + f'_{lang_code}'
    else:
        # Add _{lang_code} at the end
        output_name = name_without_ext + f'_{lang_code}'
    
    return output_name + extension

def process_pdf_translations(input_folder, output_folder, language_font_mapping):
    """
    Process all PDFs in input folder and translate them to specified languages.
    
    Parameters:
    - input_folder (str): Path to folder containing input PDFs
    - output_folder (str): Path to folder where translated PDFs will be saved
    - language_font_mapping (dict): Dictionary mapping language codes to font file paths
    """
    # Create output folder if it doesn't exist
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files in input folder
    pdf_files = glob.glob(os.path.join(input_folder, "*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {input_folder}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF file
    for pdf_file in pdf_files:
        input_filename = os.path.basename(pdf_file)
        print(f"\n{'='*60}")
        print(f"Processing: {input_filename}")
        print(f"{'='*60}")
        
        # Translate to each language
        for lang_code, font_path in language_font_mapping.items():
            try:
                print(f"\nTranslating to {lang_code}...")
                
                # Generate output filename
                output_filename = generate_output_filename(input_filename, lang_code)
                output_path = os.path.join(output_folder, output_filename)
                
                # Extract font name from font path
                font_name = get_font_name_from_path(font_path)
                
                # Check if font file exists
                if not os.path.exists(font_path):
                    print(f"Error: Font file not found: {font_path}")
                    continue
                
                print(f"  Input: {input_filename}")
                print(f"  Output: {output_filename}")
                print(f"  Language: {lang_code}")
                print(f"  Font: {font_name} ({font_path})")
                
                # Translate the PDF
                translate_pdf(
                    input_pdf=pdf_file,
                    output_pdf=output_path,
                    translate_api=translate_api,
                    target_language=lang_code,
                    fontfile=font_path,
                    fontname=font_name
                )
                
                print(f"  ✓ Successfully translated to {lang_code}")
                
            except Exception as e:
                print(f"  ✗ Error translating {input_filename} to {lang_code}: {e}")
                continue
    
    print(f"\n{'='*60}")
    print("Translation pipeline completed!")
    print(f"{'='*60}")

def main():
    """
    Main function to run the PDF translation pipeline.
    """
    # Configuration
    input_folder = "/teamspace/studios/this_studio/samples"
    output_folder = "/teamspace/studios/this_studio/translated_samples_kn"
    
    # Language to font file mapping
    language_font_mapping = {
        # "hi": "/teamspace/studios/this_studio/pdf_translator/NotoSansDevanagari-VariableFont_wdth,wght.ttf",
        "kn": "/teamspace/studios/this_studio/pdf_translator/NotoSansKannada-VariableFont_wdth,wght.ttf",
        # "te": "/teamspace/studios/this_studio/pdf_translator/NotoSansTelugu-VariableFont_wdth,wght.ttf",
        # "ta": "/teamspace/studios/this_studio/pdf_translator/NotoSansTamil-VariableFont_wdth,wght.ttf",
        # "bn": "/teamspace/studios/this_studio/pdf_translator/NotoSansBengali-VariableFont_wdth,wght.ttf",
        # "gu": "/teamspace/studios/this_studio/pdf_translator/NotoSansGujarati-VariableFont_wdth,wght.ttf",
        # "mr": "/teamspace/studios/this_studio/pdf_translator/NotoSansDevanagari-VariableFont_wdth,wght.ttf",  # Marathi uses Devanagari
        # "pa": "/teamspace/studios/this_studio/pdf_translator/NotoSansGurmukhi-VariableFont_wdth,wght.ttf",
        # "or": "/teamspace/studios/this_studio/pdf_translator/NotoSansOriya-VariableFont_wdth,wght.ttf",
        # "ml": "/teamspace/studios/this_studio/pdf_translator/NotoSansMalayalam-VariableFont_wdth,wght.ttf"
    }
    
    print("Starting PDF Translation Pipeline...")
    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Languages to translate: {list(language_font_mapping.keys())}")
    
    # Validate input folder exists
    if not os.path.exists(input_folder):
        print(f"Error: Input folder does not exist: {input_folder}")
        return
    
    # Validate font files exist
    missing_fonts = []
    for lang_code, font_path in language_font_mapping.items():
        if not os.path.exists(font_path):
            missing_fonts.append(f"{lang_code}: {font_path}")
    
    if missing_fonts:
        print("Warning: The following font files are missing:")
        for missing in missing_fonts:
            print(f"  - {missing}")
        print("Translation will skip languages with missing fonts.")
    
    # Process translations
    process_pdf_translations(input_folder, output_folder, language_font_mapping)

if __name__ == "__main__":
    main()