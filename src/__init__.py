"""CloudServe Support Orchestrator package."""

# Global compatibility shim for Pydantic v2 / ChromaDB 0.3.21
import pydantic
import pydantic.v1

setattr(pydantic, "BaseSettings", pydantic.v1.BaseSettings)
