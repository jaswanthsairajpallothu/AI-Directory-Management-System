import os
from PyPDF2 import PdfReader
from docx import Document

def extract_text(path: str) -> str:
    _, ext = os.path.splitext(path.lower())

    if ext == '.pdf':
        try:
            reader = PdfReader(path)
            return '\n'.join(page.extract_text() or '' for page in reader.pages)
        except Exception:
            return ''

    if ext == '.docx':
        try:
            doc = Document(path)
            return '\n'.join(p.text for p in doc.paragraphs if p.text)
        except Exception:
            return ''

    if ext == '.txt':
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ''

    if ext in ['.png', '.jpg', '.jpeg']:
        # --- CRITICAL FIX ---
        # Do not extract metadata as text.
        # This was confusing the text classifier.
        # The analyzer will handle images based on extension.
        return ''
