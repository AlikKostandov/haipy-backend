from typing import List

from ..core.parsing import NotebookCell


def build_llm_context(cells: List[NotebookCell], max_cells: int = 60, max_chars: int = 12000) -> str:
    chosen = cells[:max_cells]

    parts: List[str] = []
    for c in chosen:
        header = f"[cell {c.index}] type={c.cell_type}"
        body = c.source or ""

        outputs_text = getattr(c, "outputs_text", None)

        if outputs_text is None and getattr(c, "outputs", None):
            outputs_text = "\n".join(o.text for o in c.outputs if getattr(o, "text", None))

        if c.cell_type == "code" and outputs_text:
            body += f"\n\n[output]\n{outputs_text}"

        parts.append(header + "\n" + body)

    text = "\n\n---\n\n".join(parts)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[truncated]"
    return text
