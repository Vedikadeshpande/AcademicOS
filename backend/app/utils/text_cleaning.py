"""Text cleaning utilities for extracted PDF/PPT content."""
import re


def clean_text(text: str) -> str:
    """Clean raw extracted text by removing junk characters and normalizing whitespace."""
    if not text:
        return ""

    # Remove common header/footer patterns
    text = re.sub(r'(Page\s*\d+\s*(of\s*\d+)?)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(Slide\s*\d+)', '', text, flags=re.IGNORECASE)

    # Remove excessive special characters but keep common punctuation
    text = re.sub(r'[^\w\s.,;:!?\-\'\"()/&@#%+=$\[\]{}]', ' ', text)

    # Collapse multiple newlines into double newline (paragraph breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Collapse multiple spaces into single space
    text = re.sub(r'[ \t]+', ' ', text)

    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    # Remove lines that are just whitespace or very short (likely artifacts)
    lines = [line for line in text.split('\n') if len(line.strip()) > 2 or line.strip() == '']
    text = '\n'.join(lines)

    return text.strip()


def normalize_for_comparison(text: str) -> str:
    """Normalize text for topic matching — lowercase, remove punctuation."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
