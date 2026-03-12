from typing import Dict, Any, List, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class GeneratorSpec(BaseModel):
    """
    Especificação estrita e enrijecida de um gerador N1.
    Substitui a estrutura fraca da dataclass.
    """
    model_config = ConfigDict(frozen=True, strict=True)

    generator_id: str = Field(..., pattern=r"^[A-Z_]+_[a-f0-9\-]+$")
    description: str = Field(..., min_length=10, max_length=200)
    generator_type: Literal["template", "transformer", "composer", "validator"]
    inputs: Dict[str, Any]
    constraints: List[str] = Field(min_length=1)
    preconditions: List[str] = Field(min_length=1)
    postconditions: List[str] = Field(min_length=1)
    invariants: List[str] = Field(min_length=1)

    @model_validator(mode='after')
    def check_business_constraints(self) -> 'GeneratorSpec':
        if self.generator_type == "transformer" and "target_node" not in self.inputs:
            raise ValueError("Transformers must specify a 'target_node' in inputs")
            
        return self

class TriadOutput(BaseModel):
    """Output validado do motor N1."""
    model_config = ConfigDict(frozen=True)

    execute_script: str = Field(..., min_length=50)
    validate_script: str = Field(..., min_length=50)
    rollback_script: str = Field(..., min_length=50)
    execution_hash: str = Field(..., pattern=r"^[a-f0-9]{64}$")
