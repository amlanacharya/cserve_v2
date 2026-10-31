# EGM Drift Report (2026-10-30)

## README.md

- **Missing Test Suite (`pytest`)**: The blueprint specifies `pytest` as the system verification runner, but no test directory (`tests/`) or test modules (`test_*.py` / `*_test.py`) exist in the repository yet.
- **Unimplemented Evaluation Harness**: The blueprint specifies dynamic CLI path ingestion for unattended batch evaluation, but the execution harness script is not yet authored.
- **Unimplemented Retrieval & RAG Pipeline**: The blueprint specifies grounded knowledge retrieval against `05_Datasets/documentation.json` using ChromaDB / PostgreSQL vector stores, but no embedding or retrieval code is implemented yet.
- **Unimplemented Environment Loader**: The invariant requires loading credentials from `.env` (templated by `06_Configuration/.env.example`), but no runtime configuration loader exists yet.

## 01_Read_First/README.md

- **Capstone Starting State**: The walkthrough document specifies working software deliverables across pipeline stages (retrieval layer, agent routing, safety guardrails, unattended validation runner), but the repository is currently in its initial course pack state with no functional source code files authored yet.

