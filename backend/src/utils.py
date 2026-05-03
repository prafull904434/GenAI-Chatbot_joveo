import re
from typing import List


def clean_text(text: str) -> str:
      # normalize whitespace in extracted page text
    return re.sub(r"\s+", " ", (text or "")).strip()


def split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    if not text:
        return []

    length = len(text)
    if length <= chunk_size:
        return [text]

    chunks: List[str] = []
    pos = 0

# sliding window chunking with overlap
    while pos < length:
        end = min(pos + chunk_size, length)
        piece = text[pos:end].strip()

        if piece:
            chunks.append(piece)
        if end >= length:
            break
        pos = end - overlap if overlap < chunk_size else end

    return chunks