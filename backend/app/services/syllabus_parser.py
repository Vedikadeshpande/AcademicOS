"""
Syllabus parser — extracts units and topics from raw syllabus text.

Handles many input formats:
  1. "Unit 1: Title" followed by topics on next lines
  2. "Title: topic1, topic2, topic3" (colon-separated)
  3. "Title:" on its own line, with topics on following lines
  4. Multi-line colon format where topics span lines until the next header
  5. Numbered/bulleted topic lists
  6. Mixed formats
"""
import re


def parse_syllabus_text(raw_text: str) -> list[dict]:
    """
    Parse raw syllabus text into structured units and topics.

    Returns:
        List of dicts: [{"title": str, "unit_number": int, "topics": [str]}]
    """
    if not raw_text:
        return []

    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]

    # ── Strategy 1: Detect colon-header format ──
    # Matches "SomeTitle:" with or without content after the colon
    colon_header_re = re.compile(r'^([A-Z][^:,]{2,80}):\s*(.*)', re.IGNORECASE)
    colon_lines = sum(1 for l in lines if colon_header_re.match(l))

    if colon_lines >= 1 and colon_lines >= len(lines) * 0.1:
        result = _parse_colon_format(lines, colon_header_re)
        if result:
            return _clean_units(result)

    # ── Strategy 2: Explicit "Unit N: Title" headers ──
    result = _parse_unit_headers(lines)
    if result:
        return _clean_units(result)

    # ── Strategy 3: Fallback (ALL CAPS headers, etc.) ──
    result = _fallback_parse(lines)
    return _clean_units(result)


def _is_header_line(text: str) -> bool:
    """Heuristic: does this look like a section header rather than content?
    Headers are typically short, title-cased, and don't look like comma-lists of topics."""
    # Too long to be a header
    if len(text) > 100:
        return False
    # Must start with uppercase
    if not text[0].isupper():
        return False
    # If it has many commas, it's probably a topic list, not a header
    if text.count(',') > 2:
        return False
    return True


def _parse_colon_format(lines: list[str], colon_re: re.Pattern) -> list[dict]:
    """
    Parse formats like:
        Introduction:
        History of Deep Learning, Deep Learning applications, ...

        Convolutional Neural Networks: Architectures, convolution layers, LeNet, ...

        Or mixed: some headers have topics inline, some on the next line.
    """
    # Also detect "Unit N: Title" style
    unit_header_re = re.compile(
        r'^(?:Unit|Module|Chapter|Section)\s*[-:]?\s*(\d+)\s*[-:.]?\s*(.*)', re.IGNORECASE
    )

    units = []
    current_unit = None

    for line in lines:
        # Check for explicit "Unit N: Title" header first
        unit_match = unit_header_re.match(line)
        if unit_match:
            num = int(unit_match.group(1))
            title = unit_match.group(2).strip().rstrip(':').strip()
            if ',' in title:
                parts = _split_topics(title)
                current_unit = {
                    "title": f"Unit {num}",
                    "unit_number": num,
                    "topics": parts,
                }
            else:
                current_unit = {
                    "title": title or f"Unit {num}",
                    "unit_number": num,
                    "topics": [],
                }
            units.append(current_unit)
            continue

        # Check for colon-format header: "SomeName: stuff" or "SomeName:"
        colon_match = colon_re.match(line)
        if colon_match:
            header = colon_match.group(1).strip()
            content = (colon_match.group(2) or '').strip()

            # Is this a new unit header?
            if _is_header_line(header):
                topics = _split_topics(content) if content else []
                current_unit = {
                    "title": header,
                    "unit_number": len(units) + 1,
                    "topics": topics,
                }
                units.append(current_unit)
                continue

        # Not a header — treat as continuation topics for current unit
        if current_unit is not None:
            if ',' in line or ';' in line:
                current_unit["topics"].extend(_split_topics(line))
            else:
                cleaned = line.rstrip('.').strip()
                cleaned = re.sub(r'^[-•●○▪]\s*', '', cleaned).strip()
                cleaned = re.sub(r'^\d+\.?\d*\s+', '', cleaned).strip()
                if cleaned and len(cleaned) > 1:
                    current_unit["topics"].append(cleaned)

    return units


