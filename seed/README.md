# Seed data reference

This directory is a human-readable reference for the demo dataset. The
dataset is actually generated and loaded by `backend/app/seed/` (run via
`python -m app.seed`); the files here are exports and examples for anyone
who wants to read the regulation text or a scenario without running the
application.

> Synthetic demonstration regulation. Not legal advice.

## regulations/

The rendered source text for both versions of the demo regulation,
**Consumer Lending Fairness Regulation**, exactly as it is compiled by the
mock LLM provider. Each provision is realistic regulatory prose annotated
with `<<TAG: value>>` markers -- see
`backend/app/compiler/regulation_parser.py` for how these are read. A real
LLM provider (e.g. the Bedrock provider) ignores the tags entirely and
extracts structure from the prose.

Two deliberate changes exist between v1.0 and v2.0:

- **RULE-017** (Consumer Loan APR Threshold): 18% -> 16%.
- **RULE-005** (Income Verification Requirement): the covered-borrower
  income floor drops from $50,000 to $40,000.

Plus a removed rule (RULE-015, an expired forbearance provision, formally
repealed), an added rule (RULE-016, a new enhanced-disclosure
requirement), and a tightened exception on RULE-013.

## scenarios/

Individual example records with their expected verdict under each
version, useful for manually exercising the What-if Simulator or the
`POST /api/evaluate/simulate` endpoint.

## Regenerating

```bash
cd backend
python -c "
from app.seed.content import build_v1_content, build_v2_content, render_source_text
d1, r1, e1 = build_v1_content()
print(render_source_text(d1, r1, e1))
"
```
