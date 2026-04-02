from PyPDF2 import PdfReader
from PIL import Image
import os

def summarize_text(input_source, get_ai_summary_fn):
    """Universal summarization (Text/PDF/Image)."""
    text = ""
    detected_type = "Unknown"
    
    if isinstance(input_source, str) and os.path.exists(input_source):
        # File Source
        ext = input_source.split('.')[-1].lower()
        if ext == 'pdf':
            reader = PdfReader(input_source)
            text = " ".join([p.extract_text() for p in reader.pages])
            detected_type = "PDF Document"
        elif ext in ['jpg', 'png']:
            # OCR would go here (keeping placeholder logic for now)
            text = "Image content extracted..."
            detected_type = "Image (OCR)"
        elif ext == 'txt':
            with open(input_source, 'r', encoding='utf-8') as f:
                text = f.read()
            detected_type = "Text File"
    else:
        # Raw Text
        text = input_source
        detected_type = "Plain Text"

    ai_summary = get_ai_summary_fn(text)
    
    return {
        "summary": ai_summary,
        "orig_words": len(text.split()) if text else 0,
        "detected_type": detected_type
    }
