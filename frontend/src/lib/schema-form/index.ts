/**
 * index.ts — barrel export for schema-form, plus the SchemaForm
 * composition piece that wires generate.ts to scene schema.
 */

export { SchemaField, FieldWrapper, type SchemaFieldProps } from "./generate";

// Re-export for consumers that want to map a full schema at once:
export type { JsonSchema } from "./generate";
