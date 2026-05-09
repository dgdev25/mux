from dataclasses import dataclass

@dataclass
class ModelResult:
    model: str
    output: str
    confidence: float

@dataclass
class VerifyResult:
    ok: bool
    summary: str
