"""Verificarea automată a Codului fiscal, testată fără internet și fără cheie API."""

import json
from datetime import date
from types import SimpleNamespace

import pytest

from app import fiscal
from scripts import fiscal_watch


def current_feed():
    return json.loads(fiscal.BUNDLED_RULES.read_text(encoding="utf-8"))


def proposal(**overrides):
    rates = {**current_feed()["rules"][-1]["rates"], **overrides.pop("rates", {})}
    return {"effective_from": "2027-01-01", "title": "TVA 23%", "rates": rates,
            "changes": ["Cota standard de TVA crește la 23%."],
            "sources": ["https://legislatie.just.ro/exemplu"], **overrides}


class FakeMessages:
    """Primul apel: cercetarea (cu o pauză), al doilea: extragerea JSON."""

    def __init__(self, extracted):
        self.calls = []
        self.replies = [
            SimpleNamespace(stop_reason="pause_turn", content=[SimpleNamespace(type="text", text="caut…")]),
            SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="Cercetare.")]),
            SimpleNamespace(stop_reason="end_turn",
                            content=[SimpleNamespace(type="text", text=json.dumps(extracted))]),
        ]

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.replies[len(self.calls) - 1]


def test_new_rule_is_added_with_a_higher_version():
    feed = current_feed()
    new_feed, changed = fiscal_watch.merge_rules(feed, [proposal(rates={"vat_standard_rate": 23})],
                                                 date(2026, 12, 1))
    assert len(changed) == 1
    assert new_feed["rules"][-1]["rates"]["vat_standard_rate"] == 23
    assert fiscal.version_key(new_feed["version"]) > fiscal.version_key(feed["version"])


def test_rule_that_already_exists_is_not_proposed_again():
    feed = current_feed()
    same = {**feed["rules"][-1], "sources": []}
    assert fiscal_watch.merge_rules(feed, [same], date(2026, 12, 1)) == (feed, [])


def test_invalid_rates_are_rejected():
    with pytest.raises(ValueError):
        fiscal_watch.merge_rules(current_feed(), [proposal(rates={"vat_standard_rate": 230})],
                                 date(2026, 12, 1))


def test_version_numbering():
    assert fiscal_watch.next_version("2026.2", date(2026, 12, 1)) == "2026.3"
    assert fiscal_watch.next_version("2026.2", date(2027, 1, 5)) == "2027.1"


def test_full_run_writes_rules_and_report(tmp_path, monkeypatch):
    rules = tmp_path / "ro.json"
    rules.write_text(fiscal.BUNDLED_RULES.read_text(encoding="utf-8"), encoding="utf-8")
    report = tmp_path / "fiscal_update.md"
    monkeypatch.setattr(fiscal_watch, "RULES_FILE", rules)
    monkeypatch.setattr(fiscal_watch, "REPORT_FILE", report)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    fake = FakeMessages({"summary": "TVA crește la 23%.",
                         "new_rules": [proposal(rates={"vat_standard_rate": 23})]})
    monkeypatch.setattr(fiscal_watch.anthropic, "Anthropic",
                        lambda: SimpleNamespace(beta=SimpleNamespace(messages=fake)))

    assert fiscal_watch.main() == 0
    assert json.loads(rules.read_text())["rules"][-1]["rates"]["vat_standard_rate"] == 23
    text = report.read_text()
    assert "TVA 23%" in text and "legislatie.just.ro" in text and "Verificați sursele" in text
    # Cercetarea folosește căutarea pe internet și e reluată după pauză; extragerea cere JSON strict.
    assert fake.calls[0]["tools"][0]["type"] == "web_search_20260209"
    assert fake.calls[1]["messages"][1]["role"] == "assistant"
    assert fake.calls[2]["output_config"]["format"]["type"] == "json_schema"
    assert all(call["model"] == "claude-opus-5-5" for call in fake.calls)


def test_no_changes_writes_nothing(tmp_path, monkeypatch):
    rules = tmp_path / "ro.json"
    original = fiscal.BUNDLED_RULES.read_text(encoding="utf-8")
    rules.write_text(original, encoding="utf-8")
    monkeypatch.setattr(fiscal_watch, "RULES_FILE", rules)
    monkeypatch.setattr(fiscal_watch, "REPORT_FILE", tmp_path / "fiscal_update.md")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    fake = FakeMessages({"summary": "Nicio modificare adoptată.", "new_rules": []})
    monkeypatch.setattr(fiscal_watch.anthropic, "Anthropic",
                        lambda: SimpleNamespace(beta=SimpleNamespace(messages=fake)))
    assert fiscal_watch.main() == 0
    assert rules.read_text() == original
    assert not (tmp_path / "fiscal_update.md").exists()
