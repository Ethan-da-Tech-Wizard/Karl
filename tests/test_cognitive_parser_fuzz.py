"""
Fuzz Testing Suite — Karl Cognitive Parser Token Streams.

Generates 5,000 pseudo-random inputs covering:
  - nested tags
  - case variations
  - incomplete / partial tags
  - null bytes and binary payloads
  - emoji and surrogate unicode sequences
  - huge repeat blocks (up to 50,000 repetitions of <think>)
  - alternating open/close sequences

Every case asserts:
  - No exception is raised.
  - Return value is a (str, str) tuple.
  - Execution completes within a per-size-scaled time budget that catches
    any O(n²) or infinite-loop regression while allowing O(n) behaviour.
"""

from __future__ import annotations

import random
import string
import time
from typing import Callable

import pytest

from core.cognitive_parser import parse_thought_stream

# ── Configuration ─────────────────────────────────────────────────────────────

_SEED          = 42
_N_FUZZ_CASES  = 5_000

# Base ceiling: 2 ms for inputs up to _BASE_CHARS characters.
# Scaled linearly above that so large-but-O(n) inputs are allowed while a
# genuine quadratic regression (which would take seconds) is still caught.
_BASE_MS    = 2.0
_BASE_CHARS = 10_000

# ── Tag vocabulary ────────────────────────────────────────────────────────────

_OPEN_VARIANTS  = ["<think>", "<THINK>", "<Think>", "<ThInK>", "<tHiNk>"]
_CLOSE_VARIANTS = ["</think>", "</THINK>", "</Think>", "</ThInK>", "</tHiNk>"]
_EMOJI          = "😀🎉💻🔥🧠🤖⚡🌊🎯🔑"


# ── Input generators ──────────────────────────────────────────────────────────

def _rnd(rng: random.Random, max_len: int = 80) -> str:
    return "".join(rng.choices(string.printable, k=rng.randint(0, max_len)))


def _gen_nested(rng: random.Random) -> str:
    """Nested open tags followed by nested close tags at arbitrary depths."""
    depth = rng.randint(1, 6)
    opens  = "".join(rng.choice(_OPEN_VARIANTS) + _rnd(rng, 20) for _ in range(depth))
    closes = "".join(rng.choice(_CLOSE_VARIANTS) for _ in range(depth))
    return opens + closes


def _gen_case_variation(rng: random.Random) -> str:
    """Random capitalisation of open/close tags with surrounding text."""
    return (
        _rnd(rng, 40)
        + rng.choice(_OPEN_VARIANTS)
        + _rnd(rng, 80)
        + rng.choice(_CLOSE_VARIANTS)
        + _rnd(rng, 40)
    )


def _gen_incomplete(rng: random.Random) -> str:
    """Partial tag names that do not form a valid open or close tag."""
    partials = [
        "<thi", "<thin", "<think",
        "</thi", "</thin", "</think",
        "<THINK", "</THINK", "<tHi",
        "<think >",             # space inside tag — not recognised
        "< think>",
    ]
    n = rng.randint(1, 4)
    parts = [_rnd(rng, 30) + rng.choice(partials) for _ in range(n)]
    return "".join(parts) + _rnd(rng, 20)


def _gen_binary(rng: random.Random) -> str:
    """Null bytes, control characters, and printable text interleaved."""
    parts: list[str] = [
        _rnd(rng, 30),
        "".join(chr(rng.randint(0, 127)) for _ in range(rng.randint(5, 30))),
        "\x00" * rng.randint(1, 8),
        "\r\n\t" * rng.randint(1, 4),
        _rnd(rng, 30),
    ]
    rng.shuffle(parts)
    return "".join(parts)


def _gen_emoji(rng: random.Random) -> str:
    """Emoji sequences mixed with think tags."""
    emojis = "".join(rng.choices(_EMOJI, k=rng.randint(3, 30)))
    return (
        emojis
        + rng.choice(_OPEN_VARIANTS)
        + "thought \U0001f9e0"
        + _rnd(rng, 20)
        + rng.choice(_CLOSE_VARIANTS)
        + "response\U0001f680"
        + _rnd(rng, 20)
    )


