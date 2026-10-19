import copy
import json

import pytest

from eval.compare import compare, spearman
from pipeline import validate as v
from pipeline.context import build_context, context_block, decision_label

DECISIONS = [
    {"bank": "BoE", "date": "2026-07-30", "announced": "2026-07-30T11:00:00Z",
     "previous_rate": 3.75, "decision_rate": 3.75,
     "votes": {"bailey": 3.75, "pill": 4.0, "mann": 4.0, "taylor": 3.75}},
    {"bank": "BoE", "date": "2026-09-17", "announced": "2026-09-17T11:00:00Z",
     "previous_rate": 3.75, "decision_rate": 3.75,
     "votes": {"bailey": 3.75, "pill": 4.0, "mann": 3.75, "taylor": 3.75}},
]


# ---- context

def test_decision_label():
    assert decision_label(DECISIONS[0]) == "hold, 2-2 (2 for a hike)"
    unanimous = dict(DECISIONS[0], votes={"a": 4.0, "b": 4.0}, decision_rate=4.0)
    assert decision_label(unanimous) == "hike to 4%, unanimous"


def test_minutes_statement_gets_its_own_meeting():
    ctx = build_context("BoE", "mann", "2026-09-17T11:00:00Z", DECISIONS)
    assert ctx["last_decision_date"] == "2026-09-17"
    assert ctx["speaker_last_vote"] == "hold"


def test_speech_before_meeting_gets_previous_meeting():
    ctx = build_context("BoE", "mann", "2026-09-16T09:00:00Z", DECISIONS)
    assert ctx["last_decision_date"] == "2026-07-30"
    assert ctx["speaker_last_vote"] == "hike to 4%"


def test_missing_baseline_is_said_plainly(tmp_path):
    ctx = build_context("BoE", "mann", "2026-09-16T09:00:00Z", DECISIONS, baseline_dir=tmp_path)
    assert ctx["baseline_file"] is None
    assert "not available" in context_block(ctx)


# ---- validate

GOOD = {
    "id": "doc-1-p01", "document_id": "doc-1", "member_id": "pill", "bank": "BoE",
    "timestamp": "2026-09-03T14:00:00Z", "source_type": "speech",
    "document_url": "https://example", "passage": "We cannot wait for uncertainties to resolve.",
    "language": "en", "context": {}, "score": 3, "confidence": 0.8, "flag": None,
    "rate_path_signal": "implied", "dimensions": {"inflation": 2}, "topics": ["rate_path"],
    "key_quote": "cannot wait", "rationale": "Argues for acting now.", "institutional": False,
    "novelty": "new", "rubric_version": "v1", "passage_weight_share": 1.0,
}


@pytest.fixture
def checker(monkeypatch):
    c = v.Checker()
    c.version = "v1"
    monkeypatch.setattr(c, "doc_text", lambda doc_id, bank: v._squash(
        "Intro. In my view, we cannot wait for uncertainties to resolve. Thanks."))
    return c


def errors(checker, **changes):
    r = copy.deepcopy(GOOD)
    r.update(changes)
    return checker.check(r)


def test_good_record_passes(checker):
    assert errors(checker) == []


@pytest.mark.parametrize("changes, expect", [
    ({"score": 6}, "outside"),
    ({"score": 2.5}, "whole number"),
    ({"flag": "not_policy"}, "null when flag"),
    ({"score": 5}, "explicit"),
    ({"member_id": "ueda"}, "not a BoE member"),
    ({"timestamp": "2026-09-03 14:00"}, "UTC"),
    ({"source_type": "tweet"}, "unknown source_type"),
    ({"passage": "We must hike immediately."}, "not verbatim"),
    ({"rubric_version": "v0"}, "rubric_version"),
    ({"key_quote": "word " * 41}, "40 words"),
    ({"passage_weight_share": 0}, "above 0"),
])
def test_bad_records_rejected(checker, changes, expect):
    assert any(expect in e for e in errors(checker, **changes)), errors(checker, **changes)


def test_curly_quotes_and_spacing_still_count_as_verbatim(checker):
    assert errors(checker, passage="we  cannot wait for\nuncertainties to resolve.") == []


def test_shares_must_sum_to_one(monkeypatch):
    monkeypatch.setattr(v.Checker, "check", lambda self, r: [])
    monkeypatch.setattr(v, "rubric_version", lambda: "v1")
    a = dict(GOOD, id="doc-1-p01", passage_weight_share=0.5)
    b = dict(GOOD, id="doc-1-p02", passage_weight_share=0.4)
    errs = v.validate([], [a, b])
    assert any("sum to 0.9000" in e for e in errs)
    assert v.validate([], [a, dict(b, passage_weight_share=0.5)]) == []


def test_duplicate_ids_rejected(monkeypatch):
    monkeypatch.setattr(v.Checker, "check", lambda self, r: [])
    errs = v.validate([GOOD], [GOOD])
    assert any("duplicate id" in e for e in errs)


# ---- compare

def test_compare_metrics():
    labels = [{"statement_id": f"s{i}", "score": s, "flag": None} for i, s in enumerate([3, -2, 0, 1])]
    scores = [{"id": "s0", "score": 3}, {"id": "s1", "score": -1}, {"id": "s2", "score": 2},
              {"id": "s3", "score": None, "flag": "need_context"}]
    m = compare(labels, scores)["overall"]
    assert m["n"] == 3
    assert m["exact"] == pytest.approx(1 / 3)
    assert m["within_1"] == pytest.approx(2 / 3)
    assert m["average_gap"] == pytest.approx(1.0)
    assert m["bias"] == pytest.approx(1.0)


def test_spearman_handles_ties():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 1, 2, 3], [3, 3, 2, 1]) == pytest.approx(-1.0)


def test_append_ignores_the_incoming_file(tmp_path):
    from pipeline.store import append_scores
    incoming = tmp_path / "incoming.jsonl"
    rec = dict(GOOD)
    incoming.write_text(json.dumps(rec) + "\n")
    assert append_scores([rec], scores_dir=tmp_path) == 1
    assert (tmp_path / "2026-09.jsonl").exists()
    assert append_scores([rec], scores_dir=tmp_path) == 0  # already stored
