#!/usr/bin/env python3
"""Rebuild small, attributed public-data subsets using only the standard library."""

import csv
import hashlib
import io
import json
import urllib.request
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent / "datasets"
BOOLQ_URL = "https://datasets-server.huggingface.co/rows?dataset=google/boolq&config=default&split=validation&offset=0&length=100"
BOOLQ_SHA = "3decb23d0a08673127d5c8ba12843c83b12152b637fba87d883b950b2b9fef36"
BANKING_URL = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/57ec275d8078af65b7731c2a98be812d844a6d6b/banking_data/test.csv"
BANKING_SHA = "d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d"
INTENTS = {
    "card_arrival": "Physical card has not arrived",
    "card_not_working": "Physical card does not work",
    "lost_or_stolen_card": "Physical card is lost or stolen",
    "wrong_amount_of_cash_received": "ATM dispensed the wrong cash amount",
    "cash_withdrawal_charge": "Fee charged for an ATM cash withdrawal",
    "change_pin": "Changing the card PIN",
    "pending_card_payment": "Card payment remains pending",
    "pending_cash_withdrawal": "ATM cash withdrawal remains pending",
    "cancel_transfer": "Cancelling a transfer",
    "failed_transfer": "Transfer failed",
    "card_swallowed": "ATM retained the physical card",
    "card_payment_wrong_exchange_rate": "Wrong exchange rate on a card payment",
}


def download(url, expected_sha):
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise ValueError("Upstream bytes changed; review provenance before updating the SHA-256")
    return data


def save(name, metadata, cases):
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / f"{name}.json").write_text(
        json.dumps({"dataset": metadata, "cases": cases}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    rows = json.loads(download(BOOLQ_URL, BOOLQ_SHA))["rows"]
    counts = {True: 0, False: 0}
    cases = []
    for item in rows:
        row = item["row"]
        label = row["answer"]
        if counts[label] >= 12:
            continue
        counts[label] += 1
        cases.append({
            "id": f"boolq-validation-{item['row_idx']}", "type": "noul",
            "state": row["passage"],
            "instructions": "Answer this yes/no question using the passage: " + row["question"],
            "expected": label, "source_row": item["row_idx"],
        })
    assert counts == {True: 12, False: 12}
    save("boolq", {
        "name": "BoolQ", "split": "validation", "license": "CC-BY-SA-3.0",
        "source": "https://huggingface.co/datasets/google/boolq",
        "revision_at_download": "35b264d03638db9f4ce671b711558bf7ff0f80d5",
        "download_url": BOOLQ_URL, "download_sha256": BOOLQ_SHA,
        "selection": "First 12 rows per boolean label within the first 100 validation rows; full passages, no truncation.",
    }, cases)
    rows = csv.DictReader(io.StringIO(download(BANKING_URL, BANKING_SHA).decode("utf-8")))
    counts = dict.fromkeys(INTENTS, 0)
    cases = []
    for index, row in enumerate(rows):
        label = row["category"]
        if label not in counts or counts[label] >= 2:
            continue
        counts[label] += 1
        cases.append({
            "id": f"banking77-test-{index}", "type": "choice", "state": row["text"],
            "instructions": "Classify the customer's banking intent into one of the provided categories.",
            "choices": INTENTS, "expected": label, "source_row": index,
        })
    assert all(count == 2 for count in counts.values())
    save("banking77", {
        "name": "BANKING77 (12-intent adaptation)", "split": "test", "license": "CC-BY-4.0",
        "source": "https://github.com/PolyAI-LDN/task-specific-datasets",
        "download_url": BANKING_URL, "download_sha256": BANKING_SHA,
        "selection": "First 2 test rows per 12 selected intents, original text preserved; 12-way classification, not the official 77-way task.",
    }, cases)
    print("Saved 24 BoolQ and 24 adapted BANKING77 cases")


if __name__ == "__main__":
    main()
