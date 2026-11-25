"""Recurring-subscription detection from bank-statement CSVs."""

from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from typing import Any

import pandas as pd

# ------------------------------------------------------------------
# Merchant normalisation
# ------------------------------------------------------------------

_NOISE_TOKENS = {
    'payment', 'purchase', 'debit', 'credit', 'pos', 'ach', 'direct',
    'recurring', 'authorized', 'transaction', 'ref', 'card', 'online',
}


def normalize_merchant(name: str) -> str:
    """Lowercase, strip digits/noise tokens, collapse whitespace.

    Args:
        name: Raw merchant / description string from the CSV.

    Returns:
        A cleaned, normalised merchant identifier.
    """
    text = name.lower()
    text = re.sub(r'[^a-z\s]', ' ', text)          # drop non-alpha
    tokens = [t for t in text.split() if t not in _NOISE_TOKENS]
    return ' '.join(tokens).strip() or name.lower()


# ------------------------------------------------------------------
# Interval classification
# ------------------------------------------------------------------

def classify_interval(avg_gap: float) -> str | None:
    """Map an average inter-transaction gap (days) to a billing interval.

    Args:
        avg_gap: Mean number of days between consecutive transactions.

    Returns:
        One of ``'weekly'``, ``'monthly'``, ``'quarterly'``, ``'yearly'``,
        or ``None`` if the gap doesn't match a known cycle.
    """
    if 5 <= avg_gap <= 9:
        return 'weekly'
    if 25 <= avg_gap <= 35:
        return 'monthly'
    if 85 <= avg_gap <= 100:
        return 'quarterly'
    if 350 <= avg_gap <= 380:
        return 'yearly'
    return None


# ------------------------------------------------------------------
# Confidence scoring
# ------------------------------------------------------------------

def calculate_confidence(gaps: list[float], amounts: list[Decimal], count: int) -> int:
    """Score how likely a set of transactions represents a subscription.

    Considers interval consistency, amount consistency, and occurrence
    count.

    Args:
        gaps: List of day-gaps between consecutive transactions.
        amounts: List of transaction amounts (absolute values).
        count: Total number of transactions for this merchant.

    Returns:
        An integer confidence score between 0 and 100.
    """
    score = 0

    # --- Interval consistency (up to 40 pts) -------------------------
    if gaps:
        mean_gap = sum(gaps) / len(gaps)
        if mean_gap > 0:
            deviations = [abs(g - mean_gap) / mean_gap for g in gaps]
            avg_dev = sum(deviations) / len(deviations)
            interval_score = max(0, 40 - int(avg_dev * 100))
            score += interval_score

    # --- Amount consistency (up to 35 pts) ---------------------------
    if amounts:
        avg_amount = sum(amounts) / len(amounts)
        if avg_amount > 0:
            amount_devs = [abs(float(a) - float(avg_amount)) / float(avg_amount) for a in amounts]
            avg_amount_dev = sum(amount_devs) / len(amount_devs)
            amount_score = max(0, 35 - int(avg_amount_dev * 100))
            score += amount_score

    # --- Occurrence count (up to 25 pts) -----------------------------
    if count >= 12:
        score += 25
    elif count >= 6:
        score += 20
    elif count >= 4:
        score += 15
    elif count >= 3:
        score += 10
    elif count >= 2:
        score += 5

    return min(score, 100)


# ------------------------------------------------------------------
# Main detection algorithm
# ------------------------------------------------------------------

