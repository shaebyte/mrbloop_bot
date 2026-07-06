"""Match power-leaderboard screenshots: pair each row's name with its power number.

A leaderboard row (rank, name, power, ...) is usually OCR'd as several separate
text boxes on the same visual line, not one line like attendance's name-only
lists. This groups OCR boxes into rows by y-position, pulls the largest number
in each row that looks like a power value, and matches the row's remaining
text against members using the same cascade as matching.match_lines().
"""
import re

from app.config import OCR_MIN_CONFIDENCE, OCR_MIN_POWER_VALUE, OCR_ROW_Y_TOLERANCE_RATIO
from app.services.matching import best_name_match, build_name_lookups

_NUMBER = re.compile(r"\d[\d.,]*\d|\d")
_ONLY_DIGITS_PUNCT = re.compile(r"^[\d\s.,:%#+\-/()]+$")


def _box_y_center(box) -> float:
    ys = [p[1] for p in box]
    return sum(ys) / len(ys)


def _box_x_center(box) -> float:
    xs = [p[0] for p in box]
    return sum(xs) / len(xs)


def _box_height(box) -> float:
    ys = [p[1] for p in box]
    return max(ys) - min(ys)


def group_rows(lines: list[dict]) -> list[list[dict]]:
    """Cluster OCR lines into visual rows by y-position proximity, left-to-right."""
    usable = [l for l in lines if l["confidence"] >= OCR_MIN_CONFIDENCE and l["box"]]
    if not usable:
        return []

    heights = [_box_height(l["box"]) for l in usable]
    avg_height = (sum(heights) / len(heights)) if heights else 20.0
    tolerance = max(avg_height * OCR_ROW_Y_TOLERANCE_RATIO, 4.0)

    ordered = sorted(usable, key=lambda l: _box_y_center(l["box"]))
    rows: list[list[dict]] = []
    row_y: list[float] = []
    for line in ordered:
        y = _box_y_center(line["box"])
        if rows and abs(y - row_y[-1]) <= tolerance:
            rows[-1].append(line)
            row_y[-1] = sum(_box_y_center(l["box"]) for l in rows[-1]) / len(rows[-1])
        else:
            rows.append([line])
            row_y.append(y)

    for row in rows:
        row.sort(key=lambda l: _box_x_center(l["box"]))
    return rows


def _extract_power(row: list[dict]) -> int | None:
    """Largest number across the row's texts that clears OCR_MIN_POWER_VALUE.

    Power is assumed to dwarf other numeric columns (rank, furnace level, ...),
    so the max value in the row is the safest bet without knowing column layout.
    """
    best = None
    for cell in row:
        for raw in _NUMBER.findall(cell["text"]):
            digits = re.sub(r"[.,]", "", raw)
            if not digits:
                continue
            value = int(digits)
            if value >= OCR_MIN_POWER_VALUE and (best is None or value > best):
                best = value
    return best


def _row_name_text(row: list[dict]) -> str:
    """Row text with pure number/punctuation cells dropped, so the power/rank
    column never gets fed into the name matcher."""
    return " ".join(
        cell["text"] for cell in row if not _ONLY_DIGITS_PUNCT.match(cell["text"].strip())
    ).strip()


def match_power_rows(
    members: list[dict], history_rows: list[dict], screenshots: list[list[dict]]
) -> dict:
    """members: rows from am_members. history_rows: am_member_name_history rows
    valid on the target date. screenshots: one list of raw OCR lines (with boxes)
    per uploaded leaderboard screenshot — rows must be grouped per-screenshot,
    since each screenshot's rows restart near the same y-positions and would
    otherwise get merged together by cross-screenshot y-clustering.

    Returns {"matched": [...], "unmatched_rows": [...], "members_not_found": [...]}.
    Each matched entry: player_id, alias, ingame_name, matched_by_name, power,
    method, score, ocr_confidence.
    """
    by_id = {m["player_id"]: m for m in members}
    lookup, core_lookup = build_name_lookups(members, history_rows)
    keys = list(lookup)
    core_keys = list(core_lookup)

    best_per_member: dict[str, dict] = {}
    unmatched_rows: list[str] = []

    rows = [row for lines in screenshots for row in group_rows(lines)]
    for row in rows:
        power = _extract_power(row)
        name_text = _row_name_text(row)
        if power is None or not name_text:
            continue

        found = best_name_match(name_text, lookup, core_lookup, keys, core_keys)
        if found is None:
            unmatched_rows.append(name_text)
            continue
        member, method, score = found

        match = {
            "player_id": member["player_id"],
            "alias": member["alias"],
            "ingame_name": member["ingame_name"],
            "matched_by_name": name_text,
            "power": power,
            "method": method,
            "score": score,
            "ocr_confidence": min(cell["confidence"] for cell in row),
        }
        current = best_per_member.get(member["player_id"])
        if current is None or match["score"] > current["score"]:
            best_per_member[member["player_id"]] = match

    matched = sorted(best_per_member.values(), key=lambda m: (-m["score"], m["alias"]))
    not_found = [m for pid, m in by_id.items() if pid not in best_per_member]
    not_found.sort(key=lambda m: m["alias"])

    return {
        "matched": matched,
        "unmatched_rows": sorted(set(unmatched_rows)),
        "members_not_found": not_found,
    }
