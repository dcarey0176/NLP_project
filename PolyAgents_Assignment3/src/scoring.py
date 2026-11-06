"""Shared answer extraction and exact-match scoring, used identically for the baseline and the agent team."""
import re

NUM = r"-?\d[\d,]*(?:\.\d+)?|-?\.\d+"
ANSWER_LINE = re.compile(r"answer\s*[:=]\s*\**\s*\$?\s*(" + NUM + ")", re.IGNORECASE)
ANY_NUM = re.compile(NUM)
TOL = 1e-4


def parse_answer(text):
    """Return a float or None.

    Rule order: (1) the LAST 'Answer: <number>' match (the format the prompt asks for);
    (2) otherwise the last number anywhere in the output; (3) otherwise None (counted as a format failure).
    Commas, '$' and '**' markdown are ignored. Fractions/words ('nine') are not parsed.
    """
    if not text:
        return None
    m = ANSWER_LINE.findall(text)
    cand = m[-1] if m else (ANY_NUM.findall(text) or [None])[-1]
    if cand is None:
        return None
    try:
        return float(cand.replace(",", ""))
    except ValueError:
        return None


def is_correct(pred, gold, tol=TOL):
    """Exact match on the numeric value; 9, 9.0 and 9.00 are equal. None / failed calls are wrong."""
    return pred is not None and abs(pred - gold) <= tol


def exact_match(preds, golds):
    """Acc_EM = (1/N) * sum 1[parse(y_hat_i) == y*_i]; every item counts in N, including failures."""
    assert len(preds) == len(golds)
    return sum(is_correct(p, g) for p, g in zip(preds, golds)) / len(golds) if golds else float("nan")
