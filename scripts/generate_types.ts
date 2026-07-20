#!/usr/bin/env bun
/** Generate Zod schemas and inferred TypeScript types from canonical JSON Schema. */

import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";

type JsonSchema = Record<string, unknown>;

const root = resolve(import.meta.dir, "..");
const schemaDir = join(root, "shared", "schemas");
const output = join(root, "web", "src", "generated", "schemas.ts");
const files = readdirSync(schemaDir).filter((name) => name.endsWith(".json")).sort();
const documents = new Map<string, JsonSchema>(
  files.map((name) => [name, JSON.parse(readFileSync(join(schemaDir, name), "utf8"))]),
);

function pascal(value: string): string {
  const result = (value.match(/[A-Za-z0-9]+/g) ?? ["Anonymous"])
    .map((part) => part.slice(0, 1).toUpperCase() + part.slice(1))
    .join("");
  return /^\d/.test(result) ? `Model${result}` : result;
}

function getPointer(document: JsonSchema, pointer: string): JsonSchema {
  if (!pointer || pointer === "#") return document;
  return pointer
    .replace(/^#\//, "")
    .split("/")
    .reduce<unknown>((current, token) => {
      const key = token.replaceAll("~1", "/").replaceAll("~0", "~");
      return (current as Record<string, unknown>)[key];
    }, document) as JsonSchema;
}

function resolveRef(currentFile: string, ref: string): [string, JsonSchema] {
  const [filePart, fragment] = ref.split("#", 2);
  const targetFile = filePart ? basename(filePart) : currentFile;
  const document = documents.get(targetFile);
  if (!document) throw new Error(`missing schema document for ${ref}`);
  return [targetFile, getPointer(document, fragment ? `#${fragment}` : "#")];
}

function literal(value: unknown): string {
  return `z.literal(${JSON.stringify(value)})`;
}

function applyConstraints(expression: string, schema: JsonSchema): string {
  let result = expression;
  if (typeof schema.minLength === "number") result += `.min(${schema.minLength})`;
  if (typeof schema.maxLength === "number") result += `.max(${schema.maxLength})`;
  if (typeof schema.minimum === "number") result += `.min(${schema.minimum})`;
  if (typeof schema.maximum === "number") result += `.max(${schema.maximum})`;
  if (typeof schema.exclusiveMinimum === "number") result += `.gt(${schema.exclusiveMinimum})`;
  if (typeof schema.exclusiveMaximum === "number") result += `.lt(${schema.exclusiveMaximum})`;
  if (typeof schema.minItems === "number") result += `.min(${schema.minItems})`;
  if (typeof schema.maxItems === "number") result += `.max(${schema.maxItems})`;
  if (schema.uniqueItems === true) result += ".superRefine(requireUniqueItems)";
  return result;
}

function render(fileName: string, schema: JsonSchema, seen: Set<string> = new Set()): string {
  if (Object.keys(schema).length === 0) return "z.unknown()";
  if (typeof schema.$ref === "string") {
    const key = `${fileName}:${schema.$ref}`;
    if (seen.has(key)) return "z.unknown()";
    const [targetFile, target] = resolveRef(fileName, schema.$ref);
    return render(targetFile, target, new Set([...seen, key]));
  }
  if ("const" in schema) return literal(schema.const);
  if (Array.isArray(schema.enum)) {
    const variants = schema.enum.map(literal);
    return variants.length === 1 ? variants[0] : `z.union([${variants.join(", ")}])`;
  }
  if (Array.isArray(schema.oneOf) || Array.isArray(schema.anyOf)) {
    const options = (schema.oneOf ?? schema.anyOf) as JsonSchema[];
    const variants = options.map((item) => render(fileName, item, seen));
    return variants.length === 1 ? variants[0] : `z.union([${variants.join(", ")}])`;
  }
  if (Array.isArray(schema.allOf) && schema.type !== "object" && !schema.properties) {
    const variants = (schema.allOf as JsonSchema[]).map((item) => render(fileName, item, seen));
    return variants.reduce((left, right) => `${left}.and(${right})`);
  }
  if (schema.not && Object.keys(schema.not as JsonSchema).length === 0) return "z.never()";

  const declaredTypes = Array.isArray(schema.type) ? (schema.type as string[]) : [schema.type];
  const nullable = declaredTypes.includes("null");
  const schemaType = declaredTypes.find((value) => value !== "null");
  if (!schemaType && nullable) return "z.null()";
  let expression: string;

  switch (schemaType) {
    case "string":
      expression = "z.string()";
      if (schema.format === "uuid") expression += ".uuid()";
      if (schema.format === "date-time") expression += ".datetime({ offset: true })";
      break;
    case "integer":
      expression = "z.number().int()";
      break;
    case "number":
      expression = "z.number()";
      break;
    case "boolean":
      expression = "z.boolean()";
      break;
    case "array":
      expression = `z.array(${render(fileName, (schema.items as JsonSchema) ?? {}, seen)})`;
      break;
    case "object": {
      const properties = (schema.properties as Record<string, JsonSchema> | undefined) ?? {};
      const required = new Set((schema.required as string[] | undefined) ?? []);
      if (Object.keys(properties).length === 0 && schema.additionalProperties !== false) {
        expression = "z.record(z.string(), z.unknown())";
        break;
      }
      const fields = Object.entries(properties).map(([name, child]) => {
        let childExpression = render(fileName, child, seen);
        if (!required.has(name)) childExpression += ".optional()";
        return `${JSON.stringify(name)}: ${childExpression}`;
      });
      expression = `z.object({${fields.join(", ")}})`;
      expression += schema.additionalProperties === false ? ".strict()" : ".passthrough()";
      break;
    }
    case "null":
      expression = "z.null()";
      break;
    default:
      expression = "z.unknown()";
  }

  expression = applyConstraints(expression, schema);
  if (schema.title === "BetProposal" || schema.title === "BetDebate") {
    expression += ".superRefine(requireBetDecisionShape)";
  }
  if (schema.title === "MethodologyReview") {
    expression += ".superRefine(requireMethodologyDecisionShape)";
  }
  return nullable && schemaType !== "null" ? `${expression}.nullable()` : expression;
}

const exports: Array<{ fileName: string; name: string; schema: JsonSchema }> = [];
const usedNames = new Set<string>();
for (const fileName of files) {
  const document = documents.get(fileName)!;
  const rootName = pascal(String(document.title ?? basename(fileName, ".json")));
  const uniqueRoot = usedNames.has(rootName) ? `${pascal(basename(fileName, ".json"))}${rootName}` : rootName;
  usedNames.add(uniqueRoot);
  exports.push({ fileName, name: uniqueRoot, schema: document });
  for (const [defName, defSchema] of Object.entries(
    (document.$defs as Record<string, JsonSchema> | undefined) ?? {},
  )) {
    const proposed = pascal(String(defSchema.title ?? `${pascal(basename(fileName, ".json"))}${pascal(defName)}`));
    const unique = usedNames.has(proposed) ? `${pascal(basename(fileName, ".json"))}${proposed}` : proposed;
    usedNames.add(unique);
    exports.push({ fileName, name: unique, schema: defSchema });
  }
}

const digest = createHash("sha256")
  .update(files.map((name) => readFileSync(join(schemaDir, name))).join(""))
  .digest("hex");
const blocks = exports.map(({ fileName, name, schema }) => {
  const schemaName = `${name}Schema`;
  return `export const ${schemaName} = ${render(fileName, schema)};\nexport type ${name} = z.infer<typeof ${schemaName}>;`;
});
const source = `// Generated by scripts/generate_types.ts. DO NOT EDIT.\n// schema-sha256: ${digest}\n\nimport { z } from "zod";\n\nfunction requireUniqueItems(items: unknown[], context: z.RefinementCtx): void {\n  const keys = items.map((item) => JSON.stringify(item));\n  if (new Set(keys).size !== keys.length) {\n    context.addIssue({ code: "custom", message: "array items must be unique" });\n  }\n}\n\nfunction requireBetDecisionShape(value: unknown, context: z.RefinementCtx): void {\n  if (typeof value !== "object" || value === null) return;\n  const data = value as Record<string, unknown>;\n  const invalidBet = data.decision === "bet" && (data.plan == null || data.no_bet_reason !== null);\n  const invalidNoBet = data.decision === "no_bet" && (data.plan !== null || typeof data.no_bet_reason !== "string");\n  if (invalidBet || invalidNoBet) {\n    context.addIssue({ code: "custom", message: "decision, plan, and no_bet_reason are inconsistent" });\n  }\n}\n\nfunction requireMethodologyDecisionShape(value: unknown, context: z.RefinementCtx): void {\n  if (typeof value !== "object" || value === null) return;\n  const data = value as Record<string, unknown>;\n  const invalidRevision = data.decision === "revise_and_review" && !(typeof data.proposed_revision === "string" && data.proposed_revision.length > 0);\n  const invalidFinal = (data.decision === "support" || data.decision === "oppose") && data.proposed_revision !== null;\n  if (invalidRevision || invalidFinal) {\n    context.addIssue({ code: "custom", message: "decision and proposed_revision are inconsistent" });\n  }\n}\n\n${blocks.join("\n\n")}\n`;

mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, source, "utf8");
console.log(`generated ${exports.length} Zod schemas -> ${output.replace(`${root}/`, "")}`);
