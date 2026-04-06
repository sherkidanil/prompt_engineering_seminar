from __future__ import annotations

from pydantic import BaseModel, Field


class BlockField(BaseModel):
    name: str
    value: str
    editable: bool


class Block(BaseModel):
    id: str
    title: str
    kind: str
    notebook_path: str = ""
    notebook_cell_indexes: list[int] = Field(default_factory=list)
    instructions_markdown: str
    editable_fields: list[BlockField] = Field(default_factory=list)
    readonly_fields: list[BlockField] = Field(default_factory=list)
    hint: str | None = None
    solution: str | None = None


class Part(BaseModel):
    id: str
    title: str
    blocks: list[Block] = Field(default_factory=list)


class SeminarManifest(BaseModel):
    title: str
    notebook_path: str
    hints_path: str
    parts: list[Part] = Field(default_factory=list)

    def block(self, block_id: str) -> Block:
        for part in self.parts:
            for block in part.blocks:
                if block.id == block_id:
                    return block
        raise KeyError(f"Unknown block id: {block_id}")


class GradeResult(BaseModel):
    passed: bool
    details: str | None = None


class ExecutionResult(BaseModel):
    prompt_preview: str | None = None
    system_prompt: str | None = None
    prefill: str | None = None
    response: str = ""
    stdout: str = ""
    grade: GradeResult | None = None
    tool_trace: dict | None = None
