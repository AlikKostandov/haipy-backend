from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class NotebookOutput:
    output_type: str
    text: str

@dataclass(frozen=True)
class NotebookCell:
    index: int
    cell_type: str
    source: str
    execution_count: Optional[int]
    outputs: Tuple[NotebookOutput, ...]
    metadata: Dict[str, Any]

class NotebookParseError(Exception):
    pass


# convert any source type -> string
def _source_to_string(source: Any) -> str:
    if source is None:
        return ""
    if isinstance(source, str):
        return source
    if isinstance(source, list):
        return "".join(str(x) for x in source)
    return str(source)

# optimize output length
def _truncate(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"


def _extract_output_text(out: Dict[str, Any], *, max_chars: int) -> Optional[str]:
    output_type = out.get("output_type") or ""
    output_parts: List[str] = []

    if output_type == "stream":
        output_parts.append(_source_to_string(out.get("text")))

    if output_type in ("execute_result", "display_data"):
        data = out.get("data")
        if isinstance(data, dict):
            if "text/plain" in data:
                output_parts.append(_source_to_string(data.get("text/plain")))
            elif "text/html" in data:
                output_parts.append(_source_to_string(data.get("text/html")))

    if output_type == "error":
        error_name = out.get("ename", "")
        error_value = out.get("evalue", "")
        traceback = out.get("traceback")
        if isinstance(traceback, list) and traceback:
            tail = "\n".join(traceback[-3:])
            output_parts.append(f"[error] {error_name}: {error_value}\n{tail}")
        else:
            output_parts.append(f"[error] {error_name}: {error_value}")

    text = "\n".join([t for t in (p.strip() for p in output_parts) if t])
    text = _truncate(text, max_chars)
    return text if text.strip() else None


def parse_notebook(
    ipynb_bytes: bytes,
    *,
    max_cells: Optional[int] = None,
    max_source_chars: int = 20_000,
    max_output_chars: int = 5_000,
    max_outputs_per_cell: int = 5,
) -> List[NotebookCell]:

    try:
        raw = json.loads(ipynb_bytes.decode("utf-8", errors="replace"))
    except Exception as e:
        raise NotebookParseError(f"Invalid JSON in .ipynb: {e}") from e

    if not isinstance(raw, dict) or "cells" not in raw:
        raise NotebookParseError("Not a valid .ipynb structure: missing 'cells'.")

    cells = raw.get("cells")
    if not isinstance(cells, list):
        raise NotebookParseError("Invalid .ipynb: 'cells' must be a list.")

    parsed: List[NotebookCell] = []
    limit = len(cells) if max_cells is None else min(len(cells), max_cells)

    for i in range(limit):
        c = cells[i]
        if not isinstance(c, dict):
            continue

        cell_type = str(c.get("cell_type", "unknown"))
        source = _truncate(_source_to_string(c.get("source")), max_source_chars).strip()
        execution_count = c.get("execution_count")
        if not isinstance(execution_count, int):
            execution_count = None

        outputs_raw = c.get("outputs") if cell_type == "code" else None
        outputs: List[NotebookOutput] = []

        if isinstance(outputs_raw, list):
            for out in outputs_raw[:max_outputs_per_cell]:
                if not isinstance(out, dict):
                    continue
                otype = str(out.get("output_type", "unknown"))
                text = _extract_output_text(out, max_chars=max_output_chars)
                if text:
                    outputs.append(NotebookOutput(output_type=otype, text=text))

        metadata = c.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        parsed.append(
            NotebookCell(
                index=i,
                cell_type=cell_type,
                source=source,
                execution_count=execution_count,
                outputs=tuple(outputs),
                metadata=metadata,
            )
        )

    return parsed
