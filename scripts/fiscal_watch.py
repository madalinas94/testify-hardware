"""Verificarea automată a Codului fiscal: propune reguli noi în app/fiscal/ro.json.

Rulează săptămânal pe GitHub (vezi .github/workflows/fiscal-watch.yml) sau manual:

    ANTHROPIC_API_KEY=... python scripts/fiscal_watch.py

Pasul 1: Claude caută pe internet modificări ale cotelor pe care le folosește aplicația.
Pasul 2: rezultatul este transformat într-un JSON strict și validat de aplicație.
Dacă există schimbări, scriptul actualizează ro.json și scrie descrierea propunerii în
fiscal_update.md. Nu se aplică nimic fără aprobare: GitHub deschide o propunere de
modificare (pull request), pe care un om o verifică și o acceptă.
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.fiscal import RATE_KEYS, RATE_LABELS, validate_feed, version_key  # noqa: E402

RULES_FILE = ROOT / "app" / "fiscal" / "ro.json"
REPORT_FILE = ROOT / "fiscal_update.md"
MODEL = "claude-opus-5-5"
MAX_CONTINUATIONS = 5
OFFICIAL_DOMAINS = ("legislatie.just.ro", "monitoruloficial.ro", "anaf.ro", "mfinante.gov.ro",
                    "gov.ro", "cdep.ro", "senat.ro")

RESEARCH_PROMPT = """Ești un asistent care urmărește legislația fiscală din România pentru o aplicație de \
contabilitate de gestiune a unei firme mici (SRL plătitoare de TVA și de impozit pe profit, cu angajați).

Aplicația folosește aceste cote (în procente), cu data de la care se aplică fiecare set:
{rates}

Regulile pe care le are acum aplicația (JSON):
{current}

Data de azi: {today}.

Sarcina ta: caută pe internet dacă există modificări ale ACESTOR cote care nu sunt încă în regulile de mai sus:
- modificări deja în vigoare, apărute după ultima regulă;
- modificări adoptate (lege, ordonanță publicată în Monitorul Oficial) care intră în vigoare în viitor.

Reguli:
- Folosește surse oficiale (Monitorul Oficial, legislatie.just.ro, ANAF, Ministerul Finanțelor, Parlament) sau \
presă economică de încredere care citează actul normativ. Dă linkurile.
- Ignoră proiectele, propunerile și zvonurile neadoptate. Spune explicit dacă ai găsit doar propuneri.
- Pentru fiecare modificare: cota veche, cota nouă, data exactă de intrare în vigoare, actul normativ.
- Dacă nu găsești nicio modificare adoptată, spune clar „Nicio modificare adoptată”.
Răspunde în română, concis."""

EXTRACT_PROMPT = """Mai jos sunt regulile fiscale actuale ale aplicației și rezultatul unei cercetări despre \
modificări. Transformă DOAR modificările adoptate oficial (nu propunerile) în reguli noi.

Fiecare regulă nouă conține TOATE cotele valabile de la data ei (copiază cotele neschimbate din regula \
anterioară), un titlu scurt, 1–3 explicații pentru un antreprenor fără cunoștințe fiscale (ce se schimbă și \
ce înseamnă pentru el) și sursele (linkuri). Dacă nu există modificări adoptate, întoarce o listă goală.

Regulile actuale:
{current}

