"""Match OCR text lines against members' current + historical in-game names.

Pure functions — the routes fetch members/history from the repository and
pass them in as plain dicts.

Pipeline:
1. filter_candidates(): drop UI noise (numbers, known words, too short/long,
   low OCR confidence).
2. build a lookup of normalized name -> member, from current names AND
   history rows that were valid on the event date (catches recent renames).
3. exact match first, then fuzzy (rapidfuzz) above a configurable threshold.
"""
import re
import unicodedata

from rapidfuzz import fuzz, process

from app.config import (
    FUZZY_MATCH_THRESHOLD,
    OCR_IGNORE_WORDS,
    OCR_MAX_NAME_LENGTH,
    OCR_MIN_CONFIDENCE,
    OCR_MIN_NAME_LENGTH,
    STRIP_ALLIANCE_TAG,
)

_WHITESPACE = re.compile(r"\s+")
# Leading alliance tag like "[ABC] Name", "(XYZ)Name", "<TAG> Name"
_ALLIANCE_TAG = re.compile(r"^[\[\(\{<][^\]\)\}>]{1,6}[\]\)\}>]\s*")
_ONLY_DIGITS_PUNCT = re.compile(r"^[\d\s.,:%#+\-/()]+$")


def normalize(name: str) -> str:
    n = unicodedata.normalize("NFKC", name).strip()
    if STRIP_ALLIANCE_TAG:
        n = _ALLIANCE_TAG.sub("", n)
    n = _WHITESPACE.sub(" ", n)
    return n.casefold()


def filter_candidates(lines: list[dict]) -> list[dict]:
    """Keep only OCR lines that could plausibly be a player name."""
    out = []
    for line in lines:
        if line["confidence"] < OCR_MIN_CONFIDENCE:
            continue
        norm = normalize(line["text"])
        if not (OCR_MIN_NAME_LENGTH <= len(norm) <= OCR_MAX_NAME_LENGTH):
            continue
        if _ONLY_DIGITS_PUNCT.match(norm):
            continue
        if norm in OCR_IGNORE_WORDS:
            continue
        out.append(line)
    return out


def match_lines(members: list[dict], history_rows: list[dict], lines: list[dict]) -> dict:
    """members: rows from am_members (player_id, alias, ingame_name).
    history_rows: rows from am_member_name_history valid on the event date.
    lines: OCR lines that survived filter_candidates().

    Returns {"matched": [...], "unmatched_lines": [...], "members_not_found": [...]}.
    """
    by_id = {m["player_id"]: m for m in members}

    # normalized name -> (member, method); current names win over history names
    lookup: dict[str, tuple[dict, str]] = {}
    for m in members:
        lookup[normalize(m["ingame_name"])] = (m, "exact")
    for row in history_rows:
        member = by_id.get(row["player_id"])
        if member is None:
            continue
        key = normalize(row["ingame_name"])
        if key not in lookup:
            lookup[key] = (member, "history")

    keys = list(lookup)
    best_per_member: dict[str, dict] = {}  # player_id -> best match so far
    unmatched: list[str] = []

    for line in lines:
        norm = normalize(line["text"])

        hit = lookup.get(norm)
        if hit is not None:
            member, method = hit
            score = 100.0
        elif keys:
            found = process.extractOne(
                norm, keys, scorer=fuzz.WRatio, score_cutoff=FUZZY_MATCH_THRESHOLD
            )
            if found is None:
                unmatched.append(line["text"].strip())
                continue
            key, score, _ = found
            member, _base_method = lookup[key]
            method = "fuzzy"
            score = float(score)
        else:
            unmatched.append(line["text"].strip())
            continue

        match = {
            "player_id": member["player_id"],
            "alias": member["alias"],
            "ingame_name": member["ingame_name"],
            "matched_by_name": line["text"].strip(),  # raw OCR text
            "method": method,  # "exact" | "history" | "fuzzy"
            "score": score,
            "ocr_confidence": line["confidence"],
        }
        current = best_per_member.get(member["player_id"])
        if current is None or match["score"] > current["score"]:
            best_per_member[member["player_id"]] = match

    matched = sorted(best_per_member.values(), key=lambda m: (-m["score"], m["alias"]))
    not_found = [m for pid, m in by_id.items() if pid not in best_per_member]
    not_found.sort(key=lambda m: m["alias"])

    return {
        "matched": matched,
        "unmatched_lines": sorted(set(unmatched)),
        "members_not_found": not_found,
    }
