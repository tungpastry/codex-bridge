from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import Field

from app.schemas.common import SchemaBase


AllowedHost = Literal["local", "UbuntuDesktop", "UbuntuServer"]


class GeminiCommandSpec(SchemaBase):
    host: AllowedHost
    command_id: str
    args: Dict[str, Any] = Field(default_factory=dict)
    reason: str


class GeminiJobOutputContract(SchemaBase):
    summary: str = "Short human-readable summary"
    confidence: str = "low|medium|high"
    needs_human: str = "true|false"
    why: str = "Why the plan is safe or why it needs escalation"
    commands: str = "Array of {host, command_id, args, reason}"
    final_markdown: str = "Operator-ready markdown summary"


class GeminiJob(SchemaBase):
    mode: Literal["ops_auto"] = "ops_auto"
    run_id: str = ""
    job_id: str
    title: str
    repo: str
    profile_name: str = ""
    problem_summary: str
    context_digest: str
    constraints: List[str] = Field(default_factory=list)
    allowed_hosts: List[AllowedHost] = Field(default_factory=list)
    allowed_command_ids: List[str] = Field(default_factory=list)
    output_contract: GeminiJobOutputContract = Field(default_factory=GeminiJobOutputContract)
    prompt: str = ""
