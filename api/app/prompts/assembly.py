from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.orchestration.context import (
    FrozenContextSnapshot,
    PromptEnvelope,
    build_instance_context,
)
from app.prompts.versions import PromptArtifactKind, PromptVersion, PromptVersionLoader


@dataclass(frozen=True, slots=True)
class PromptVersionSelection:
    identity_key: str
    identity_version: int
    methodology_key: str
    methodology_version: int
    phase_key: str
    phase_version: int
    output_schema_key: str
    output_schema_version: int
    tool_contract_key: str
    tool_contract_version: int


@dataclass(frozen=True, slots=True)
class PromptAssemblyInput:
    instance_id: str
    snapshot: FrozenContextSnapshot
    selection: PromptVersionSelection
    history_context: Mapping[str, Any] | str
    lesson_context: Sequence[Mapping[str, Any] | str]
    peer_context: Sequence[Mapping[str, Any]] = ()
    codename_map: Mapping[str, str] | None = None


@dataclass(slots=True)
class PromptAssembler:
    loader: PromptVersionLoader

    async def assemble(self, request: PromptAssemblyInput) -> PromptEnvelope:
        selection = request.selection
        identity = await self.loader.load(
            key=selection.identity_key,
            version=selection.identity_version,
            expected_kind=PromptArtifactKind.IDENTITY,
        )
        methodology = await self.loader.load(
            key=selection.methodology_key,
            version=selection.methodology_version,
            expected_kind=PromptArtifactKind.CORE_METHODOLOGY,
        )
        phase = await self.loader.load(
            key=selection.phase_key,
            version=selection.phase_version,
            expected_kind=PromptArtifactKind.PHASE_INSTRUCTION,
        )
        output_schema = await self.loader.load(
            key=selection.output_schema_key,
            version=selection.output_schema_version,
            expected_kind=PromptArtifactKind.OUTPUT_SCHEMA,
        )
        tool_contract = await self.loader.load(
            key=selection.tool_contract_key,
            version=selection.tool_contract_version,
            expected_kind=PromptArtifactKind.TOOL_CONTRACT,
        )
        return assemble_prompt_envelope(
            request=request,
            identity=identity,
            methodology=methodology,
            phase=phase,
            output_schema=output_schema,
            tool_contract=tool_contract,
        )


def assemble_prompt_envelope(
    *,
    request: PromptAssemblyInput,
    identity: PromptVersion,
    methodology: PromptVersion,
    phase: PromptVersion,
    output_schema: PromptVersion,
    tool_contract: PromptVersion,
) -> PromptEnvelope:
    """Build L1-L7 without converting untrusted data into instructions."""

    for artifact, expected in (
        (identity, PromptArtifactKind.IDENTITY),
        (methodology, PromptArtifactKind.CORE_METHODOLOGY),
        (phase, PromptArtifactKind.PHASE_INSTRUCTION),
        (output_schema, PromptArtifactKind.OUTPUT_SCHEMA),
        (tool_contract, PromptArtifactKind.TOOL_CONTRACT),
    ):
        if artifact.kind is not expected:
            raise ValueError(f"{artifact.key} has wrong artifact kind")
    if not all(isinstance(item.content, str) for item in (identity, methodology, phase)):
        raise TypeError("identity, methodology, and phase content must be text")
    if not isinstance(output_schema.content, Mapping):
        raise TypeError("output schema content must be an object")
    if not isinstance(tool_contract.content, Sequence) or isinstance(
        tool_contract.content, (str, bytes, bytearray)
    ):
        raise TypeError("tool contract content must be an array")
    tools: list[Mapping[str, Any]] = []
    for item in tool_contract.content:
        if not isinstance(item, Mapping):
            raise TypeError("each tool contract entry must be an object")
        tools.append(item)
    return build_instance_context(
        instance_id=request.instance_id,
        snapshot=request.snapshot,
        identity_prompt=identity.content,
        core_methodology=methodology.content,
        phase_instruction=phase.content,
        output_schema=output_schema.content,
        tools=tools,
        history_context=request.history_context,
        lesson_context=request.lesson_context,
        peer_context=request.peer_context,
        codename_map=request.codename_map,
        versions={
            "identity_prompt_version": identity.version_id,
            "core_methodology_version": methodology.version_id,
            "phase_prompt_version": phase.version_id,
            "output_schema_version": output_schema.version_id,
            "tool_contract_version": tool_contract.version_id,
        },
    )


build_prompt_envelope = assemble_prompt_envelope
