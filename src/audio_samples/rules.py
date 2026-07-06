from typing import Optional, List, Tuple
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, field_validator

class ChunksRule(BaseModel):
    chunk_size_seconds: int = Field(..., description="Size of each chunk in seconds")
    amount: int = Field(-1, description="Amount of chunks to sample. -1 means slice all audio.")
    remove_seconds: Optional[List[Tuple[int, int]]] = Field(None, description="Time ranges to remove from sampling.")

    @field_validator("chunk_size_seconds")
    @classmethod
    def validate_chunk_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("chunk_size_seconds must be strictly positive")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v == 0:
            raise ValueError("amount cannot be 0")
        if v < -1:
            raise ValueError("amount must be -1 or positive")
        return v

    @field_validator("remove_seconds")
    @classmethod
    def validate_remove_seconds(cls, v: Optional[List[Tuple[int, int]]]) -> Optional[List[Tuple[int, int]]]:
        if v is None:
            return v
        for item in v:
            if len(item) != 2:
                raise ValueError("Each interval in remove_seconds must have exactly 2 elements (start, end)")
            start, end = item
            if start < 0 or end < 0:
                raise ValueError("Interval times in remove_seconds must be non-negative")
            if start >= end:
                raise ValueError("Interval start must be strictly less than end in remove_seconds")
        return v


class RulesConfig(BaseModel):
    version: int = Field(..., description="Configuration file version")
    chunks: List[ChunksRule] = Field(..., description="List of slicing rules")
    remove_seconds: Optional[List[Tuple[int, int]]] = Field(None, description="Global time ranges to remove from sampling.")

    @field_validator("remove_seconds")
    @classmethod
    def validate_remove_seconds(cls, v: Optional[List[Tuple[int, int]]]) -> Optional[List[Tuple[int, int]]]:
        if v is None:
            return v
        for item in v:
            if len(item) != 2:
                raise ValueError("Each interval in remove_seconds must have exactly 2 elements (start, end)")
            start, end = item
            if start < 0 or end < 0:
                raise ValueError("Interval times in remove_seconds must be non-negative")
            if start >= end:
                raise ValueError("Interval start must be strictly less than end in remove_seconds")
        return v



def load_rules_from_yaml(file_path: Path) -> RulesConfig:
    """Load and validate rules configuration from a YAML file."""
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)
    return RulesConfig.model_validate(data)
