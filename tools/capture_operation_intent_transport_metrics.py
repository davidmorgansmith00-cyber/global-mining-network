from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime


def _build_metrics_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/api/v1/blockchain/maintenance/metrics"


def _fetch_metrics(base_url: str, token_header: str, token_value: str) -> dict[str, object]:
    if not token_value:
        raise RuntimeError("Missing maintenance token; set MAINTENANCE_AUTH_TOKEN or pass --token")

    request = urllib.request.Request(_build_metrics_url(base_url), method="GET")
    request.add_header(token_header, token_value)

    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Metrics request failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Metrics request failed: {exc.reason}") from exc

    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise RuntimeError("Metrics response is not a JSON object")
    return payload


def _extract_transport_counters(payload: dict[str, object]) -> dict[str, int]:
    raw = payload.get("operation_intent_transport_requests_total", {})
    if not isinstance(raw, dict):
        return {}

    counters: dict[str, int] = {}
    for key, value in raw.items():
        mode = str(key)
        try:
            counters[mode] = int(value)
        except (TypeError, ValueError):
            counters[mode] = 0
    return counters


def _build_summary(
    first: dict[str, int],
    last: dict[str, int],
    elapsed_seconds: float,
) -> dict[str, dict[str, float | int]]:
    modes = sorted(set(first.keys()) | set(last.keys()))
    summary: dict[str, dict[str, float | int]] = {}
    for mode in modes:
        first_count = first.get(mode, 0)
        last_count = last.get(mode, 0)
        delta = last_count - first_count
        rate_per_minute = (delta / elapsed_seconds * 60.0) if elapsed_seconds > 0 else 0.0
        summary[mode] = {
            "first": first_count,
            "last": last_count,
            "delta": delta,
            "rate_per_minute": round(rate_per_minute, 4),
        }
    return summary


def _build_query_share(summary: dict[str, dict[str, float | int]]) -> dict[str, float | int]:
    query_delta = int(summary.get("query", {}).get("delta", 0))
    header_delta = int(summary.get("header", {}).get("delta", 0))
    dual_match_delta = int(summary.get("dual_match", {}).get("delta", 0))
    total_delta = query_delta + header_delta + dual_match_delta
    share_ratio = (query_delta / total_delta) if total_delta > 0 else 0.0

    return {
        "query_delta": query_delta,
        "header_delta": header_delta,
        "dual_match_delta": dual_match_delta,
        "total_transport_delta": total_delta,
        "query_share_ratio": round(share_ratio, 6),
        "query_share_percent": round(share_ratio * 100.0, 4),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture operation-intent transport mode counters from maintenance metrics "
            "and optionally compute a short trend summary."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("GMN_API_BASE_URL", "http://127.0.0.1:8000"),
        help="API base URL (default: env GMN_API_BASE_URL or http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--token-header",
        default=os.getenv("MAINTENANCE_AUTH_HEADER", "X-Maintenance-Token"),
        help="Maintenance auth header name",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("MAINTENANCE_AUTH_TOKEN", ""),
        help="Maintenance auth token (default: MAINTENANCE_AUTH_TOKEN)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=1,
        help="Number of samples to collect (default: 1)",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=60.0,
        help="Seconds between samples when --samples > 1 (default: 60)",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional path to write JSON output",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.samples < 1:
        print("--samples must be >= 1", file=sys.stderr)
        return 2
    if args.interval_seconds < 0:
        print("--interval-seconds must be >= 0", file=sys.stderr)
        return 2

    snapshots: list[dict[str, object]] = []
    started_at = datetime.now(UTC)
    monotonic_start = time.monotonic()

    for index in range(args.samples):
        payload = _fetch_metrics(args.base_url, args.token_header, args.token)
        counters = _extract_transport_counters(payload)
        snapshots.append(
            {
                "sample_index": index,
                "captured_at": datetime.now(UTC).isoformat(),
                "operation_intent_session_header_name": payload.get("operation_intent_session_header_name"),
                "counters": counters,
            }
        )
        if index < args.samples - 1:
            time.sleep(args.interval_seconds)

    elapsed_seconds = time.monotonic() - monotonic_start
    first_counters = snapshots[0].get("counters", {})
    last_counters = snapshots[-1].get("counters", {})

    summary = _build_summary(
        first=first_counters if isinstance(first_counters, dict) else {},
        last=last_counters if isinstance(last_counters, dict) else {},
        elapsed_seconds=elapsed_seconds,
    )
    query_share = _build_query_share(summary)

    result = {
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "base_url": args.base_url,
        "token_header": args.token_header,
        "samples": args.samples,
        "interval_seconds": args.interval_seconds,
        "snapshots": snapshots,
        "summary": summary,
        "query_share_from_deltas": query_share,
    }

    output_text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output_text + "\n")

    print(output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())