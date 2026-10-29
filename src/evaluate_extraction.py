"""Evaluate invoice extraction field by field on a labelled dataset.

Usage:  python -m src.evaluate_extraction                            (default set)
        python -m src.evaluate_extraction data/other_invoices.json

Prints per-field accuracy, lists every wrong field, and saves the full results
to results/ so different models and prompts can be compared.
"""
import json
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

from src.extraction import extract_invoice
from src.llm import MODEL

DEFAULT_DATASET = Path("data/sample_invoices.json")
RESULTS_DIR = Path("results")
FIELDS = ["supplier", "invoice_number", "invoice_date", "due_date", "total_amount", "currency", "category"]


def normalize(field: str, value):
    """Make harmless formatting differences count as correct."""
    if value is None:
        return None
    if field in ("supplier", "invoice_number"):
        # "Papelaria Central, Lda." == "papelaria central lda"; "#4521" == "4521"
        return re.sub(r"[^a-z0-9]", "", str(value).lower()) or None
    if field == "total_amount":
        return round(float(value), 2)
    if field == "currency":
        return str(value).upper()
    return str(value)  # ISO dates and category


def main() -> None:
    dataset = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATASET
    invoices = json.loads(dataset.read_text(encoding="utf-8"))
    print(f"Dataset: {dataset} ({len(invoices)} invoices)\n")
    rows = []
    start = time.perf_counter()

    for i, item in enumerate(invoices, start=1):
        first_line = item["text"].strip().splitlines()[0]
        print(f"[{i}/{len(invoices)}] {first_line[:55]}")
        try:
            result = extract_invoice(item["text"], reference_date=date.fromisoformat(item["reference_date"]))
            predicted = result.model_dump(mode="json")
        except Exception as error:  # one failure should not stop the evaluation
            predicted = {field: f"error: {error}" for field in FIELDS}

        expected = item["expected"]
        field_ok = {f: normalize(f, predicted.get(f)) == normalize(f, expected.get(f)) for f in FIELDS}
        rows.append(
            {
                "text": item["text"],
                "expected": expected,
                "predicted": predicted,
                "field_ok": field_ok,
                "all_ok": all(field_ok.values()),
                "note": item.get("note", ""),
            }
        )

    elapsed = time.perf_counter() - start
    n = len(rows)
    field_acc = {f: sum(r["field_ok"][f] for r in rows) / n for f in FIELDS}
    all_acc = sum(r["all_ok"] for r in rows) / n

    print(f"\nModel: {MODEL}")
    print(f"Dataset: {dataset}")
    for f in FIELDS:
        print(f"  {f:<15} {field_acc[f]:.0%}")
    print(f"All fields correct: {all_acc:.0%}")
    print(f"Avg time per invoice: {elapsed / n:.1f}s")

    mistakes = [r for r in rows if not r["all_ok"]]
    if mistakes:
        print("\nMistakes:")
        for r in mistakes:
            print(f"- {r['text'].strip().splitlines()[0][:70]}")
            for f in FIELDS:
                if not r["field_ok"][f]:
                    print(f"    {f}: expected {r['expected'].get(f)!r}, got {r['predicted'].get(f)!r}")
            if r["note"]:
                print(f"    note: {r['note']}")

    RESULTS_DIR.mkdir(exist_ok=True)
    safe_model = re.sub(r"[^\w.-]", "_", MODEL)
    out = RESULTS_DIR / f"eval_extraction_{dataset.stem}_{safe_model}_{datetime.now():%Y%m%d_%H%M}.json"
    summary = {
        "model": MODEL,
        "dataset": str(dataset),
        "n_invoices": n,
        "field_accuracy": {f: round(a, 3) for f, a in field_acc.items()},
        "all_fields_accuracy": round(all_acc, 3),
        "avg_seconds_per_invoice": round(elapsed / n, 2),
    }
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved full results to {out}")


if __name__ == "__main__":
    main()