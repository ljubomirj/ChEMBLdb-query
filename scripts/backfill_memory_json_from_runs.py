#!/usr/bin/env python3
"""Backfill MEMORY-ChEMBLdb-query.json from existing run logs + result CSVs."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Optional


TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} ")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_uq(log_text: str) -> Optional[str]:
    lines = log_text.splitlines()
    start: Optional[int] = None
    for i, line in enumerate(lines):
        if line.strip() == "<UQ>":
            start = i + 1
            break
    if start is None:
        return None
    out: list[str] = []
    for line in lines[start:]:
        if line.strip() == "</UQ>":
            break
        out.append(line)
    uq = "\n".join(out).strip()
    return uq or None


def _extract_accept_iteration(log_text: str) -> Optional[int]:
    best: Optional[int] = None
    for line in log_text.splitlines():
        if "Stopping: judge_decision=True" not in line:
            continue
        m = re.search(r"ITER_(\d+)", line)
        if not m:
            continue
        best = int(m.group(1))
    if best is None:
        return None
    return best


def _collect_raw_after_header(lines: list[str], header_idx: int) -> str:
    out: list[str] = []
    started = False
    for line in lines[header_idx + 1 :]:
        if TS_RE.match(line):
            if started:
                break
            continue
        if not started and not line.strip():
            continue
        started = True
        out.append(line.rstrip())
    return "\n".join(out).strip()


def _extract_up(log_text: str, iteration: int) -> Optional[str]:
    lines = log_text.splitlines()
    marker = f"UP_{iteration}:"
    header_idx: Optional[int] = None
    for i, line in enumerate(lines):
        if marker in line:
            header_idx = i
    if header_idx is None:
        return None
    out = _collect_raw_after_header(lines, header_idx)
    return out or None


def _extract_generated_sql_label_order(log_text: str, iteration: int) -> dict[str, int]:
    order: dict[str, int] = {}
    idx = 0
    marker = f"Generated SQL_{iteration} ("
    for line in log_text.splitlines():
        if marker not in line:
            continue
        m = re.search(rf"Generated SQL_{iteration} \((.+?)\):", line)
        if not m:
            continue
        label = m.group(1).strip()
        if label in order:
            continue
        idx += 1
        order[label] = idx
    return order


def _extract_res_row_counts_by_label(log_text: str, iteration: int) -> dict[str, int]:
    out: dict[str, int] = {}
    pat = re.compile(rf"RES_{iteration}(?:_\d+)? .*?\((.+?)\) \[(\d+) rows x")
    for line in log_text.splitlines():
        m = pat.search(line)
        if not m:
            continue
        out[m.group(1).strip()] = int(m.group(2))
    return out


def _extract_winner(log_text: str, iteration: int, target_row_count: Optional[int] = None) -> dict[str, Any]:
    line_matches: list[str] = []
    marker = f"Winner (ITER_{iteration}):"
    for line in log_text.splitlines():
        if marker in line:
            line_matches.append(line)
    if line_matches:
        line = line_matches[-1]

        new_fmt = re.search(
            rf"Winner \(ITER_{iteration}\): SQL_{iteration}_(\d+) (.+?) judged by (.+?) \(J(\d+)\) decision=(True|False) score=([0-9.]+)",
            line,
        )
        if new_fmt:
            return {
                "raw_line": line,
                "sql_index": int(new_fmt.group(1)),
                "sql_label": new_fmt.group(2).strip(),
                "judge_label": new_fmt.group(3).strip(),
                "judge_idx": int(new_fmt.group(4)),
                "decision": new_fmt.group(5) == "True",
                "score": float(new_fmt.group(6)),
            }

        old_fmt = re.search(
            rf"Winner \(ITER_{iteration}\): C(\d+) (.+?) judged by (.+?) \(J(\d+)\) decision=(True|False) score=([0-9.]+)",
            line,
        )
        if old_fmt:
            # In older logs, C1/C2/C3 maps to SQL_{iteration}_1/_2/_3.
            return {
                "raw_line": line,
                "sql_index": int(old_fmt.group(1)),
                "sql_label": old_fmt.group(2).strip(),
                "judge_label": old_fmt.group(3).strip(),
                "judge_idx": int(old_fmt.group(4)),
                "decision": old_fmt.group(5) == "True",
                "score": float(old_fmt.group(6)),
            }

    # Fallback for older logs that only print candidate verdict lines.
    cand_pat = re.compile(
        rf"Candidate (.+?) judged by (.+?): decision=(True|False) score=([0-9.]+)"
    )
    candidates: list[dict[str, Any]] = []
    for ln in log_text.splitlines():
        if f"ITER_{iteration}" not in ln or "Candidate " not in ln:
            continue
        m = cand_pat.search(ln)
        if not m:
            continue
        candidates.append(
            {
                "raw_line": ln,
                "sql_label": m.group(1).strip(),
                "judge_label": m.group(2).strip(),
                "decision": m.group(3) == "True",
                "score": float(m.group(4)),
            }
        )
    if not candidates:
        raise ValueError(f"Unrecognized winner line format: {line}")

    sql_order = _extract_generated_sql_label_order(log_text, iteration)
    res_rows = _extract_res_row_counts_by_label(log_text, iteration)

    picked: Optional[dict[str, Any]] = None
    # Prefer YES candidates that match the saved CSV row count.
    yes = [c for c in candidates if c["decision"]]
    if target_row_count is not None and yes:
        matched = [
            c for c in yes if res_rows.get(str(c["sql_label"])) == int(target_row_count)
        ]
        if matched:
            picked = max(matched, key=lambda c: float(c["score"]))
    if picked is None and yes:
        picked = max(yes, key=lambda c: float(c["score"]))
    if picked is None:
        picked = max(candidates, key=lambda c: float(c["score"]))

    picked = dict(picked)
    picked["sql_index"] = int(sql_order.get(str(picked["sql_label"]), 1))
    picked["judge_idx"] = 1
    return picked


def _extract_sql_text(log_text: str, iteration: int, sql_index: int, sql_label: str) -> Optional[str]:
    lines = log_text.splitlines()
    marker1 = f"SQL_{iteration}_{sql_index} text:"
    for i, line in enumerate(lines):
        if marker1 in line:
            block = _collect_raw_after_header(lines, i)
            if block:
                return block

    marker2 = f"Generated SQL_{iteration} ({sql_label}):"
    for i, line in enumerate(lines):
        if marker2 in line:
            block = _collect_raw_after_header(lines, i)
            if block:
                return block
    return None


def _extract_json_object(text: str) -> Optional[dict[str, Any]]:
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        start = m.start()
        try:
            obj, _ = decoder.raw_decode(text, idx=start)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _extract_judge(log_text: str, iteration: int) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    lines = log_text.splitlines()
    marker = f"J_{iteration}:"
    header_idx: Optional[int] = None
    for i, line in enumerate(lines):
        if marker in line:
            header_idx = i
    if header_idx is None:
        return None, None
    raw = _collect_raw_after_header(lines, header_idx)
    if not raw:
        return None, None
    parsed = _extract_json_object(raw)
    return parsed, raw


def _extract_res_summary(
    log_text: str,
    iteration: int,
    sql_index: int,
    sql_label: str,
) -> Optional[str]:
    lines = log_text.splitlines()
    candidates = [
        f"RES_{iteration}_{sql_index} ({sql_label}):",
        f"RES_{iteration} ({sql_label}):",
    ]
    start_idx: Optional[int] = None
    for idx, line in enumerate(lines):
        if any(marker in line for marker in candidates):
            start_idx = idx
            break
    if start_idx is None:
        return None

    out: list[str] = []
    started = False
    for line in lines[start_idx + 1 :]:
        if TS_RE.match(line):
            if started:
                break
            continue
        stripped = line.rstrip()
        if not stripped and not started:
            continue
        started = True
        out.append(stripped)
    res = "\n".join(out).strip()
    return res or None


def _extract_system_prompt_sha(log_text: str) -> Optional[str]:
    for line in log_text.splitlines():
        m = re.search(r"SYSTEM_SHA256:\s*([a-fA-F0-9]{64})", line)
        if m:
            return m.group(1).lower()
    return None


def _csv_stats(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        rows = list(reader)
    if not rows:
        return {"row_count": 0, "n_cols": 0, "columns": [], "head": None, "middle": None, "tail": None}
    header = rows[0]
    data = rows[1:]
    n = len(data)
    head = data[0] if n else None
    mid = data[n // 2] if n else None
    tail = data[-1] if n else None
    return {
        "row_count": n,
        "n_cols": len(header),
        "columns": header,
        "head": head,
        "middle": mid,
        "tail": tail,
    }


def _extract_run_entry(log_path: Path, csv_path: Path) -> dict[str, Any]:
    log_text = _read_text(log_path)
    csv_meta = _csv_stats(csv_path)

    uq = _extract_uq(log_text)
    if not uq:
        raise ValueError(f"Could not extract UQ from {log_path}")

    iter_n = _extract_accept_iteration(log_text)
    if iter_n is None:
        raise ValueError(f"Could not find accepted iteration in {log_path}")

    up = _extract_up(log_text, iter_n)
    if not up:
        raise ValueError(f"Could not extract UP_{iter_n} from {log_path}")

    winner = _extract_winner(log_text, iter_n, target_row_count=csv_meta["row_count"])
    sql_text = _extract_sql_text(log_text, iter_n, winner["sql_index"], winner["sql_label"])
    if not sql_text:
        raise ValueError(
            f"Could not extract SQL text for ITER_{iter_n} SQL index {winner['sql_index']} in {log_path}"
        )

    j_obj, j_raw = _extract_judge(log_text, iter_n)
    if not j_raw:
        raise ValueError(f"Could not extract J_{iter_n} from {log_path}")

    res_summary = _extract_res_summary(log_text, iter_n, winner["sql_index"], winner["sql_label"])
    if not res_summary:
        raise ValueError(
            f"Could not extract RES summary for ITER_{iter_n} SQL index {winner['sql_index']} label {winner['sql_label']}"
        )

    run_label = csv_path.stem.replace("query_results_", "", 1)

    return {
        "ts_utc_backfill": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_label": run_label,
        "accepted": True,
        "iteration": iter_n,
        "UQ": uq,
        "UP": up,
        "SQL": sql_text,
        "RES": res_summary,
        "J": j_obj if j_obj is not None else {"raw": j_raw},
        "J_raw": j_raw,
        "row_count": csv_meta["row_count"],
        "n_cols": csv_meta["n_cols"],
        "columns": csv_meta["columns"],
        "csv_samples": {
            "head": csv_meta["head"],
            "middle": csv_meta["middle"],
            "tail": csv_meta["tail"],
        },
        "sql_label": winner["sql_label"],
        "judge_label": winner["judge_label"],
        "sql_stage": f"SQL_{iter_n}_{winner['sql_index']}",
        "judge_stage": f"J_{iter_n}_{winner['judge_idx']}_SQL_{iter_n}_{winner['sql_index']}",
        "winner_decision": winner["decision"],
        "winner_score": winner["score"],
        "winner_line": winner["raw_line"],
        "system_prompt_sha256": _extract_system_prompt_sha(log_text),
        "source_log_path": str(log_path),
        "source_csv_path": str(csv_path),
    }


def _load_existing(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "entries": []}
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return {"schema_version": 1, "entries": []}
    obj = json.loads(text)
    if isinstance(obj, dict) and isinstance(obj.get("entries"), list):
        return obj
    if isinstance(obj, list):
        return {"schema_version": 1, "entries": obj}
    raise ValueError(f"Unsupported JSON structure in {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill MEMORY-ChEMBLdb-query.json from selected timestamps")
    parser.add_argument(
        "--timestamps",
        nargs="+",
        required=True,
        help="Run timestamps like 20260207_203639",
    )
    parser.add_argument(
        "--output",
        default="MEMORY-ChEMBLdb-query.json",
        help="Output JSON file path (default: MEMORY-ChEMBLdb-query.json)",
    )
    args = parser.parse_args()

    out_path = Path(args.output)
    payload = _load_existing(out_path)
    existing = payload.get("entries", [])

    existing_labels = {e.get("run_label") for e in existing if isinstance(e, dict)}
    new_entries: list[dict[str, Any]] = []

    for ts in args.timestamps:
        log_candidates = sorted(Path("logs").glob(f"*{ts}*.log"))
        csv_candidates = sorted(Path(".").glob(f"query_results_query1_kinase_after_2022_*{ts}.csv"))
        if not log_candidates:
            raise FileNotFoundError(f"No log file found for timestamp {ts}")
        if not csv_candidates:
            raise FileNotFoundError(f"No CSV file found for timestamp {ts}")
        log_path = log_candidates[0]
        csv_path = csv_candidates[0]
        entry = _extract_run_entry(log_path, csv_path)
        if entry["run_label"] in existing_labels:
            continue
        new_entries.append(entry)

    payload["schema_version"] = 1
    payload["generated_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    payload["entries"] = existing + new_entries
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(new_entries)} new entries to {out_path} (total={len(payload['entries'])})")


if __name__ == "__main__":
    main()
