"""
tokens.py — Billing-optimized token extraction helpers.

Goal:
  - Provide stable, predictable (input, output, total) token counts for COST ESTIMATION.
  - Cope with OpenAI usage schema variants across SDKs/APIs:
    - modern:  input_tokens / output_tokens / total_tokens
    - legacy:  prompt_tokens / completion_tokens / total_tokens

Policy:
  - Default policy="billing":
      input  := input_tokens  if present else prompt_tokens
      output := completion_tokens if present else output_tokens
    Rationale: completion_tokens is closest to "generated text" for many models,
    while input_tokens covers billing for modern APIs; prompt_tokens is used as fallback.

  - policy="auto":
      Prefer modern keys (input/output). If missing, fall back to legacy (prompt/completion).
      This matches your earlier implementation and is useful for diagnostics.

  - policy="prefer_completion":
      input  := prompt_tokens  if present else input_tokens
      output := completion_tokens if present else output_tokens

  - policy="prefer_output":
      input  := input_tokens  if present else prompt_tokens
      output := output_tokens if present else completion_tokens

Notes:
  - We NEVER invent tokens. If total_tokens is absent, we compute total := input + output.
  - If usage is missing or malformed, we safely return zeros.
"""

from __future__ import annotations
from typing import Any, NamedTuple, Literal, Dict


class Tokens(NamedTuple):
    input: int
    output: int
    total: int


def _get_attr(obj: Any, name: str):
    try:
        return getattr(obj, name)
    except Exception:
        return None


def _coerce_int(x: Any) -> int:
    try:
        return int(x)
    except Exception:
        return 0


def _read_usage_fields(usage_obj: Any) -> Dict[str, Any]:
    """
    Read both modern and legacy token fields from a usage object (dict or obj).
    Returns a dict with possibly-None fields:
      input_tokens, output_tokens, prompt_tokens, completion_tokens, total_tokens
    """
    if usage_obj is None:
        return {
            "input_tokens": None,
            "output_tokens": None,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }

    # Try attributes (Pydantic/object) first
    input_tok  = _get_attr(usage_obj, "input_tokens")
    output_tok = _get_attr(usage_obj, "output_tokens")
    prompt_tok = _get_attr(usage_obj, "prompt_tokens")
    compl_tok  = _get_attr(usage_obj, "completion_tokens")
    total_tok  = _get_attr(usage_obj, "total_tokens")

    # If dict, fill missing via .get
    if isinstance(usage_obj, dict):
        if input_tok  is None: input_tok  = usage_obj.get("input_tokens")
        if output_tok is None: output_tok = usage_obj.get("output_tokens")
        if prompt_tok is None: prompt_tok = usage_obj.get("prompt_tokens")
        if compl_tok  is None: compl_tok  = usage_obj.get("completion_tokens")
        if total_tok  is None: total_tok  = usage_obj.get("total_tokens")

    return {
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "prompt_tokens": prompt_tok,
        "completion_tokens": compl_tok,
        "total_tokens": total_tok,
    }


def extract_tokens(usage_obj: Any,
                   policy: Literal["billing","auto","prefer_completion","prefer_output"]="billing"
                  ) -> Tokens:
    """
    Extract (input, output, total) token counts from a usage object for COST ESTIMATION.

    Args:
      usage_obj: dict or object that may carry token fields.
      policy: selection rule described in the module docstring.

    Returns:
      Tokens(input, output, total)
    """
    fields = _read_usage_fields(usage_obj)
    in_m  = fields["input_tokens"]
    out_m = fields["output_tokens"]
    in_l  = fields["prompt_tokens"]
    out_l = fields["completion_tokens"]
    tot   = fields["total_tokens"]

    # Decide input/output by policy
    if policy == "prefer_completion":
        ptok = in_l if in_l is not None else in_m
        ctok = out_l if out_l is not None else out_m
    elif policy == "prefer_output":
        ptok = in_m if in_m is not None else in_l
        ctok = out_m if out_m is not None else out_l
    elif policy == "auto":
        # Prefer modern; fall back to legacy
        ptok = in_m if in_m is not None else in_l
        ctok = out_m if out_m is not None else out_l
    else:  # "billing" (default)
        # Input: modern then legacy; Output: legacy (completion) then modern
        ptok = in_m if in_m is not None else in_l
        ctok = out_l if out_l is not None else out_m

    # Coerce to ints and compute total if missing
    ptok_i = _coerce_int(ptok)
    ctok_i = _coerce_int(ctok)
    total_i = _coerce_int(tot) if tot is not None else (ptok_i + ctok_i)

    return Tokens(ptok_i, ctok_i, total_i)


# Backward-compatible alias
_extract_tokens = extract_tokens


def extract_tokens_from_response(resp: Any,
                                 policy: Literal["billing","auto","prefer_completion","prefer_output"]="billing"
                                ) -> Tokens:
    """
    Convenience: read resp.usage and apply the same policy.
    """
    if resp is None:
        return Tokens(0, 0, 0)

    usage = None
    try:
        usage = getattr(resp, "usage")
    except Exception:
        usage = None

    if usage is None and isinstance(resp, dict):
        usage = resp.get("usage")

    return extract_tokens(usage, policy=policy)


def debug_usage_snapshot(usage_obj: Any) -> Dict[str, int]:
    """
    Return a normalized snapshot of usage fields (ints with zeros for missing)
    to help debug discrepancies.
    """
    f = _read_usage_fields(usage_obj)
    return {
        "input_tokens":      _coerce_int(f["input_tokens"]),
        "output_tokens":     _coerce_int(f["output_tokens"]),
        "prompt_tokens":     _coerce_int(f["prompt_tokens"]),
        "completion_tokens": _coerce_int(f["completion_tokens"]),
        "total_tokens":      _coerce_int(f["total_tokens"]),
    }
