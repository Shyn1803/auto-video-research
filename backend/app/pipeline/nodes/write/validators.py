"""Pure-function validators for the write node -- Task 4-5 Steps 4-7.

Every validator here is a pure function: `(text | data) -> result`, no I/O,
no DB, no LLM call -- these run as deterministic post-checks on LLM output
(same "AI never decides structure/rules alone" posture as task 4-4's
verify.py gates), and are exactly what the DoD calls out as needing the
most scrutiny (the number-set subset check).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.step_version import ContentWarning

# ---------------------------------------------------------------------------
# Step 4: number-set normalization + subset check (BR: "tập số outline ⊆
# script"). Three input shapes must normalize to the same canonical form:
#   - "92,5"   (Vietnamese decimal comma)
#   - "92.5"   (English/JSON decimal point)
#   - "chín mươi hai phẩy năm" (spelled-out Vietnamese, read digit-by-digit
#     after "phẩy" -- Vietnamese speech reads decimals one digit at a time,
#     e.g. "92,57" -> "... phẩy năm bảy", not "... phẩy năm mươi bảy")
# ---------------------------------------------------------------------------

_DIGIT_WORDS: dict[str, int] = {
    "không": 0, "một": 1, "mốt": 1, "hai": 2, "ba": 3,
    "bốn": 4, "tư": 4, "năm": 5, "lăm": 5, "nhăm": 5,
    "sáu": 6, "bảy": 7, "bẩy": 7, "tám": 8, "chín": 9,
}
_TENS_UNIT = 10
_HUNDRED_UNIT = 100
_THOUSAND_UNIT = 1_000
_MILLION_UNIT = 1_000_000

_MAGNITUDE_WORDS: dict[str, int] = {
    "mươi": _TENS_UNIT,
    "chục": _TENS_UNIT,
    "trăm": _HUNDRED_UNIT,
    "nghìn": _THOUSAND_UNIT,
    "ngàn": _THOUSAND_UNIT,
    "triệu": _MILLION_UNIT,
}

# Negative lookbehind/lookahead on letters so a digit embedded in an
# alphanumeric token -- e.g. the "1" in a "[s1]" source citation -- is
# never mistaken for a real number in the text (real bug found in task
# 4-5 Step 9's own integration test: outline text always carries [source_id]
# citations per BR-1/AC1, and those digits must never enter the compared
# number sets).
_NUMBER_TOKEN_RE = re.compile(r"(?<![a-zA-Z])\d+(?:[.,]\d+)?(?![a-zA-Z])")


def _parse_integer_words(words: list[str]) -> int | None:
    """Parse a compound Vietnamese integer phrase (e.g. "chín mươi hai",
    "một trăm") into an int, or None if *words* isn't a number phrase.
    """
    if not words:
        return None

    # Special case: "mười" alone (or leading) means the tens digit is 1,
    # e.g. "mười hai" = 12, distinct from "X mươi" = X*10.
    total = 0
    current = 0
    i = 0
    matched_any = False

    while i < len(words):
        w = words[i]
        if w == "mười" and current == 0:
            current = 1 * _TENS_UNIT
            matched_any = True
            i += 1
            continue
        if w in _DIGIT_WORDS:
            digit = _DIGIT_WORDS[w]
            # lookahead: digit followed by a magnitude word multiplies it
            if i + 1 < len(words) and words[i + 1] in _MAGNITUDE_WORDS:
                mag = _MAGNITUDE_WORDS[words[i + 1]]
                current += digit * mag
                i += 2
                matched_any = True
                continue
            current += digit
            matched_any = True
            i += 1
            continue
        if w in _MAGNITUDE_WORDS:
            # bare magnitude word (e.g. "trăm" without a leading digit) is
            # not a valid standalone phrase here -- bail out.
            return None if not matched_any else total + current
        # unrecognized word ends the number phrase
        break

    if not matched_any:
        return None
    return total + current


def _extract_word_numbers(text: str) -> set[str]:
    """Find spelled-out Vietnamese numbers (incl. decimals via "phẩy") and
    return them as canonical decimal strings, e.g. {"92.5"}.
    """
    lowered = text.lower()
    # \w is Unicode-aware in Python 3 (no re.ASCII flag) -- covers every
    # Vietnamese diacritic in one shot. An earlier hand-rolled character
    # class here silently dropped letters like "ẩ"/"ộ", truncating tokens
    # ("phẩy" -> "ph"+"y", "một" -> nothing) and breaking decimal detection.
    tokens = re.findall(r"\w+", lowered)

    found: set[str] = set()
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i] == "phẩy":
            i += 1
            continue
        # try to consume the longest run of digit/magnitude words starting here
        j = i
        while j < n and (
            tokens[j] in _DIGIT_WORDS
            or tokens[j] in _MAGNITUDE_WORDS
            or tokens[j] == "mười"
        ):
            j += 1
        if j > i:
            integer_part = _parse_integer_words(tokens[i:j])
            if integer_part is not None:
                # look for a following "phẩy <digit-words...>" decimal part
                decimal_digits = ""
                k = j
                if k < n and tokens[k] == "phẩy":
                    k += 1
                    while k < n and tokens[k] in _DIGIT_WORDS:
                        decimal_digits += str(_DIGIT_WORDS[tokens[k]])
                        k += 1
                if decimal_digits:
                    found.add(_canonical(f"{integer_part}.{decimal_digits}"))
                    i = k
                    continue
                # A bare single-word digit ("năm", "một", "hai"...) is too
                # ambiguous to treat as a number on its own -- these are
                # common homographs (năm = "year"/"5", một = "a/an"/"1").
                # Only count it when it's part of a multi-word compound
                # (e.g. "chín mươi hai") or a decimal continuation (above).
                if (j - i) >= 2:
                    found.add(_canonical(str(integer_part)))
            i = j
        else:
            i += 1
    return found


def _canonical(number_str: str) -> str:
    """Normalize "92,5" / "92.5" / "92.50" -> "92.5" (strip trailing zeros,
    unify the decimal separator)."""
    s = number_str.replace(",", ".")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
        if s == "" or s == "-":
            s = "0"
    return s


def normalize_numbers(text: str) -> set[str]:
    """Extract every number mentioned in *text* (digit form or spelled-out
    Vietnamese words) as a canonical set of decimal strings.
    """
    digit_numbers = {_canonical(m) for m in _NUMBER_TOKEN_RE.findall(text)}
    word_numbers = _extract_word_numbers(text)
    return digit_numbers | word_numbers


@dataclass(frozen=True)
class NumberSetCheckResult:
    ok: bool
    missing: frozenset[str]


def check_number_subset(outline_text: str, script_text: str) -> NumberSetCheckResult:
    """BR: every number in the outline must reappear in the script (after
    normalization) -- pure function, no retry/side effects here (the
    calling node owns the "retry once, then warn" policy)."""
    outline_numbers = normalize_numbers(outline_text)
    script_numbers = normalize_numbers(script_text)
    missing = outline_numbers - script_numbers
    return NumberSetCheckResult(ok=not missing, missing=frozenset(missing))


# ---------------------------------------------------------------------------
# Step 5: voice_over readability validator (BR-2) -- warns if raw symbols
# slip through instead of the prompt's required spelled-out numerals.
# ---------------------------------------------------------------------------

_LEAKED_SYMBOLS = ("%", "$")


def check_voice_over_symbol_leak(voice_over: str) -> ContentWarning | None:
    leaked = [ch for ch in _LEAKED_SYMBOLS if ch in voice_over]
    if not leaked:
        return None
    return ContentWarning(
        type="voice_over_symbol_leak",
        detail=f"voice_over contains raw symbol(s) {leaked} instead of spoken-word numerals",
    )


# ---------------------------------------------------------------------------
# Step 6: title length guard (BR-3) -- truncate at a word boundary, never
# mid-word, and always flag a warning (never a silent cut).
# ---------------------------------------------------------------------------

TITLE_MAX_LEN = 70


@dataclass(frozen=True)
class TitleGuardResult:
    title: str
    warning: ContentWarning | None


def enforce_title_length(title: str) -> TitleGuardResult:
    if len(title) <= TITLE_MAX_LEN:
        return TitleGuardResult(title=title, warning=None)

    truncated = title[:TITLE_MAX_LEN]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    truncated = truncated.rstrip()

    warning = ContentWarning(
        type="title_truncated",
        detail=f"original title was {len(title)} chars, truncated to {len(truncated)}",
    )
    return TitleGuardResult(title=truncated, warning=warning)


# ---------------------------------------------------------------------------
# Step 7: WARN-claim disclosure enforcement (BR-4) -- any script sentence
# built from a WARN claim must actually contain the disclosure phrase, not
# just be instructed to by the prompt.
# ---------------------------------------------------------------------------

DISCLOSURE_PHRASE = "theo nguồn chưa xác nhận"


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


# High-frequency function/connector words that coincidentally recur across
# unrelated Vietnamese sentences (negation, linking, generic nouns) -- a
# single shared word like this is not evidence a sentence is "about" a
# claim; see check_warn_claim_disclosure's overlap-count-2 rule below,
# which this list backs by keeping obviously-generic words out of the
# keyword set in the first place.
_DISCLOSURE_STOPWORDS = {
    "không", "hoàn", "toàn", "liên", "quan", "dung", "điều", "được",
    "trong", "những", "cũng", "rằng", "hơn", "này", "cho", "với",
}


def _keywords(text: str, *, min_len: int = 4) -> set[str]:
    words = "".join(ch if ch.isalnum() else " " for ch in text.lower()).split()
    return {w for w in words if len(w) >= min_len and w not in _DISCLOSURE_STOPWORDS}


def check_warn_claim_disclosure(
    voice_over: str, warn_claims: list[dict[str, str]]
) -> list[ContentWarning]:
    """For each WARN claim whose keywords show up in a script sentence,
    that sentence must contain DISCLOSURE_PHRASE -- returns one warning
    per claim that was used without the disclosure actually present.

    "Shows up" requires at least 2 overlapping distinctive keywords (or
    all of them, if the claim has fewer than 2 to begin with) -- a single
    shared word is too weak a signal on its own (see _DISCLOSURE_STOPWORDS
    above for the common-word cases this is guarding against).
    """
    warnings: list[ContentWarning] = []
    sentences = _split_sentences(voice_over)

    for claim in warn_claims:
        claim_text = claim.get("claim_text", "")
        claim_keywords = _keywords(claim_text)
        if not claim_keywords:
            continue
        overlap_threshold = min(2, len(claim_keywords))

        used_sentences = [
            s for s in sentences
            if len(_keywords(s) & claim_keywords) >= overlap_threshold
        ]
        if not used_sentences:
            continue  # claim not used in the script at all -- nothing to flag

        if not any(DISCLOSURE_PHRASE in s.lower() for s in used_sentences):
            warnings.append(
                ContentWarning(
                    type="warn_claim_disclosure_missing",
                    detail=(
                        f"WARN claim used without disclosure phrase: "
                        f"{claim_text!r}"
                    ),
                )
            )

    return warnings
