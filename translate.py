import fitz  # PyMuPDF
import os
from dotenv import load_dotenv
import requests
import numpy as np
import re
from loguru import logger
load_dotenv()

AZURE_KEY = os.getenv("AZURE_TRANSLATOR_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_TRANSLATOR_ENDPOINT", 'https://api.cognitive.microsofttranslator.com/')
AZURE_REGION = os.getenv("AZURE_TRANSLATOR_REGION", "centralindia")

def rgb_to_fitz_color(color_int):
    """Convert fitz color integer to RGB tuple"""
    if color_int == 0:
        return (0, 0, 0)  # Black
    
    # Extract RGB components from integer
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF
    
    return (r/255.0, g/255.0, b/255.0)

def get_contrasting_color(bg_color):
    """Get a contrasting color for better visibility"""
    if not bg_color or len(bg_color) != 3:
        return (0, 0, 0)  # Default to black
    
    # Calculate luminance
    r, g, b = bg_color
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    
    # Return black for light backgrounds, white for dark backgrounds
    if luminance > 0.5:
        return (0, 0, 0)  # Black
    else:
        return (1, 1, 1)  # White

def detect_text_alignment(last_text_box, page_width, tolerance=60):
    """
    Detect text alignment based on the last text box position within the page.
    
    Parameters:
    - last_text_box: The last text box (span) in the group
    - page_width: Width of the page
    - tolerance: Pixel tolerance for alignment detection (default: 10)
    
    Returns:
    - 0: Left align
    - 1: Center align  
    - 2: Right align
    """
    if not last_text_box:
        return 0
    
    # Get the bounding box of the last text box
    last_bbox = fitz.Rect(last_text_box['bbox'])
    
    # Extract bbox coordinates
    x_min = last_bbox.x0  # Left edge
    x_max = last_bbox.x1  # Right edge
    
    # Calculate box dimensions
    box_width = x_max - x_min
    box_center = x_min + (box_width / 2)
    
    # Check for left alignment
    if abs(x_min - 0) <= tolerance:
        return 0  # Left align
    
    # Check for right alignment
    elif abs(x_max - page_width) <= tolerance:
        return 2  # Right align
    
    # Check for center alignment
    elif abs(box_center - (page_width / 2)) <= tolerance:
        return 1  # Center align
    
    else:
        # Default to left align if not clearly aligned
        return 0  # Left align


def group_text_spans_combined(
    blocks,
    vertical_weight=1.5,
    horizontal_threshold=15,
    indent_threshold=15,
    heading_size_factor=1.2,
    basic_size_diff=0.2
):
    """
    Unified grouping of text spans that handles:
      1. Basic formatting: font size, color, flags, vertical/horizontal proximity
      2. Advanced layout: left-margin for paragraphs, indent-based sub-items
      3. Heading detection: large font spans grouped together
    """
    text_groups = []

    # 1) Determine heading size threshold
    all_sizes = [span.get('size', 0)
                 for block in blocks if block.get('type') == 0
                 for line in block.get('lines', [])
                 for span in line.get('spans', [])
                 if span.get('text','').strip()]
    median_size = float(np.median(all_sizes)) if all_sizes else 0
    heading_threshold = median_size * heading_size_factor

    for block in blocks:
        if block.get('type') != 0:
            continue

        # Collect per-line stats
        lines = []
        for line in block.get('lines', []):
            spans = [span for span in line.get('spans', []) if span.get('text','').strip()]
            if not spans:
                continue
            boxes = [fitz.Rect(s['bbox']) for s in spans]
            sizes = [s['size'] for s in spans]
            lines.append({
                'spans': spans,
                'left': min(b.x0 for b in boxes),
                'right': max(b.x1 for b in boxes),
                'mid_y': np.mean([b.y0 for b in boxes]),
                'height': np.mean([b.y1 - b.y0 for b in boxes]),
                'avg_size': np.mean(sizes)
            })
        if not lines:
            continue

        # Baseline left margin
        baseline_left = float(np.median([ln['left'] for ln in lines]))

        current = None
        prev_mid_y = None

        for ln in lines:
            is_heading = ln['avg_size'] >= heading_threshold
            indent = ln['left'] - baseline_left > indent_threshold

            # Basic-grouping fallback criteria per line
            def basic_groupable(span, group):
                if not group:
                    return True
                size_ok = abs(span['size'] - group['avg_size']) / group['avg_size'] <= basic_size_diff
                color_ok = span.get('color',0) == group['avg_color']
                flags_ok = span.get('flags',0) == group['flags']
                v_ok = abs(ln['mid_y'] - prev_mid_y if prev_mid_y else 0) < ln['height']*vertical_weight
                h_ok = abs(fitz.Rect(span['bbox']).x0 - (group['bbox'].x1 if group['bbox'] else 0)) < horizontal_threshold
                return size_ok and (v_ok or h_ok) and (color_ok and flags_ok)

            # Decide new block
            new_block = False
            # big vertical gap
            if prev_mid_y is not None and ln['mid_y'] - prev_mid_y > ln['height']*vertical_weight:
                new_block = True
            # horizontal jump
            if current and ln['left'] > current['bbox'].x1 + horizontal_threshold:
                new_block = True
            # paragraph->subitem boundary
            if current and indent and current['type']=='paragraph':
                new_block = True
            # headings stay together
            if current and current.get('is_heading') and is_heading:
                new_block = False
            # fallback: if basic criteria fail for first span
            if current and not basic_groupable(ln['spans'][0], current):
                new_block = True

            # start new group
            if current is None or new_block:
                if current:
                    text_groups.append(current)
                current = {
                    'spans': [],
                    'bbox': None,
                    'avg_size': None,
                    'avg_color': None,
                    'flags': None,
                    'type': 'heading' if is_heading else ('sub-item' if indent else 'paragraph'),
                    'is_heading': is_heading
                }

            # merge spans
            for span in ln['spans']:
                rect = fitz.Rect(span['bbox'])
                span['bbox'] = rect
                if current['avg_size'] is None:
                    current.update({'avg_size': span['size'], 'avg_color': span.get('color',0), 'flags': span.get('flags',0)})
                else:
                    current['avg_size'] = (current['avg_size'] + span['size'])/2
                if current['avg_color'] == span.get('color',0):
                    current['avg_color'] = span.get('color',0)
                current['bbox'] = rect if current['bbox'] is None else (current['bbox'] | rect)
                current['spans'].append(span)

            prev_mid_y = ln['mid_y']

        if current:
            text_groups.append(current)

    return text_groups




