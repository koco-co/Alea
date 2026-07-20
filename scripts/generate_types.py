#!/usr/bin/env python3
"""Generate Pydantic v2 models from Alea's canonical JSON Schemas."""

from __future__ import annotations

import hashlib
import json
import keyword
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "shared" / "schemas"
OUTPUT = ROOT / "api" / "app" / "generated" / "schemas.py"
INIT_OUTPUT = OUTPUT.parent / "__init__.py"

Schema = dict[str, Any]
SchemaKey = tuple[str, str]


def pascal(value: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", value)
    result = "".join(part[:1].upper() + part[1:] for part in parts) or "Anonymous"
    return f"Model{result}" if result[0].isdigit() else result


def field_name(value: str) -> str:
    result = re.sub(r"\W", "_", value)
    if not result or result[0].isdigit() or keyword.iskeyword(result):
        result = f"field_{result}"
    return result


def pointer_join(pointer: str, token: str) -> str:
    escaped = token.replace("~", "~0").replace("/", "~1")
    return f"{pointer}/{escaped}"


def pointer_get(document: Schema, pointer: str) -> Schema:
    if pointer in ("", "#"):
        return document
    current: Any = document
    for token in pointer.removeprefix("#/").split("/"):
        current = current[token.replace("~1", "/").replace("~0", "~")]
    return current


documents = {
    path.name: json.loads(path.read_text(encoding="utf-8"))
    for path in sorted(SCHEMA_DIR.glob("*.json"))
}
names: dict[SchemaKey, str] = {}
used_names: set[str] = set()


def unique_name(candidate: str, file_name: str) -> str:
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate
    prefixed = pascal(Path(file_name).stem) + candidate
    index = 2
    while prefixed in used_names:
        prefixed = f"{pascal(Path(file_name).stem)}{candidate}{index}"
        index += 1
    used_names.add(prefixed)
    return prefixed


def is_named_schema(schema: Schema) -> bool:
    return bool(
        schema.get("type") == "object"
        or "properties" in schema
        or "oneOf" in schema
        or "allOf" in schema
        or schema.get("not") == {}
    )


def discover(file_name: str, schema: Schema, pointer: str, suggested: str) -> None:
    if is_named_schema(schema):
        candidate = pascal(str(schema.get("title") or suggested))
        names.setdefault((file_name, pointer), unique_name(candidate, file_name))
        suggested = names[(file_name, pointer)]

    for key, child in schema.get("$defs", {}).items():
        discover(file_name, child, pointer_join(pointer, "$defs") + f"/{key}", f"{suggested}{pascal(key)}")
    for key, child in schema.get("properties", {}).items():
        if isinstance(child, dict):
            discover(file_name, child, pointer_join(pointer_join(pointer, "properties"), key), f"{suggested}{pascal(key)}")
    items = schema.get("items")
    if isinstance(items, dict):
        discover(file_name, items, pointer_join(pointer, "items"), f"{suggested}Item")
    for keyword_name in ("oneOf", "anyOf", "allOf"):
        for index, child in enumerate(schema.get(keyword_name, [])):
            if isinstance(child, dict) and "$ref" not in child:
                discover(
                    file_name,
                    child,
                    pointer_join(pointer_join(pointer, keyword_name), str(index)),
                    f"{suggested}{pascal(keyword_name)}{index + 1}",
                )


for current_file, document in documents.items():
    discover(current_file, document, "#", pascal(Path(current_file).stem))


def resolve_ref(file_name: str, ref: str) -> tuple[str, str, Schema]:
    target_file_part, separator, fragment = ref.partition("#")
    target_file = Path(target_file_part).name if target_file_part else file_name
    pointer = f"#{fragment}" if separator else "#"
    return target_file, pointer, pointer_get(documents[target_file], pointer)


def constraint_args(schema: Schema) -> list[str]:
    mapping = {
        "minimum": "ge",
        "maximum": "le",
        "exclusiveMinimum": "gt",
        "exclusiveMaximum": "lt",
        "minLength": "min_length",
        "maxLength": "max_length",
        "minItems": "min_length",
        "maxItems": "max_length",
    }
    return [f"{target}={schema[source]!r}" for source, target in mapping.items() if source in schema]


def type_expr(file_name: str, schema: Schema, pointer: str) -> str:
    if not schema:
        return "Any"
    if "$ref" in schema:
        target_file, target_pointer, target = resolve_ref(file_name, schema["$ref"])
        return names.get((target_file, target_pointer), type_expr(target_file, target, target_pointer))
    if "const" in schema:
        return f"Literal[{schema['const']!r}]"
    if "enum" in schema:
        return "Literal[" + ", ".join(repr(value) for value in schema["enum"]) + "]"
    if "oneOf" in schema or "anyOf" in schema:
        variants = schema.get("oneOf", schema.get("anyOf", []))
        rendered = [
            type_expr(file_name, item, pointer_join(pointer_join(pointer, "oneOf"), str(index)))
            for index, item in enumerate(variants)
        ]
        return " | ".join(dict.fromkeys(rendered)) or "Any"
    if "allOf" in schema:
        referenced = [item for item in schema["allOf"] if "$ref" in item]
        if referenced:
            return type_expr(file_name, referenced[0], pointer)

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        non_null = [value for value in schema_type if value != "null"]
        base = type_expr(file_name, {**schema, "type": non_null[0]}, pointer) if non_null else "None"
        return f"{base} | None" if "null" in schema_type and base != "None" else base
    if schema_type == "null":
        return "None"
    if schema_type == "string":
        return {"uuid": "UUID", "date-time": "datetime"}.get(schema.get("format"), "str")
    if schema_type == "integer":
        return "int"
    if schema_type == "number":
        return "float"
    if schema_type == "boolean":
        return "bool"
    if schema_type == "array":
        item_schema = schema.get("items", {})
        item_pointer = pointer_join(pointer, "items")
        return f"list[{type_expr(file_name, item_schema, item_pointer)}]"
    if schema_type == "object" or "properties" in schema:
        return names.get((file_name, pointer), "dict[str, Any]")
    if schema.get("not") == {}:
        return "Never"
    return "Any"


def combined_object_parts(schema: Schema) -> tuple[list[Schema], list[Schema]]:
    bases: list[Schema] = []
    bodies: list[Schema] = []
    if schema.get("type") == "object" or "properties" in schema:
        bodies.append(schema)
    elif "allOf" in schema:
        for part in schema["allOf"]:
            (bases if "$ref" in part else bodies).append(part)
    else:
        bodies.append(schema)
    return bases, bodies


def render_object(file_name: str, pointer: str, schema: Schema, name: str) -> str:
    base_parts, body_parts = combined_object_parts(schema)
    bases = [type_expr(file_name, part, pointer) for part in base_parts]
    base = bases[0] if bases else "SchemaModel"
    properties: dict[str, Schema] = {}
    required: set[str] = set()
    for body in body_parts:
        properties.update(body.get("properties", {}))
        required.update(body.get("required", []))

    lines = [f"class {name}({base}):"]
    if not properties:
        if any(body.get("additionalProperties") is not False for body in body_parts):
            lines.append('    model_config = ConfigDict(extra="allow")')
        else:
            lines.append("    pass")
        return "\n".join(lines)

    for json_name, child in properties.items():
        child_pointer = pointer_join(pointer_join(pointer, "properties"), json_name)
        annotation = type_expr(file_name, child, child_pointer)
        args = constraint_args(child)
        python_name = field_name(json_name)
        if python_name != json_name:
            args.append(f"alias={json_name!r}")
        metadata: list[str] = []
        if args:
            metadata.append(f"Field({', '.join(args)})")
        if child.get("uniqueItems") is True:
            metadata.append("AfterValidator(_ensure_unique)")
        if metadata:
            annotation = f"Annotated[{annotation}, {', '.join(metadata)}]"
        if json_name not in required:
            if "None" not in annotation:
                annotation = f"{annotation} | None"
            lines.append(f"    {python_name}: {annotation} = None")
        else:
            lines.append(f"    {python_name}: {annotation}")

    title = schema.get("title")
    if title in {"BetProposal", "BetDebate"}:
        lines.extend(
            [
                "",
                '    @model_validator(mode="after")',
                "    def validate_decision_shape(self) -> Self:",
                '        if self.decision == "bet" and (self.plan is None or self.no_bet_reason is not None):',
                '            raise ValueError("bet requires plan and null no_bet_reason")',
                '        if self.decision == "no_bet" and (self.plan is not None or self.no_bet_reason is None):',
                '            raise ValueError("no_bet requires null plan and a reason")',
                "        return self",
            ]
        )
    if title == "MethodologyReview":
        lines.extend(
            [
                "",
                '    @model_validator(mode="after")',
                "    def validate_revision_shape(self) -> Self:",
                '        if self.decision == "revise_and_review" and not self.proposed_revision:',
                '            raise ValueError("revise_and_review requires proposed_revision")',
                '        if self.decision in {"support", "oppose"} and self.proposed_revision is not None:',
                '            raise ValueError("support and oppose require null proposed_revision")',
                "        return self",
            ]
        )
    return "\n".join(lines)


object_blocks: list[str] = []
root_blocks: list[str] = []
model_names: list[str] = []
for (current_file, pointer), name in names.items():
    schema = pointer_get(documents[current_file], pointer)
    if schema.get("type") == "object" or "properties" in schema or "allOf" in schema:
        object_blocks.append(render_object(current_file, pointer, schema, name))
        model_names.append(name)
    elif "oneOf" in schema or "anyOf" in schema:
        expression = type_expr(current_file, schema, pointer)
        root_blocks.append(f"class {name}(RootModel[{expression}]):\n    pass")
        model_names.append(name)

digest = hashlib.sha256(
    b"".join(path.read_bytes() for path in sorted(SCHEMA_DIR.glob("*.json")))
).hexdigest()
header = f'''# Generated by scripts/generate_types.py. DO NOT EDIT.\n# schema-sha256: {digest}\n\n'''
imports = '''from __future__ import annotations\n\nimport json\nfrom datetime import datetime\nfrom typing import Annotated, Any, Literal, Never, Self, TypeVar\nfrom uuid import UUID\n\nfrom pydantic import (\n    AfterValidator,\n    BaseModel,\n    ConfigDict,\n    Field,\n    RootModel,\n    model_validator,\n)\n\n\nUniqueValue = TypeVar("UniqueValue")\n\n\ndef _ensure_unique(items: list[UniqueValue]) -> list[UniqueValue]:\n    keys = [\n        json.dumps(\n            item.model_dump(mode="json") if isinstance(item, BaseModel) else item,\n            ensure_ascii=False,\n            sort_keys=True,\n            default=str,\n        )\n        for item in items\n    ]\n    if len(keys) != len(set(keys)):\n        raise ValueError("array items must be unique")\n    return items\n\n\nclass SchemaModel(BaseModel):\n    model_config = ConfigDict(extra="forbid")\n\n'''
rebuild = "\n\nfor _model in [\n" + "".join(f"    {name},\n" for name in model_names) + "]:\n"
rebuild += "    _model.model_rebuild(_types_namespace=globals())\n"

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    header + imports + "\n\n".join(object_blocks + root_blocks) + rebuild,
    encoding="utf-8",
)
INIT_OUTPUT.write_text(
    '"""Generated models backed by shared/schemas JSON Schema."""\n',
    encoding="utf-8",
)
print(f"generated {len(model_names)} Pydantic models -> {OUTPUT.relative_to(ROOT)}")
