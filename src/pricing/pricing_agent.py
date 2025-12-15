"""Pricing agent that validates internal marks against market data."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List
import os
import time

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

from src.pricing.normalizer import MarketNormalizer
from src.pricing.schema import EnrichedMark, Mark
from src.pricing.logger import setup_logger


class PricingAgent:
    """Run mark validation and reporting."""

    def __init__(self, normalizer: MarketNormalizer | None = None):
        setup_logger()
        self.normalizer = normalizer or MarketNormalizer()
        self.logger = logging.getLogger(__name__)
        self.perf_budget_ms = self.normalizer.tolerances.get("perf_budget_ms", 30000)

    def _load_marks(self, marks_input) -> List[Dict[str, Any]]:
        if isinstance(marks_input, list):
            return marks_input
        if isinstance(marks_input, str):
            path = Path(marks_input)
            if not path.exists():
                raise FileNotFoundError(f"Marks file not found: {marks_input}")
            if path.suffix.lower() == ".csv":
                if pd is None:
                    raise ImportError("pandas required to read CSV marks")
                return pd.read_csv(path).to_dict(orient="records")
            if path.suffix.lower() in (".json", ".jsonl"):
                data = json.loads(path.read_text())
                return data if isinstance(data, list) else [data]
            raise ValueError("Unsupported marks file format")
        if pd is not None and hasattr(marks_input, "to_dict"):
            return marks_input.to_dict(orient="records")
        raise ValueError("marks_input must be list/CSV/JSON/DataFrame path/object")

    def run(self, marks_input) -> Dict[str, Any]:
        start_ts = time.perf_counter()
        marks_records = self._load_marks(marks_input)
        self.logger.info("pricing_agent start count=%d", len(marks_records))
        enriched: List[EnrichedMark] = self.normalizer.enrich_marks(marks_records)
        enriched_dicts = [m.model_dump() for m in enriched]
        summary = self._aggregate(enriched)
        explanations = [self._explain(m) for m in enriched]
        for idx, exp in enumerate(explanations):
            enriched_dicts[idx]["explanation"] = exp
        duration_ms = (time.perf_counter() - start_ts) * 1000
        self.logger.info("pricing_agent complete count=%d duration_ms=%.2f", len(enriched_dicts), duration_ms)
        self._audit(enriched_dicts)
        self._write_metrics(enriched_dicts, summary, duration_ms)
        return {
            "enriched_marks": enriched_dicts,
            "summary": {**summary, "duration_ms": duration_ms, "within_budget": duration_ms <= self.perf_budget_ms},
        }

    def evaluate_dataset(self, marks_path: str | Path) -> Dict[str, Any]:
        """Evaluate processing of a dataset: classifications/explanations present and perf budget met."""
        start = time.perf_counter()
        report = self.run(marks_path)
        duration_ms = (time.perf_counter() - start) * 1000
        enriched = report["enriched_marks"]
        missing_explanations = [m["ticker"] for m in enriched if not m.get("explanation")]
        missing_classifications = [m["ticker"] for m in enriched if not m.get("classification")]
        pass_rate = 1.0 if not missing_explanations and not missing_classifications else (
            1 - (len(missing_explanations) + len(missing_classifications)) / max(len(enriched), 1)
        )
        return {
            "duration_ms": duration_ms,
            "within_budget": duration_ms <= self.perf_budget_ms,
            "missing_explanations": missing_explanations,
            "missing_classifications": missing_classifications,
            "pass_rate": pass_rate,
            "summary": report["summary"],
        }

    def _aggregate(self, marks: List[EnrichedMark]) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        deviations: List[float] = []
        for m in marks:
            cls = m.classification
            counts[cls] = counts.get(cls, 0) + 1
            if m.deviation_percentage is not None:
                deviations.append(abs(m.deviation_percentage))
        total = len(marks)
        avg_dev = sum(deviations) / len(deviations) if deviations else None
        max_dev = max(deviations) if deviations else None
        top_tickers = sorted({m.ticker for m in marks if m.classification != "OK"})
        return {
            "counts": counts,
            "total_marks": total,
            "average_deviation": avg_dev,
            "max_deviation": max_dev,
            "top_tickers": top_tickers,
        }

    def _explain(self, mark: EnrichedMark) -> str:
        cls = mark.classification
        if cls == "OUT_OF_TOLERANCE":
            return (
                f"{mark.ticker} mark {mark.internal_mark} vs market {mark.market_price} "
                f"({mark.deviation_percentage:.2%} off); check for stale data, corp actions, or input errors."
            )
        if cls == "REVIEW_NEEDED":
            return (
                f"{mark.ticker} mark {mark.internal_mark} vs market {mark.market_price} "
                f"({mark.deviation_percentage:.2%} off); moderate variance, verify source."
            )
        if cls == "NO_MARKET_DATA":
            return f"{mark.ticker} missing market data; investigate data source or ticker mapping. {mark.error or ''}".strip()
        if cls == "STALE_MARK":
            return f"{mark.ticker} mark dated {mark.as_of_date} exceeds stale threshold; refresh required."
        return f"{mark.ticker} within tolerance."

    def _audit(self, enriched: List[Dict[str, Any]]) -> None:
        """Append audit entries to file if PRICING_AUDIT_LOG is set."""
        audit_path = os.getenv("PRICING_AUDIT_LOG")
        if not audit_path:
            return
        try:
            path = Path(audit_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                for m in enriched:
                    f.write(json.dumps(m, ensure_ascii=False) + "\n")
        except Exception as exc:
            self.logger.warning("audit write failed: %s", exc)

    def _write_metrics(self, enriched: List[Dict[str, Any]], summary: Dict[str, Any], duration_ms: float) -> None:
        """Write simple metrics JSONL if PRICING_METRICS_LOG is set."""
        metrics_path = os.getenv("PRICING_METRICS_LOG")
        if not metrics_path:
            return
        counts = summary.get("counts", {})
        payload = {
            "ts_ms": int(time.time() * 1000),
            "total_marks": summary.get("total_marks", len(enriched)),
            "counts": counts,
            "duration_ms": duration_ms,
            "max_deviation": summary.get("max_deviation"),
            "average_deviation": summary.get("average_deviation"),
        }
        try:
            path = Path(metrics_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception as exc:
            self.logger.warning("metrics write failed: %s", exc)


def generate_report(enriched_payload: Dict[str, Any], output_path: str | None = None, output_format: str = "md") -> str:
    """Build a simple report; supports Markdown or JSON. Returns the report string."""
    if output_format == "json":
        report = json.dumps(enriched_payload, indent=2)
        if output_path:
            Path(output_path).write_text(report, encoding="utf-8")
        return report

    lines = []
    summary = enriched_payload.get("summary", {})
    lines.append("# Pricing Report")
    lines.append("")
    lines.append("## Summary")
    for k, v in summary.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Details")
    for mark in enriched_payload.get("enriched_marks", []):
        lines.append(
            f"- {mark['ticker']} ({mark['as_of_date']}): {mark['classification']} | "
            f"internal {mark['internal_mark']} vs market {mark.get('market_price')} | "
            f"dev {mark.get('deviation_percentage')}"
        )
        if mark.get("explanation"):
            lines.append(f"  - {mark['explanation']}")
    report = "\n".join(lines)
    if output_path:
        Path(output_path).write_text(report, encoding="utf-8")
    return report
