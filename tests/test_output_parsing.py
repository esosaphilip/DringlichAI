"""Unit tests for `parse_triage_response()` — the parser between the LLM and the triage decision.

WHY THIS EXISTS: the raw model string is untrusted, and this parser is the only thing standing
between a chatty/garbled response and a silently wrong triage level. These tests pin down the
exact fallback chain (labelled line -> bare `P<n>` -> any digit -> default 3) so a future edit
cannot quietly change how a bad response is interpreted.

WHAT A FAILURE WOULD MEAN: if the garbled-response test starts failing with a priority other
than 3, the documented safety default changed and every downstream triage decision inherits that
change — a real behavioural regression, not just a refactor that broke a test.

No LLM and no Ollama are needed: `parse_triage_response` is a pure function.
"""

from priority_analyzer_agent import parse_triage_response


def test_perfectly_formatted_response():
    """The happy path: four labelled lines parse into the four structured fields."""
    raw = (
        "PRIORITY: P2\n"
        "CONFIDENCE: 87\n"
        "GUIDELINE: CP-03\n"
        "REASON: crushing central chest pain radiating to the left arm"
    )
    out = parse_triage_response(raw)

    assert out["priority"] == 2
    assert out["confidence"] == 87
    assert out["guideline"] == "CP-03"
    assert out["reasoning"] == "crushing central chest pain radiating to the left arm"


def test_missing_confidence_line_defaults_to_80():
    """A response that omits the CONFIDENCE line must still yield a usable confidence (80)."""
    raw = (
        "PRIORITY: P3\n"
        "GUIDELINE: SB-03\n"
        "REASON: known asthma, still speaking in full sentences"
    )
    out = parse_triage_response(raw)

    assert out["priority"] == 3
    assert out["confidence"] == 80
    assert out["guideline"] == "SB-03"


def test_chatty_response_with_surrounding_text():
    """A model that talks around the required lines must still be parsed correctly."""
    raw = (
        "Sure, let me work through this case.\n"
        "PRIORITY: P1\n"
        "CONFIDENCE: 99\n"
        "GUIDELINE: HA-01\n"
        "REASON: reduced consciousness with a reported seizure.\n"
        "Let me know if you need anything else!"
    )
    out = parse_triage_response(raw)

    assert out["priority"] == 1
    assert out["confidence"] == 99
    assert out["guideline"] == "HA-01"
    assert out["reasoning"].startswith("reduced consciousness with a reported seizure")


def test_fully_garbled_response_falls_back_to_priority_3():
    """A response with no parseable fields must land on priority 3 — the current documented default.

    This does NOT assert that 3 is the clinically right default; it asserts that the behaviour we
    have today is the behaviour the tests (and README) describe. Changing it is a deliberate
    decision, not something a refactor should be able to do unnoticed.
    """
    garbled = "I am sorry, I am not able to help with that request."
    out = parse_triage_response(garbled)

    assert out["priority"] == 3
    # With no GUIDELINE line the caller's fallback label is used, and reasoning stays empty.
    assert out["guideline"] == "Triage guide"
    assert out["reasoning"] == ""

    # Empty input must behave the same way rather than raising.
    assert parse_triage_response("")["priority"] == 3
