"""
Markdown parser — strips all Markdown syntax and returns clean plain text.

Two-step process:
  1. markdown → HTML  (via the `markdown` library)
  2. HTML  → plain text  (via a simple tag-stripping regex)

This preserves heading hierarchy as blank-line-separated text blocks,
which the chunker then splits on paragraph boundaries.
"""
import logging
import re
from pathlib import Path

import markdown as md_lib
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Matches any HTML tag
_TAG_RE = re.compile(r"<[^>]+>")
# Collapse 3+ consecutive newlines to 2
_MULTI_NL = re.compile(r"\n{3,}")


def _strip_html(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    # Decode common HTML entities
    text = (
        text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&nbsp;", " ")
    )
    return _MULTI_NL.sub("\n\n", text).strip()


async def parse_markdown(file_path: str) -> list[Document]:
    path = Path(file_path)

    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            raw = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Cannot decode '{path.name}'.")

    html = md_lib.markdown(
        raw,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    plain = _strip_html(html)

    doc = Document(
        page_content=plain,
        metadata={"source": path.name, "original_format": "markdown"},
    )
    logger.info("Markdown parsed | file=%s chars=%d", path.name, len(plain))
    return [doc]
