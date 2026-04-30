"""Text chunking utilities for splitting documents into embeddable segments."""


def chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> list[str]:
    """
    Split text into overlapping chunks suitable for embedding.

    Uses character-based splitting with paragraph-aware boundaries.
    Falls back to sentence splitting, then hard character split.

    Args:
        text: The input text to chunk.
        max_chars: Maximum characters per chunk (~512 tokens ≈ 1500 chars).
        overlap: Number of overlapping characters between consecutive chunks.

    Returns:
        List of text chunks.
    """
    if not text or len(text) <= max_chars:
        return [text] if text else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_chars

        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        # Try to break at a paragraph boundary
        break_point = text.rfind('\n\n', start, end)
        if break_point == -1 or break_point <= start:
            # Try sentence boundary
            break_point = text.rfind('. ', start, end)
            if break_point == -1 or break_point <= start:
                # Hard break
                break_point = end
            else:
                break_point += 1  # Include the period

        chunk = text[start:break_point].strip()
        if chunk:
            chunks.append(chunk)

        # Move start forward with overlap
        start = max(break_point - overlap, start + 1)

    return chunks
