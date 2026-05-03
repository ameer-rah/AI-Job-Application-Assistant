from pathlib import Path


def extract_text(path: str) -> str:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        return _from_pdf(path)
    elif suffix == ".docx":
        return _from_docx(path)
    else:
        raise ValueError(f"Unsupported file type '{suffix}'. Only .pdf and .docx are supported.")


def _from_pdf(path: str) -> str:
    import pdfplumber

    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    if not pages:
        raise ValueError(f"Could not extract any text from '{path}'. The PDF may be image-based.")
    return "\n\n".join(pages)


def _from_docx(path: str) -> str:
    from docx import Document

    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        raise ValueError(f"Could not extract any text from '{path}'.")
    return "\n".join(paragraphs)
