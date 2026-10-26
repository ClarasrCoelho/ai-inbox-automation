"""Evaluate the email classifier on the labelled dataset.

Usage:  python -m src.evaluate                          (development set)
        python -m src.evaluate data/test_emails.json    (held-out test set)

Prints category and urgency accuracy, lists every mistake, and saves the
full results to results/ so different models and prompts can be compared.
"""
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from src.classification import classify_email
from src.llm import MODEL

DEFAULT_DATASET = Path("data/sample_emails.json")
RESULTS_DIR = Path("results")


def main() -> None:
    dataset = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATASET
    emails = json.loads(dataset.read_text(encoding="utf-8"))
    print(f"Dataset: {dataset} ({len(emails)} emails)\n")
    rows = []
    start = time.perf_counter()

    for i, email in enumerate(emails, start=1):
        print(f"[{i}/{len(emails)}] {email['subject'][:55]}")
        try:
            result = classify_email(email["subject"], email["body"])
            category, urgency, reason = result.category, result.urgency, result.reason
        except Exception as error:  # one failure should not stop the evaluation
            category, urgency, reason = "error", "error", str(error)

        rows.append(
            {
                "subject": email["subject"],
                "expected_category": email["expected_category"],
                "predicted_category": category,
                "expected_urgency": email["expected_urgency"],
                "predicted_urgency": urgency,
                "category_ok": category == email["expected_category"],
                "urgency_ok": urgency == email["expected_urgency"],
                "reason": reason,
                "note": email.get("note", ""),
            }
        )

    elapsed = time.perf_counter() - start
    n = len(rows)
    category_acc = sum(r["category_ok"] for r in rows) / n
    urgency_acc = sum(r["urgency_ok"] for r in rows) / n
    both_acc = sum(r["category_ok"] and r["urgency_ok"] for r in rows) / n

    print(f"\nModel: {MODEL}")
    print(f"Dataset: {dataset}")
    print(f"Category accuracy: {category_acc:.0%}")
    print(f"Urgency accuracy:  {urgency_acc:.0%}")
    print(f"Both correct:      {both_acc:.0%}")
    print(f"Avg time per email: {elapsed / n:.1f}s")

    mistakes = [r for r in rows if not (r["category_ok"] and r["urgency_ok"])]
    if mistakes:
        print("\nMistakes:")
        for r in mistakes:
            print(f"- {r['subject']}")
            if not r["category_ok"]:
                print(f"    category: expected {r['expected_category']}, got {r['predicted_category']}")
            if not r["urgency_ok"]:
                print(f"    urgency:  expected {r['expected_urgency']}, got {r['predicted_urgency']}")
            print(f"    model's reason: {r['reason']}")
            if r["note"]:
                print(f"    note: {r['note']}")

    # Which categories get confused with which (expected -> predicted).
    confusions = Counter(
        f"{r['expected_category']} -> {r['predicted_category']}" for r in rows if not r["category_ok"]
    )
    if confusions:
        print("\nCategory confusions:")
        for pair, count in confusions.most_common():
            print(f"  {pair}: {count}")

    RESULTS_DIR.mkdir(exist_ok=True)
    safe_model = re.sub(r"[^\w.-]", "_", MODEL)  # e.g. "qwen2.5:7b" -> "qwen2.5_7b"
    out = RESULTS_DIR / f"eval_{dataset.stem}_{safe_model}_{datetime.now():%Y%m%d_%H%M}.json"
    summary = {
        "model": MODEL,
        "dataset": str(dataset),
        "n_emails": n,
        "category_accuracy": round(category_acc, 3),
        "urgency_accuracy": round(urgency_acc, 3),
        "both_accuracy": round(both_acc, 3),
        "avg_seconds_per_email": round(elapsed / n, 2),
    }
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved full results to {out}")


if __name__ == "__main__":
    main()
