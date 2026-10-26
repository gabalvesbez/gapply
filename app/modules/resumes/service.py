from pathlib import PurePosixPath
from app.config import MAX_UPLOAD_BYTES, ALLOWED_EXTENSIONS
from app.modules.resumes.errors import FileTooLargeError, UnsupportedFormatError, InvalidDocumentError, NoTextFoundError
from app.modules.resumes.extractors.pdf import extract_pdf_text
from app.modules.resumes.extractors.docx import extract_docx_text
from app.modules.resumes.schemas import ResumeTextResponse

def extract_resume_text(filename: str, content: bytes) -> ResumeTextResponse:
    name = PurePosixPath(filename.replace("\\", "/")).name
    extension = PurePosixPath(name).suffix.lower()
    if not content:
        raise InvalidDocumentError("O arquivo está vazio.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise FileTooLargeError("O arquivo deve ter no máximo 10 MiB.")
    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedFormatError("Envie um arquivo .pdf ou .docx.")
    text, warnings = (extract_pdf_text if extension == ".pdf" else extract_docx_text)(content)
    if not text.strip():
        raise NoTextFoundError("Não encontramos texto. O documento pode precisar de OCR.")
    return ResumeTextResponse(filename=name, format=extension[1:], text=text.strip(), warnings=warnings)