def _gen_surrogate(rng: random.Random) -> str:
    """Lone surrogates — valid Python str values, not valid UTF-8."""
    surrogates = "".join(
        chr(rng.randint(0xD800, 0xDFFF)) for _ in range(rng.randint(1, 6))
    )
    return "prefix" + surrogates + "<think>content</think>suffix"


def _gen_huge_open_only(rng: random.Random) -> str:
    """Up to 50,000 repetitions of <think> with no closing tag.

    The parser finds the first opener in two iterations regardless of
    repetition count, then appends the rest as thought content and breaks.
    This ensures the test stays within the time budget despite string length.
    """
    count = rng.randint(10_000, 50_000)
    return "<think>" * count


def _gen_huge_close_only(rng: random.Random) -> str:
    """Many </think> tags with no opener — pre-seeded thought mode."""
    count = rng.randint(5_000, 20_000)
    return "</think>" * count


def _gen_huge_response(rng: random.Random) -> str:
    """A large tag-free string — parser appends it all then breaks."""
    count = rng.randint(30_000, 100_000)
    return rng.choice(string.ascii_letters) * count


def _gen_moderate_alternating(rng: random.Random) -> str:
    """Alternating open/close pairs.

    Capped at 500 pairs (≈ 15 k chars, 1,000 loop iterations) to stay
    comfortably within the 2 ms base budget.
    """
    pairs = rng.randint(50, 500)
    chunk = _rnd(rng, 10)
    return ("<think>" + chunk + "</think>" + "r") * pairs


def _gen_mixed(rng: random.Random) -> str:
    """Combination of tags, binary, emoji, and incomplete tags."""
    pieces = [
        _rnd(rng, 20),
        rng.choice(_OPEN_VARIANTS),
        _rnd(rng, 20),
        rng.choice(_CLOSE_VARIANTS),
        "\x00",
        rng.choice(_EMOJI),
        rng.choice(["<thi", "</THINK", "<think", ""]),
        _rnd(rng, 20),
    ]
    rng.shuffle(pieces)
    return "".join(pieces)


def _gen_trivial(rng: random.Random) -> str:
    """Edge-case degenerate inputs."""
    return rng.choice([
        "",
        " ",
        "\n",
        "\t",
        "hello world",
        "overposting",
        "no tags here",
        "   \n\n   ",
        "\x00",
        "overposting. yes. overposting",
    ])


# Weighted strategy table — weights are relative (not required to sum to 100).
_STRATEGIES: list[tuple[Callable[[random.Random], str], int]] = [
    (_gen_nested,              8),
    (_gen_case_variation,     10),
    (_gen_incomplete,         10),
    (_gen_binary,              8),
    (_gen_emoji,               8),
    (_gen_surrogate,           6),
    (_gen_huge_open_only,      4),   # large strings, O(1) loop iterations
    (_gen_huge_close_only,     3),   # large strings, O(1) loop iterations
    (_gen_huge_response,       4),   # large strings, no tags at all
    (_gen_moderate_alternating, 8),
    (_gen_mixed,              12),
    (_gen_trivial,            10),
]