Rezultatul cercetării:
{research}"""

RULE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "new_rules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "effective_from": {"type": "string", "format": "date"},
                    "title": {"type": "string"},
                    "rates": {
                        "type": "object",
                        "properties": {key: {"type": "number"} for key in RATE_KEYS},
                        "required": list(RATE_KEYS),
                        "additionalProperties": False,
                    },
                    "changes": {"type": "array", "items": {"type": "string"}},
                    "sources": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["effective_from", "title", "rates", "changes", "sources"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "new_rules"],
    "additionalProperties": False,
}


def text_of(response) -> str:
    return "\n".join(block.text for block in response.content if block.type == "text").strip()


def research(client, current: dict, today: str) -> str:
    """Pasul 1: căutare pe internet, cu reluare dacă serverul pune căutarea pe pauză."""
    rates = "\n".join(f"- {key}: {label}" for key, label in RATE_LABELS.items())
    prompt = RESEARCH_PROMPT.format(rates=rates, current=json.dumps(current, ensure_ascii=False, indent=1),
                                    today=today)
    messages = [{"role": "user", "content": prompt}]
    for _ in range(MAX_CONTINUATIONS):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "high"},
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 20}],
            messages=messages,
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Modelul a refuzat cercetarea.")
        if response.stop_reason != "pause_turn":
            return text_of(response)
        messages = [{"role": "user", "content": prompt}, {"role": "assistant", "content": response.content}]
    raise RuntimeError("Cercetarea nu s-a terminat după mai multe reluări.")


def extract(client, current: dict, findings: str) -> dict:
    """Pasul 2: din textul cercetării, reguli în format strict (JSON validat de API)."""
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": RULE_SCHEMA}},
        messages=[{"role": "user", "content": EXTRACT_PROMPT.format(
            current=json.dumps(current, ensure_ascii=False, indent=1), research=findings)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Modelul a refuzat extragerea regulilor.")
    return json.loads(text_of(response))


def next_version(current: str | None, today: date) -> str:
    major, *rest = version_key(current) or (today.year,)
    if major == today.year:
        return f"{major}.{(rest[0] if rest else 0) + 1}"
    return f"{today.year}.1"


def merge_rules(feed: dict, proposals: list[dict], today: date) -> tuple[dict, list[dict]]:
    """Adaugă regulile noi sau modificate; întoarce feed-ul nou și ce s-a schimbat."""
    existing = {rule["effective_from"]: rule for rule in feed["rules"]}
    changed = []
    for proposal in proposals:
        rates = {key: proposal["rates"][key] for key in RATE_KEYS}
        old = existing.get(proposal["effective_from"])
        if old and all(float(old["rates"][key]) == float(rates[key]) for key in RATE_KEYS):
            continue  # regula există deja, cu aceleași cote
        rule = {"effective_from": proposal["effective_from"], "title": proposal["title"],
                "rates": rates, "changes": proposal["changes"], "sources": proposal["sources"]}
        existing[rule["effective_from"]] = rule
        changed.append(rule)
    if not changed:
        return feed, []
    new_feed = {**feed, "rules": sorted(existing.values(), key=lambda r: r["effective_from"]),
                "version": next_version(feed.get("version"), today), "published": today.isoformat()}
    validate_feed(new_feed)  # aceeași validare ca în aplicație: cote între 0 și 100, toate prezente
    return new_feed, changed


def report(summary: str, changed: list[dict], findings: str) -> str:
    lines = ["## Propunere automată: modificări în Codul fiscal", "",
             "Verificarea săptămânală a găsit modificări ale cotelor folosite de aplicație.",
             "**Verificați sursele înainte de a accepta.** După acceptare, toate aplicațiile se",
             "actualizează singure în cel mult 6 ore.", "", f"**Rezumat:** {summary}", ""]
    for rule in changed:
        lines += [f"### {rule['title']} (de la {rule['effective_from']})", ""]
        lines += [f"- {change}" for change in rule["changes"]]
        lines += ["", "Cote: " + ", ".join(f"{RATE_LABELS[k]} {rule['rates'][k]:g}%" for k in RATE_KEYS), ""]
        official = [s for s in rule["sources"] if any(d in s for d in OFFICIAL_DOMAINS)]
        lines += ["**Surse:**"] + [f"- {source}" for source in rule["sources"]]
        if not official:
            lines += ["", "> ⚠️ Nicio sursă oficială (Monitorul Oficial, ANAF, legislatie.just.ro). "
                          "Verificați cu atenție sau cu contabilul."]
        lines.append("")
    lines += ["<details><summary>Cercetarea completă</summary>", "", findings, "", "</details>", "",
              "---", "_Generat automat de verificarea fiscală (Claude)._"]
    return "\n".join(lines)


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Lipsește ANTHROPIC_API_KEY. Adăugați-l în Settings → Secrets and variables → Actions.")
        return 2
    today = date.today()
    feed = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    client = anthropic.Anthropic()
    findings = research(client, feed, today.isoformat())
    extracted = extract(client, feed, findings)
    new_feed, changed = merge_rules(feed, extracted["new_rules"], today)
    if not changed:
        print("Nicio modificare nouă adoptată. Regulile fiscale sunt la zi.")
        print(extracted["summary"])
        return 0
    RULES_FILE.write_text(json.dumps(new_feed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_FILE.write_text(report(extracted["summary"], changed, findings), encoding="utf-8")
    print(f"Am propus {len(changed)} reguli noi (versiunea {new_feed['version']}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
