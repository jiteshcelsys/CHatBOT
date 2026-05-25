"""
Text cleaner — normalises raw extracted text before chunking.

Pipeline (applied in order):
  1. Strip null bytes and non-printable control characters.
  2. Normalise Unicode to NFC (handles accented chars from PDFs).
  3. Collapse runs of whitespace within a line to a single space.
  4. Collapse 3+ consecutive blank lines to 2 (paragraph separator).
  5. Strip leading/trailing whitespace per line.
  6. Remove lines that are purely punctuation or whitespace (garbage lines
     common in scanned PDFs: "- - - - -", "· · ·", page numbers).
  7. Trim the whole document.

The cleaner is intentionally non-destructive: it does NOT remove stopwords,
stem, or lower-case — that would degrade embedding quality.
"""
import logging
import re
import unicodedata
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Control chars except \t, \n, \r
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Collapse internal whitespace (spaces, tabs) in a line
_INLINE_WS = re.compile(r"[ \t]+")
# 3+ blank lines → 2 blank lines
_MULTI_BLANK = re.compile(r"\n{3,}")
# Lines that are only punctuation/whitespace/digits (page numbers, dividers)
_JUNK_LINE = re.compile(r"^\s*[\W\d]+\s*$")


def clean_text(text: str) -> str:
    # 1. Remove control characters
    text = _CONTROL_CHARS.sub("", text)

    # 2. NFC normalisation
    text = unicodedata.normalize("NFC", text)

    # 3. Per-line cleanup
    lines = text.split("\n")
    cleaned: list[str] = []
    for line in lines:
        line = _INLINE_WS.sub(" ", line).strip()
        # Keep the line unless it is pure punctuation/numbers AND short (< 6 chars)
        if _JUNK_LINE.match(line) and len(line) < 6:
            continue
        cleaned.append(line)

    # 4. Rejoin and collapse excess blank lines
    text = "\n".join(cleaned)
    text = _MULTI_BLANK.sub("\n\n", text)

    return text.strip()


def clean_documents(documents: list[Document]) -> list[Document]:
    """Apply clean_text to every Document in-place; drop docs that become empty."""
    result: list[Document] = []
    for doc in documents:
        cleaned = clean_text(doc.page_content)
        if cleaned:
            doc.page_content = cleaned
            result.append(doc)
        else:
            logger.debug("Dropped empty document after cleaning: %s", doc.metadata.get("source"))
    logger.info("Cleaning complete | input=%d output=%d docs", len(documents), len(result))
    return result