def _build_inputs(n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    fns, weights = zip(*_STRATEGIES)
    chosen = rng.choices(list(fns), weights=list(weights), k=n)
    return [fn(rng) for fn in chosen]


# Build the corpus once at module-import time (deterministic, < 200 ms).
_FUZZ_INPUTS: list[str] = _build_inputs(_N_FUZZ_CASES, _SEED)


def _budget_ms(text: str) -> float:
    """Per-input time ceiling in milliseconds.

    Returns 2 ms for inputs up to _BASE_CHARS characters, then scales
    linearly so that O(n) parsers are never penalised for large inputs while
    O(n²) regressions (which take seconds) are always caught.
    """
    return _BASE_MS * max(1.0, len(text) / _BASE_CHARS)


# ── Main fuzz test ────────────────────────────────────────────────────────────

def test_fuzz_cognitive_parser_5000_cases():
    """5,000 pseudo-random inputs must each complete without crashing or hanging."""
    failures: list[str] = []

    for idx, text in enumerate(_FUZZ_INPUTS):
        budget = _budget_ms(text)

        # ── no-exception guard ────────────────────────────────────────────────
        try:
            t0 = time.perf_counter()
            result = parse_thought_stream(text)
            elapsed_ms = (time.perf_counter() - t0) * 1_000.0
        except Exception as exc:
            failures.append(
                f"[case {idx}] {type(exc).__name__}: {exc} "
                f"(input preview: {text[:60]!r})"
            )
            continue

        # ── return-type guard ─────────────────────────────────────────────────
        if not isinstance(result, tuple) or len(result) != 2:
            failures.append(
                f"[case {idx}] Expected (str, str) tuple, got {type(result)}: {result!r}"
            )
            continue

        thought, response = result
        if not isinstance(thought, str):
            failures.append(
                f"[case {idx}] thought is {type(thought)!r}, expected str"
            )
        if not isinstance(response, str):
            failures.append(
                f"[case {idx}] response is {type(response)!r}, expected str"
            )

        # ── timing guard (catches infinite loops / quadratic regressions) ─────
        if elapsed_ms > budget:
            failures.append(
                f"[case {idx}] {elapsed_ms:.2f} ms > {budget:.2f} ms budget "
                f"(input len={len(text)}, preview={text[:40]!r})"
            )

    if failures:
        sample = "\n".join(failures[:20])
        pytest.fail(
            f"{len(failures)}/{_N_FUZZ_CASES} fuzz cases failed "
            f"(showing up to 20):\n{sample}"
        )


# ── Fixed regression cases ────────────────────────────────────────────────────
# These named inputs are tested regardless of RNG distribution so that critical
# categories are always exercised.

_FIXED: list[tuple[str, str]] = [
    ("empty string",                 ""),
    ("whitespace only",              "   \n\t  "),
    ("open tag only",                "<think>"),
    ("close tag only",               "</think>"),
    ("empty thought block",          "<think></think>"),
    ("uppercase open close",         "<THINK>text</THINK>"),
    ("mixed case tags",              "<ThInK>thought</tHiNk>response"),
    ("pre-seeded close before open", "partial</think>rest"),
    ("null bytes around tags",       "\x00<think>\x00thought\x00</think>\x00"),
    ("lone surrogate",               "𐏿<think>x</think>y"),
    ("overposting in thought",       "<think>  overposting  </think>"),
    ("overposting in response",      "text overposting. more text"),
    ("overposting both sides",       "<think>overposting</think>also overposting"),
    ("deeply nested open-close",     "<think>" * 10 + "content" + "</think>" * 10),
    ("incomplete open at end",       "hello<thi"),
    ("incomplete close at end",      "hello</thin"),
    ("space inside tag brackets",    "< think>content</think>"),
    ("50k open tags no close",       "<think>" * 50_000),
    ("10k close tags no open",       "</think>" * 10_000),
    ("emoji stream with tags",       "😀" * 500 + "<think>🧠</think>🚀"),
    ("interleaved null and tags",    "\x00<think>\x00</think>\x00"),
    ("response before thought",      "response<think>thought</think>"),
    ("multiple think blocks",        "<think>a</think>b<think>c</think>d"),
    ("no-close mid-stream",          "text<think>unclosed thought here"),
    ("adjacent open close",          "<think></think>" * 500),
]


@pytest.mark.parametrize("label,text", _FIXED, ids=[label for label, _ in _FIXED])
def test_fixed_regression(label: str, text: str):
    """Named edge-case inputs — each must complete without exception in budget."""
    budget = _budget_ms(text)

    try:
        t0 = time.perf_counter()
        result = parse_thought_stream(text)
        elapsed_ms = (time.perf_counter() - t0) * 1_000.0
    except Exception as exc:
        pytest.fail(
            f"[{label!r}] parse_thought_stream raised "
            f"{type(exc).__name__}: {exc}"
        )

    assert isinstance(result, tuple) and len(result) == 2, (
        f"[{label!r}] Expected (str, str) 2-tuple, got {result!r}"
    )
    thought, response = result
    assert isinstance(thought, str), (
        f"[{label!r}] thought must be str, got {type(thought)!r}"
    )
    assert isinstance(response, str), (
        f"[{label!r}] response must be str, got {type(response)!r}"
    )
    assert elapsed_ms <= budget, (
        f"[{label!r}] Timed out: {elapsed_ms:.2f} ms > {budget:.2f} ms "
        f"(input len={len(text)})"
    )