def calculate_font_size(font, text, bbox_width, bbox_height, original_size, min_size=6):
    """Calculate appropriate font size to fit text in bbox"""
    if not text.strip():
        return original_size

    font_size = original_size
    max_iterations = 20
    iteration = 0
    
    while iteration < max_iterations:
        try:
            # Estimate number of lines needed
            text_width = font.text_length(text, fontsize=font_size)
            lines_needed = max(1, text_width / (bbox_width * 0.95))
            estimated_height = lines_needed * font_size * 1.2  # 1.2 for line spacing
            
            # Check if text fits both horizontally and vertically
            if estimated_height <= bbox_height * 0.95:
                break
                
            font_size *= 0.999
            if font_size < min_size:
                font_size = min_size
                break
        except:
            # If font measurement fails, use a conservative size
            font_size = min(original_size * 0.99, min_size + 2)
            break
        iteration += 1
    
    return max(font_size, min_size)

def is_long_text_block(text, min_words=10):
    """Check if text block is long enough to warrant justified alignment"""
    return len(text.split()) >= min_words

def open_pdf(input_pdf):
    logger.info("Opening PDF document...")
    return fitz.open(input_pdf)

def embed_font(doc, fontfile):
    logger.info("Embedding font into PDF...")
    fontname = os.path.basename(fontfile).split("-")[0]
    with open(fontfile, 'rb') as f:
        font_data = f.read()
    doc._insert_font(fontfile=fontfile, fontbuffer=font_data)
    font = fitz.Font(fontfile=fontfile)
    logger.info(f"Font '{fontname}' embedded successfully")
    return fontname, font