def detect_recurring(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Identify recurring charges in a transaction DataFrame.

    The DataFrame must have columns ``date``, ``description`` and ``amount``
    (all lowercase).  Transactions are grouped by normalised merchant name,
    then gap analysis and confidence scoring determine which are likely
    subscriptions.

    Args:
        df: Cleaned transactions DataFrame (see :func:`parse_csv`).

    Returns:
        A list of dicts, each with keys ``merchant_name``,
        ``normalized_name``, ``amount``, ``interval``, ``confidence``,
        ``next_expected_date``, and ``transaction_count``.
    """
    results: list[dict[str, Any]] = []

    df = df.copy()
    df['normalized'] = df['description'].apply(normalize_merchant)
    df['abs_amount'] = df['amount'].abs()
    df = df.sort_values('date')

    for norm_name, group in df.groupby('normalized'):
        if len(group) < 3:
            continue

        sorted_group = group.sort_values('date')
        dates = sorted_group['date'].tolist()
        amounts = [Decimal(str(a)) for a in sorted_group['abs_amount'].tolist()]

        # Calculate gaps
        gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        gaps = [g for g in gaps if g > 0]

        if not gaps:
            continue

        avg_gap = sum(gaps) / len(gaps)
        interval = classify_interval(avg_gap)
        if interval is None:
            continue

        confidence = calculate_confidence(gaps, amounts, len(group))
        if confidence < 30:
            continue

        avg_amount = sum(amounts) / len(amounts)

        # Predict next expected date
        last_date = max(dates)
        delta_map = {
            'weekly': timedelta(weeks=1),
            'monthly': timedelta(days=30),
            'quarterly': timedelta(days=91),
            'yearly': timedelta(days=365),
        }
        next_date = last_date + delta_map.get(interval, timedelta(days=30))

        # Use the most common raw merchant name
        merchant_name = sorted_group['description'].mode().iloc[0]

        results.append({
            'merchant_name': merchant_name,
            'normalized_name': norm_name,
            'amount': avg_amount.quantize(Decimal('0.01')),
            'interval': interval,
            'confidence': confidence,
            'next_expected_date': next_date if isinstance(next_date, date) else None,
            'transaction_count': len(group),
        })

    # Sort by confidence descending
    results.sort(key=lambda r: r['confidence'], reverse=True)
    return results


# ------------------------------------------------------------------
# CSV parsing
# ------------------------------------------------------------------

_DATE_COLUMN_NAMES = {'date', 'transaction date', 'trans date', 'posting date', 'booked date'}
_DESC_COLUMN_NAMES = {'description', 'merchant', 'name', 'memo', 'details', 'payee', 'narrative'}
_AMOUNT_COLUMN_NAMES = {'amount', 'debit', 'value', 'transaction amount'}


def _find_column(columns: list[str], candidates: set[str]) -> str | None:
    """Case-insensitive column-name matching."""
    lower_map = {c.lower().strip(): c for c in columns}
    for candidate in candidates:
        if candidate in lower_map:
            return lower_map[candidate]
    return None


def parse_csv(file) -> pd.DataFrame:
    """Read and normalise a bank-statement CSV.

    Attempts to auto-detect date, description, and amount columns.

    Args:
        file: A file-like object or Django ``UploadedFile``.

    Returns:
        A DataFrame with lowercase columns ``date``, ``description``,
        and ``amount``.

    Raises:
        ValueError: If required columns cannot be detected.
    """
    content = file.read()
    if isinstance(content, bytes):
        content = content.decode('utf-8', errors='replace')

    df = pd.read_csv(StringIO(content))
    df.columns = [c.strip() for c in df.columns]

    date_col = _find_column(df.columns.tolist(), _DATE_COLUMN_NAMES)
    desc_col = _find_column(df.columns.tolist(), _DESC_COLUMN_NAMES)
    amount_col = _find_column(df.columns.tolist(), _AMOUNT_COLUMN_NAMES)

    if not date_col:
        raise ValueError('Could not detect a date column. Expected one of: ' + ', '.join(_DATE_COLUMN_NAMES))
    if not desc_col:
        raise ValueError('Could not detect a description column. Expected one of: ' + ', '.join(_DESC_COLUMN_NAMES))
    if not amount_col:
        raise ValueError('Could not detect an amount column. Expected one of: ' + ', '.join(_AMOUNT_COLUMN_NAMES))

    result = pd.DataFrame()
    # pandas 2.0 removed infer_datetime_format; format inference is now the default.
    result['date'] = pd.to_datetime(df[date_col], errors='coerce')
    result['description'] = df[desc_col].astype(str).str.strip()
    result['amount'] = pd.to_numeric(
        df[amount_col].astype(str).str.replace(r'[^\d.\-]', '', regex=True),
        errors='coerce',
    )

    result = result.dropna(subset=['date', 'description', 'amount'])
    result['date'] = result['date'].dt.date

    if result.empty:
        raise ValueError('No valid rows found after parsing. Check your CSV format.')

    return result
