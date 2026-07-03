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


def normalize_core(name: str) -> str:
    """ASCII-letters-only core of a name.

    Decorative symbols in ingame names (stars, dividers, IPA-style glyphs)
    get OCR'd inconsistently — sometimes as stray digits, sometimes as a
    different letter, sometimes dropped. Reducing both sides to just their
    plain a-z letters sidesteps that noise. Used as a fallback after the
    normal exact/fuzzy match on the full name fails.
    """
    return "".join(ch for ch in normalize(name) if "a" <= ch <= "z")


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

    # ASCII-core name -> member; dropped if ambiguous (two different members
    # share the same core, e.g. their symbols are the only thing distinguishing
    # them) since a fallback match must be unambiguous to be trustworthy.
    core_lookup: dict[str, dict] = {}
    core_ambiguous: set[str] = set()

    def _add_core(key: str, member: dict) -> None:
        if not key:
            return
        existing = core_lookup.get(key)
        if existing is not None and existing["player_id"] != member["player_id"]:
            core_ambiguous.add(key)
            return
        core_lookup[key] = member

    for m in members:
        _add_core(normalize_core(m["ingame_name"]), m)
    for row in history_rows:
        member = by_id.get(row["player_id"])
        if member is not None:
            _add_core(normalize_core(row["ingame_name"]), member)
    for key in core_ambiguous:
        core_lookup.pop(key, None)

    keys = list(lookup)
    core_keys = list(core_lookup)
    best_per_member: dict[str, dict] = {}  # player_id -> best match so far
    unmatched: list[str] = []

    for line in lines:
        norm = normalize(line["text"])
        core = normalize_core(line["text"])

        member = None
        method = None
        score = None

        hit = lookup.get(norm)
        if hit is not None:
            member, method = hit
            score = 100.0
        elif core and core in core_lookup:
            member = core_lookup[core]
            method = "exact_core"
            score = 95.0
        elif keys:
            found = process.extractOne(
                norm, keys, scorer=fuzz.WRatio, score_cutoff=FUZZY_MATCH_THRESHOLD
            )
            if found is not None:
                key, score, _ = found
                member, _base_method = lookup[key]
                method = "fuzzy"
                score = float(score)

        if member is None and core and core_keys:
            found = process.extractOne(
                core, core_keys, scorer=fuzz.WRatio, score_cutoff=FUZZY_MATCH_THRESHOLD
            )
            if found is not None:
                key, score, _ = found
                member = core_lookup[key]
                method = "fuzzy_core"
                score = float(score)

        if member is None:
            unmatched.append(line["text"].strip())
            continue

        match = {
            "player_id": member["player_id"],
            "alias": member["alias"],
            "ingame_name": member["ingame_name"],
            "matched_by_name": line["text"].strip(),  # raw OCR text
            "method": method,  # "exact" | "history" | "exact_core" | "fuzzy" | "fuzzy_core"
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
