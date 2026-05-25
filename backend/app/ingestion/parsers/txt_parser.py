"""Plain-text parser — reads UTF-8 with BOM-stripping fallback."""
import logging
from pathlib import Path

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


async def parse_txt(file_path: str) -> list[Document]:
    path = Path(file_path)

    # Try UTF-8 first, fall back to latin-1 for legacy files
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Cannot decode '{path.name}' with supported encodings.")

    doc = Document(
        page_content=text,
        metadata={"source": path.name, "encoding": encoding},
    )
    logger.info("TXT parsed | file=%s chars=%d", path.name, len(text))
    return [doc]
