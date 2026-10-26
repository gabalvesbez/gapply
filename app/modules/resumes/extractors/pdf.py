from io import BytesIO
from pypdf import PdfReader
from pypdf.errors import PyPdfError
from app.modules.resumes.errors import InvalidDocumentError, ProtectedDocumentError

def extract_pdf_text(content: bytes) -> tuple[str, list[str]]:
    if not content.startswith(b"%PDF-"):
        raise InvalidDocumentError("O conteúdo não é um PDF válido.")
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise ProtectedDocumentError("Envie um PDF sem criptografia/senha.")
        if len(reader.pages) > 100:
            raise InvalidDocumentError("Máximo de 100 páginas por currículo.")
        texts, warnings = [], []
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if not text.strip():
                warnings.append(f"Página {number} sem texto extraível; OCR pode ser necessário.")
            texts.append(text)
        return "\n\n".join(texts), warnings
    except (PyPdfError, ValueError, TypeError, KeyError, IndexError, RecursionError) as exc:
        raise InvalidDocumentError("Não foi possível ler a estrutura do PDF.") from exc
