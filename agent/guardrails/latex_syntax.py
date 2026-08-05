"""
Structural LaTeX validator — checks for common errors without invoking a compiler.

Used as a guardrail in the tutor node: if validation fails, the error messages
are fed back to the LLM so it can regenerate the LaTeX.  This avoids the
latency of a full TeX compilation while catching >90% of syntax issues.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Packages known to render correctly in Flutter (flutter_tex / MathJax / KaTeX).
# Anything outside this list may silently fail on the client.
FLUTTER_COMPATIBLE_PACKAGES: set[str] = {
    "amsmath",
    "amssymb",
    "amsfonts",
    "mathtools",
    "xcolor",
    "tikz",
    "pgfplots",
    "geometry",
    "graphicx",
    "hyperref",
    "enumitem",
    "booktabs",
    "tabularx",
    "array",
    "multicol",
    "fancyhdr",
    "tcolorbox",
    "float",
    "caption",
    "subcaption",
    "listings",
    "algorithm2e",
    "cancel",
    "bm",
    "siunitx",
    "chemfig",
    "mhchem",
    "circuitikz",
    "fontenc",
    "inputenc",
    "babel",
    "ulem",
    "soul",
}

# Common document classes accepted.
_VALID_DOCUMENTCLASSES = {
    "article",
    "report",
    "book",
    "standalone",
    "beamer",
    "minimal",
    "memoir",
    "scrartcl",
}

# Environments that are frequently used and must have matching \begin/\end.
_ENV_RE = re.compile(r"\\(begin|end)\{([^}]+)\}")

# \usepackage extraction.
_PACKAGE_RE = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}")

# Inline math delimiters.
_INLINE_MATH_RE = re.compile(r"(?<!\\)\$(?!\$)")
_DISPLAY_MATH_OPEN = re.compile(r"(?<!\\)\\\[")
_DISPLAY_MATH_CLOSE = re.compile(r"(?<!\\)\\\]")
_DOUBLE_DOLLAR_RE = re.compile(r"(?<!\\)\$\$")


@dataclass
class ValidationResult:
    """Result of a structural LaTeX validation pass."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def feedback_for_llm(self) -> str:
        """Format errors into a concise prompt addendum for the LLM retry."""
        if self.valid:
            return ""
        parts = ["The LaTeX source has the following structural errors:"]
        for i, err in enumerate(self.errors, 1):
            parts.append(f"  {i}. {err}")
        if self.warnings:
            parts.append("Warnings (non-blocking):")
            for w in self.warnings:
                parts.append(f"  - {w}")
        parts.append(
            "Fix ONLY these issues. Do not rewrite unrelated sections. "
            "Return the corrected full LaTeX source."
        )
        return "\n".join(parts)


def validate_latex(source: str) -> ValidationResult:
    """
    Run all structural checks on a LaTeX source string.

    Returns a ``ValidationResult`` with ``valid=True`` if no blocking errors
    were found, or ``valid=False`` with actionable error descriptions.
    """
    result = ValidationResult()
    if not source or not source.strip():
        result.valid = False
        result.errors.append("LaTeX source is empty.")
        return result

    _check_document_structure(source, result)
    _check_balanced_braces(source, result)
    _check_environment_matching(source, result)
    _check_math_delimiters(source, result)
    _check_packages(source, result)
    _check_common_pitfalls(source, result)

    if result.errors:
        result.valid = False
    return result


# ── Individual checks ─────────────────────────────────────────


def _check_document_structure(source: str, result: ValidationResult) -> None:
    """Verify required top-level LaTeX structure."""
    if "\\documentclass" not in source:
        result.errors.append(
            "Missing \\documentclass declaration. "
            "Start with \\documentclass{article} or similar."
        )
    else:
        dc_match = re.search(r"\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}", source)
        if dc_match:
            cls = dc_match.group(1).strip().lower()
            if cls not in _VALID_DOCUMENTCLASSES:
                result.warnings.append(
                    f"Unusual document class '{cls}'. "
                    f"Prefer one of: {', '.join(sorted(_VALID_DOCUMENTCLASSES))}."
                )

    if "\\begin{document}" not in source:
        result.errors.append("Missing \\begin{document}.")
    if "\\end{document}" not in source:
        result.errors.append("Missing \\end{document}.")

    # \begin{document} must come after \documentclass
    dc_pos = source.find("\\documentclass")
    bd_pos = source.find("\\begin{document}")
    if dc_pos >= 0 and bd_pos >= 0 and bd_pos < dc_pos:
        result.errors.append(
            "\\begin{document} appears before \\documentclass. "
            "Move the preamble (\\documentclass, \\usepackage, etc.) before \\begin{document}."
        )


