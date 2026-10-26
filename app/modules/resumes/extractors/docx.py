from io import BytesIO
from zipfile import ZipFile, BadZipFile
from docx import Document
from docx.text.paragraph import Paragraph
from lxml.etree import XMLSyntaxError
from app.config import MAX_DOCX_BYTES, MAX_DOCX_ENTRIES
from app.modules.resumes.errors import InvalidDocumentError, FileTooLargeError

def block_text(container, depth: int = 0) -> str:
    if depth > 12:
        raise InvalidDocumentError("Documento com tabelas aninhadas demais.")
    texts = []
    for block in container.iter_inner_content():
        if isinstance(block, Paragraph):
            texts.append(block.text)
        else:
            seen = set()
            for row in block.rows:
                cells = []
                for cell in row.cells:
                    if cell._tc not in seen:
                        seen.add(cell._tc)
                        cells.append(block_text(cell, depth + 1))
                texts.append("\t".join(cells))
    return "\n".join(texts)

def extract_docx_text(content: bytes) -> tuple[str, list[str]]:
    try:
        with ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_DOCX_ENTRIES or sum(e.file_size for e in entries) > MAX_DOCX_BYTES:
                raise FileTooLargeError("DOCX excede o limite descompactado.")
            if not {"[Content_Types].xml", "word/document.xml"}.issubset(archive.namelist()):
                raise InvalidDocumentError("O arquivo não contém um documento DOCX.")
            if any(e.flag_bits & 1 for e in entries):
                raise InvalidDocumentError("DOCX criptografado não é suportado.")
        return block_text(Document(BytesIO(content))), [
            "Leitura do corpo do DOCX; cabeçalhos, rodapés e caixas de texto não são incluídos."
        ]
    except (BadZipFile, KeyError, ValueError, XMLSyntaxError, OSError, EOFError) as exc:
        raise InvalidDocumentError("DOCX corrompido ou incompatível.") from exc
