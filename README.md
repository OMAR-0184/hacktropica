# hacktropica
Repository for hacktropica

## Architecture Overview

### Guardrails
Cognimap incorporates specific LLM quality guardrails to ensure robust output from the nodes:
- `agent/guardrails/tutor_quality.py`: Contains content validation heuristics (`check_tutor_quality`) that evaluate LLM tutor outputs for word count and repetitive phrases.
- `agent/guardrails/quiz_quality.py`: Contains validation heuristics (`check_quiz_quality`) that ensure quiz questions have appropriate length, no duplicate options, and varied correct answer positions.
- `agent/guardrails/latex_syntax.py`: A structural LaTeX validator that verifies syntax (e.g., balanced braces, environment matching, Flutter-compatible packages) without needing a full TeX compiler. If LaTeX compilation is invalid, the LLM receives specific syntax errors to fix.