def _check_balanced_braces(source: str, result: ValidationResult) -> None:
    """Check that curly braces are balanced, ignoring escaped braces."""
    depth = 0
    for i, ch in enumerate(source):
        if ch == "{" and (i == 0 or source[i - 1] != "\\"):
            depth += 1
        elif ch == "}" and (i == 0 or source[i - 1] != "\\"):
            depth -= 1
        if depth < 0:
            # Find approximate line number for the error.
            line_no = source[:i].count("\n") + 1
            result.errors.append(
                f"Unmatched closing brace '}}' near line {line_no}."
            )
            return
    if depth > 0:
        result.errors.append(
            f"Unmatched opening brace(s): {depth} opening '{{' without closing '}}'."
        )
    elif depth < 0:
        result.errors.append(
            f"Unmatched closing brace(s): {abs(depth)} extra '}}'."
        )


def _check_environment_matching(source: str, result: ValidationResult) -> None:
    """Ensure every \\begin{env} has a matching \\end{env} in the correct order."""
    stack: list[tuple[str, int]] = []
    for match in _ENV_RE.finditer(source):
        kind = match.group(1)  # "begin" or "end"
        env_name = match.group(2).strip()
        line_no = source[: match.start()].count("\n") + 1

        if kind == "begin":
            stack.append((env_name, line_no))
        else:  # "end"
            if not stack:
                result.errors.append(
                    f"\\end{{{env_name}}} at line {line_no} has no matching \\begin{{{env_name}}}."
                )
            else:
                top_env, top_line = stack.pop()
                if top_env != env_name:
                    result.errors.append(
                        f"Environment mismatch: \\begin{{{top_env}}} at line {top_line} "
                        f"is closed by \\end{{{env_name}}} at line {line_no}. "
                        f"Expected \\end{{{top_env}}}."
                    )

    for env_name, line_no in stack:
        result.errors.append(
            f"\\begin{{{env_name}}} at line {line_no} is never closed. "
            f"Add \\end{{{env_name}}}."
        )


def _check_math_delimiters(source: str, result: ValidationResult) -> None:
    """Check that inline ($) and display (\\[, $$) math delimiters are paired."""
    # Inline $...$  (ignore $$ which is display math)
    inline_count = len(_INLINE_MATH_RE.findall(source))
    # Subtract $$ occurrences (each $$ contributes 2 matches to inline count)
    double_count = len(_DOUBLE_DOLLAR_RE.findall(source))
    adjusted_inline = inline_count - (double_count * 2)
    if adjusted_inline % 2 != 0:
        result.errors.append(
            "Odd number of inline math delimiters ($). "
            "Each opening $ must have a closing $."
        )

    # Display math $$...$$
    if double_count % 2 != 0:
        result.errors.append(
            "Odd number of display math delimiters ($$). "
            "Each opening $$ must have a closing $$."
        )

    # \\[...\\]
    open_display = len(_DISPLAY_MATH_OPEN.findall(source))
    close_display = len(_DISPLAY_MATH_CLOSE.findall(source))
    if open_display != close_display:
        result.errors.append(
            f"Mismatched display math delimiters: {open_display} \\[ "
            f"but {close_display} \\]. Each \\[ must have a matching \\]."
        )


def _check_packages(source: str, result: ValidationResult) -> None:
    """Warn about packages that may not render on Flutter clients."""
    for match in _PACKAGE_RE.finditer(source):
        raw_packages = match.group(1)
        for pkg in raw_packages.split(","):
            pkg = pkg.strip().lower()
            if pkg and pkg not in FLUTTER_COMPATIBLE_PACKAGES:
                result.warnings.append(
                    f"Package '{pkg}' may not be supported by Flutter LaTeX renderers. "
                    f"Consider using a compatible alternative."
                )


def _check_common_pitfalls(source: str, result: ValidationResult) -> None:
    """Catch frequent LaTeX mistakes that cause compilation failures."""
    # Unescaped special characters outside math mode (simplified heuristic).
    # We only check for the most problematic ones.
    for char, name in [("&", "ampersand"), ("#", "hash"), ("%", "percent")]:
        # Find occurrences that are NOT escaped and NOT inside expected contexts.
        pattern = rf"(?<!\\){re.escape(char)}"
        matches = list(re.finditer(pattern, source))
        if char == "&":
            # & is valid inside tabular/align environments — don't flag those.
            pass  # Too many false positives; skip for now.
        elif char == "%":
            pass  # % starts comments — perfectly valid.
        elif char == "#":
            # # outside \newcommand definitions is usually an error.
            for m in matches:
                context_before = source[max(0, m.start() - 50) : m.start()]
                if "newcommand" not in context_before and "def\\" not in context_before:
                    line_no = source[: m.start()].count("\n") + 1
                    result.warnings.append(
                        f"Unescaped '#' at line {line_no}. "
                        f"Use \\# unless inside a \\newcommand definition."
                    )
                    break  # One warning is enough.

    # Empty \begin{...}\end{...} with nothing between them (common LLM mistake).
    empty_env = re.findall(
        r"\\begin\{(\w+)\}\s*\\end\{\1\}", source
    )
    for env in empty_env:
        if env not in {"document"}:
            result.warnings.append(
                f"Empty environment \\begin{{{env}}}...\\end{{{env}}}. "
                f"Either add content or remove the environment."
            )