def _parse_unit_headers(lines: list[str]) -> list[dict]:
    """Parse format with explicit Unit/Module/Chapter headers followed by topics."""
    unit_patterns = [
        re.compile(r'^(?:Unit|Module|Chapter|Section)\s*[-:]?\s*(\d+)\s*[-:.]?\s*(.*)', re.IGNORECASE),
        re.compile(r'^(\d+)\s*[.:]\s+([A-Z].*)', re.MULTILINE),
        re.compile(r'^(UNIT|MODULE|CHAPTER)\s+(\w+)\s*[-:.]?\s*(.*)', re.IGNORECASE),
    ]

    topic_patterns = [
        re.compile(r'^\d+\.\d+\s+(.+)'),
        re.compile(r'^[-•●○▪]\s+(.+)'),
        re.compile(r'^[a-z]\)\s+(.+)'),
        re.compile(r'^\(\w\)\s+(.+)'),
    ]

    units = []
    current_unit = None

    for line in lines:
        is_unit = False
        for pattern in unit_patterns:
            match = pattern.match(line)
            if match:
                groups = match.groups()
                try:
                    unit_num = int(groups[0]) if groups[0].isdigit() else len(units) + 1
                except ValueError:
                    unit_num = len(units) + 1
                title = groups[-1].strip() if len(groups) >= 2 and groups[-1].strip() else f"Unit {unit_num}"

                if ',' in title:
                    parts = _split_topics(title)
                    current_unit = {
                        "title": f"Unit {unit_num}",
                        "unit_number": unit_num,
                        "topics": parts,
                    }
                else:
                    current_unit = {
                        "title": title,
                        "unit_number": unit_num,
                        "topics": [],
                    }
                units.append(current_unit)
                is_unit = True
                break

        if is_unit:
            continue

        if current_unit is not None:
            if ',' in line or ';' in line:
                current_unit["topics"].extend(_split_topics(line))
                continue

            for pattern in topic_patterns:
                match = pattern.match(line)
                if match:
                    t = match.group(1).strip()
                    if t and len(t) > 2:
                        current_unit["topics"].append(t)
                    break
            else:
                if len(line) > 3 and line[0].isupper() and len(line) < 200:
                    current_unit["topics"].append(line)

    return units


def _split_topics(text: str) -> list[str]:
    """Split a comma/semicolon-separated string into individual topic names."""
    parts = re.split(r'[,;]+', text)
    topics = []
    for p in parts:
        p = p.strip().rstrip('.')
        p = re.sub(r'^[\d.)\-•●]+\s*', '', p).strip()
        if p and len(p) > 1:
            topics.append(p)
    return topics


def _fallback_parse(lines: list[str]) -> list[dict]:
    """Fallback parser for unstructured syllabi — detects ALL CAPS headers."""
    units = []
    current_unit = None

    for line in lines:
        if len(line) < 3:
            continue

        if line.isupper() and len(line) > 5:
            current_unit = {
                "title": line.title(),
                "unit_number": len(units) + 1,
                "topics": [],
            }
            units.append(current_unit)
        elif current_unit is not None:
            if ',' in line or ';' in line:
                current_unit["topics"].extend(_split_topics(line))
            else:
                current_unit["topics"].append(line)
        else:
            topics = _split_topics(line) if (',' in line or ';' in line) else [line]
            current_unit = {
                "title": "General Topics",
                "unit_number": 1,
                "topics": topics,
            }
            units.append(current_unit)

    return units


def _clean_units(units: list[dict]) -> list[dict]:
    """Remove empty units, deduplicate topics, strip trailing dots."""
    cleaned = []
    for u in units:
        topics = []
        seen = set()
        for t in u["topics"]:
            t = t.strip().rstrip('.')
            t_lower = t.lower()
            if t and t_lower not in seen and len(t) > 1:
                seen.add(t_lower)
                topics.append(t)
        u["topics"] = topics
        if u["topics"]:
            cleaned.append(u)
    return cleaned