def process_text_group(page, group, font, fontname, target_language, translate_api, S_min):
    import re
    spans = group['spans']
    combined_bbox = group['bbox']
    avg_size = group['avg_size']
    avg_color = group['avg_color']
    flags = group['flags']
    combined_text = " ".join(span["text"].strip() for span in spans)
    combined_text = re.sub(r'\s+', ' ', combined_text).strip()
    logger.debug(f"[DEBUG] Text block: {combined_text}")
    if not combined_text:
        return
    translated_text = translate_api(combined_text, target_language)
    logger.debug(f"[DEBUG] Translated text: {translated_text}")
    translated_text = re.sub(r'\s+', ' ', translated_text).strip()
    text_color = rgb_to_fitz_color(avg_color)
    if sum(text_color) > 2.7:
        text_color = (0, 0, 0)
    last_text_box = spans[-1]
    page_width = page.rect.width
    alignment = detect_text_alignment(last_text_box, page_width)
    if is_long_text_block(combined_text) and alignment == 0:
        alignment = 3  # Justified for long text blocks
    font_size = calculate_font_size(
        font, translated_text,
        combined_bbox.width, combined_bbox.height,
        avg_size, S_min
    )
    alignment_css_map = {
        0: "left",
        1: "center",
        2: "right",
        3: "justify"
    }
    alignment_css = alignment_css_map.get(alignment, "left")
    css_style = f"""
    body {{
        font-family: '{fontname}', Arial, sans-serif;
        font-size: {font_size}px;
        color: rgb({int(text_color[0]*255)}, {int(text_color[1]*255)}, {int(text_color[2]*255)});
        margin: 0;
        padding: 2px;
        line-height: 1.2;
        text-align: {alignment_css};
        font-weight: normal;
        font-style: normal;
        word-wrap: break-word;
        overflow-wrap: break-word;
        white-space: pre-wrap;
        hyphens: auto;
        {'text-justify: inter-word;' if alignment == 3 else ''}
        {'word-spacing: 0.1em;' if alignment == 3 else ''}
    }}
    """
    page.draw_rect(combined_bbox, color=(1, 1, 1), fill=True)
    try:
        page.insert_htmlbox(
            combined_bbox,
            translated_text,
            css=css_style,
            scale_low=0.4,
            overlay=True
        )
    except Exception as e:
        logger.error(f"HTML insertion failed for '{combined_text[:30]}...': {e}")
        try:
            pymupdf_alignment = 0 if alignment == 3 else alignment
            fit_font_size = font_size
            for attempt in range(3):
                rc = page.insert_textbox(
                    combined_bbox,
                    translated_text,
                    fontname=fontname,
                    fontsize=fit_font_size,
                    color=text_color,
                    align=pymupdf_alignment,
                    wrap=1,
                    border_width=0
                )
                if rc >= 0:
                    break
                fit_font_size *= 0.95
        except Exception as e2:
            logger.error(f"Textbox insertion failed: {e2}")

def process_pages(doc, font, fontname, target_language, translate_api, S_min):
    logger.info("Processing all pages in PDF...")
    for page_num, page in enumerate(doc):
        logger.info(f"Processing page {page_num + 1}...")
        page_rect = page.rect
        page_width = page_rect.width
        text_dict = page.get_text("dict")
        blocks = text_dict["blocks"]
        text_groups = group_text_spans_combined(blocks)
        for group in text_groups:
            process_text_group(page, group, font, fontname, target_language, translate_api, S_min)

def save_pdf(doc, output_pdf):
    logger.info("Saving translated PDF...")
    doc.save(
        output_pdf,
        garbage=4,
        clean=True,
        deflate=True,
        deflate_images=True,
        deflate_fonts=True,
        pretty=True,
        encryption=fitz.PDF_ENCRYPT_NONE
    )
    logger.info(f"Translated PDF saved successfully: {output_pdf}")

def translate_pdf(input_pdf, output_pdf, translate_api, target_language, fontfile, S_min=6):
    doc = open_pdf(input_pdf)
    try:
        fontname, font = embed_font(doc, fontfile)
    except Exception as e:
        logger.error(f"Error embedding font: {e}")
        doc.close()
        return
    process_pages(doc, font, fontname, target_language, translate_api, S_min)
    try:
        save_pdf(doc, output_pdf)
    except Exception as e:
        logger.error(f"Error saving PDF: {e}")
    finally:
        doc.close()

# Translate API function (unchanged)
def translate_api(text: str, target_lang: str) -> str:
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
        translated = data[0]["translations"][0]["text"]
        return translated
    except Exception as e:
        logger.warning(f"[translate_api] warning, falling back to original text: {e}")
        return text

# Example usage
if __name__ == "__main__":
    load_dotenv()
    AZURE_KEY = os.getenv("AZURE_TRANSLATOR_KEY")
    AZURE_ENDPOINT = os.getenv("AZURE_TRANSLATOR_ENDPOINT", 'https://api.cognitive.microsofttranslator.com/')
    AZURE_REGION = os.getenv("AZURE_TRANSLATOR_REGION", "centralindia")
    
    translate_pdf(
        "PIB_DRDO.pdf",
        "PIB_DRDO_HI.pdf",
        translate_api,
        "hi",  # Target language: Hindi
        r"D:\Business\Sample_Set\pdf-translation\indic-fonts\NotoSansDevanagari-VariableFont_wdth,wght.ttf"  # Path to static font folder
    )