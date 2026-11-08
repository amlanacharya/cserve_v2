# Prompt library

Versioned copies of the prompts used at runtime. The source of truth is
`src/generation/prompts.py`; these files are exported snapshots (v1) so prompt
changes are reviewable in diffs. The Stage 3 workbook in `03_Workbooks/` holds the
design rationale for each prompt.

- `classification_system_prompt_v1.txt` - intent/urgency/confidence extraction
- `generation_system_prompt_v1.txt` - citation-grounded answer synthesis (XML-sandboxed ticket body)
