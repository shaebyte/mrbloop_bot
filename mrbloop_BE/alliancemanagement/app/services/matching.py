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


def build_name_lookups(members: list[dict], history_rows: list[dict]) -> tuple[dict, dict]:
    """Build the (lookup, core_lookup) tables shared by name-matching passes.

    lookup: normalized name -> (member, method); current names win over history.
    core_lookup: ASCII-letters-only core name -> member; ambiguous cores (two
    different members sharing the same core, e.g. their symbols are the only
    thing distinguishing them) are dropped since a fallback match must be
    unambiguous to be trustworthy.
    """
    by_id = {m["player_id"]: m for m in members}

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

    return lookup, core_lookup


def best_name_match(
    text: str, lookup: dict, core_lookup: dict, keys: list[str], core_keys: list[str]
) -> tuple[dict, str, float] | None:
    """Resolve a single piece of OCR text to a member, or None if no match clears
    the fuzzy threshold. Same exact -> exact_core -> fuzzy -> fuzzy_core cascade
    used by match_lines(), factored out so power_matching can reuse it per-row.
    """
    norm = normalize(text)
    core = normalize_core(text)

    hit = lookup.get(norm)
    if hit is not None:
        member, method = hit
        return member, method, 100.0

    if core and core in core_lookup:
        return core_lookup[core], "exact_core", 95.0

    if keys:
        found = process.extractOne(
            norm, keys, scorer=fuzz.WRatio, score_cutoff=FUZZY_MATCH_THRESHOLD
        )
        if found is not None:
            key, score, _ = found
            member, _base_method = lookup[key]
            return member, "fuzzy", float(score)

    if core and core_keys:
        found = process.extractOne(
            core, core_keys, scorer=fuzz.WRatio, score_cutoff=FUZZY_MATCH_THRESHOLD
        )
        if found is not None:
            key, score, _ = found
            return core_lookup[key], "fuzzy_core", float(score)

    return None


def match_lines(members: list[dict], history_rows: list[dict], lines: list[dict]) -> dict:
    """members: rows from am_members (player_id, alias, ingame_name).
    history_rows: rows from am_member_name_history valid on the event date.
    lines: OCR lines that survived filter_candidates().

    Returns {"matched": [...], "unmatched_lines": [...], "members_not_found": [...]}.
    """
    by_id = {m["player_id"]: m for m in members}
    lookup, core_lookup = build_name_lookups(members, history_rows)

    keys = list(lookup)
    core_keys = list(core_lookup)
    best_per_member: dict[str, dict] = {}  # player_id -> best match so far
    unmatched: list[str] = []

    for line in lines:
        found = best_name_match(line["text"], lookup, core_lookup, keys, core_keys)
        if found is None:
            unmatched.append(line["text"].strip())
            continue
        member, method, score = found

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
