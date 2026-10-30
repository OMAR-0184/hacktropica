"""
Micro-benchmark for the LaTeX structural validator.

Measures validation latency on realistic LLM-generated LaTeX documents.
Gives you a real number for the resume bullet about <5ms validation.

Usage:
    python -m scripts.benchmark_latex
"""

from __future__ import annotations

import statistics
import time

from agent.guardrails.latex_syntax import validate_latex

# ── Realistic test documents ──────────────────────────────────

VALID_DOC = r"""
\documentclass{article}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{tikz}

\begin{document}

\section{Vectors and Linear Transformations}

A vector $\mathbf{v} \in \mathbb{R}^n$ can be written as:
$$
\mathbf{v} = \begin{pmatrix} v_1 \\ v_2 \\ \vdots \\ v_n \end{pmatrix}
$$

The dot product of two vectors $\mathbf{u}$ and $\mathbf{v}$ is defined as:
\[
\mathbf{u} \cdot \mathbf{v} = \sum_{i=1}^{n} u_i v_i
\]

A linear transformation $T: \mathbb{R}^n \to \mathbb{R}^m$ satisfies:
\begin{align}
T(\mathbf{u} + \mathbf{v}) &= T(\mathbf{u}) + T(\mathbf{v}) \\
T(c\mathbf{u}) &= cT(\mathbf{u})
\end{align}

\subsection{Matrix Representation}

Every linear transformation can be represented as a matrix multiplication:
$$
T(\mathbf{v}) = A\mathbf{v} = \begin{pmatrix}
a_{11} & a_{12} & \cdots & a_{1n} \\
a_{21} & a_{22} & \cdots & a_{2n} \\
\vdots & \vdots & \ddots & \vdots \\
a_{m1} & a_{m2} & \cdots & a_{mn}
\end{pmatrix}
\begin{pmatrix} v_1 \\ v_2 \\ \vdots \\ v_n \end{pmatrix}
$$

\begin{enumerate}
    \item The determinant: $\det(A) = \sum_{\sigma \in S_n} \text{sgn}(\sigma) \prod_{i=1}^{n} a_{i,\sigma(i)}$
    \item Eigenvalues satisfy: $\det(A - \lambda I) = 0$
    \item For symmetric matrices: $A = Q\Lambda Q^T$
\end{enumerate}

The Cauchy-Schwarz inequality states:
\[
|\mathbf{u} \cdot \mathbf{v}| \leq \|\mathbf{u}\| \cdot \|\mathbf{v}\|
\]

\end{document}
"""

INVALID_DOC = r"""
\documentclass{article}
\usepackage{amsmath}

\begin{document}

The quadratic formula is $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a$.

Missing closing brace above. Also an unmatched environment:

\begin{align}
f(x) &= x^2 + 2x + 1 \\
g(x) &= (x + 1)^2
\end{equation}

And an odd number of dollar signs: $E = mc^2$$ is wrong.

\end{document}
"""

SMALL_DOC = r"""
\documentclass{article}
\begin{document}
The equation $E = mc^2$ is famous.
\end{document}
"""


def run_benchmark(iterations: int = 10_000) -> None:
    docs = [
        ("valid_large", VALID_DOC),
        ("invalid_large", INVALID_DOC),
        ("valid_small", SMALL_DOC),
    ]

    print(f"\n  LaTeX Validator Benchmark ({iterations:,} iterations each)")
    print("=" * 60)

    for name, doc in docs:
        # Warmup
        for _ in range(100):
            validate_latex(doc)

        # Measure
        times_us: list[float] = []
        t_total_start = time.perf_counter()
        for _ in range(iterations):
            t0 = time.perf_counter()
            validate_latex(doc)
            times_us.append((time.perf_counter() - t0) * 1_000_000)
        total_s = time.perf_counter() - t_total_start

        mean_us = statistics.mean(times_us)
        median_us = statistics.median(times_us)
        p99_us = sorted(times_us)[int(len(times_us) * 0.99)]
        max_us = max(times_us)

        result = validate_latex(doc)
        status = "✓ valid" if result.valid else f"✗ {len(result.errors)} errors"

        print(f"\n  {name} ({len(doc)} chars, {status})")
        print(f"    Mean:   {mean_us:>8.1f} µs  ({mean_us/1000:.3f} ms)")
        print(f"    Median: {median_us:>8.1f} µs  ({median_us/1000:.3f} ms)")
        print(f"    p99:    {p99_us:>8.1f} µs  ({p99_us/1000:.3f} ms)")
        print(f"    Max:    {max_us:>8.1f} µs  ({max_us/1000:.3f} ms)")
        print(f"    Throughput: {iterations/total_s:,.0f} validations/sec")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_benchmark()
