/**
 * schema-form/generate.ts — schema-driven SceneForm generator (BR-4).
 *
 * Reads a subset of JSON Schema and emits the matching HTML control
 * per field type (no hand-written per-field form code).
 *
 * Supported: string, number, integer, boolean, enum, textarea, array
 *
 * AC-4: add an optional field to the fixture schema → control auto-renders
 *      with zero FE code changes.
 */

/**
 * A JSON Schema subset used by the form generator. Deliberately a flat
 * optional-fields interface (not a discriminated union) — real JSON Schema
 * documents legally mix keywords (e.g. `oneOf` alongside `title`), and every
 * branch below only ever reads fields via `schema.type === "..."` narrowing,
 * never relies on excess-property checks.
 */
export interface JsonSchema {
  type?: "string" | "number" | "integer" | "boolean" | "array" | "object";
  enum?: string[];
  title?: string;
  description?: string;
  items?: JsonSchema;
  properties?: Record<string, JsonSchema>;
  required?: string[];
  oneOf?: JsonSchema[];
  anyOf?: JsonSchema[];
  minLength?: number;
}

export interface SchemaFieldProps {
  path: string[];
  schema: JsonSchema;
  /** current value — immer-style mutable updater would be nicer but we keep plain */
  value: unknown;
  onChange: (path: string[], value: unknown) => void;
  required?: boolean;
  /** 422 field_path mapped errors → inline render */
  fieldErrors?: Record<string, string>;
}

export function SchemaField({
  path,
  schema,
  value,
  onChange,
  required,
  fieldErrors = {},
}: SchemaFieldProps) {
  const pathKey = path.join(".");
  const errorMsg = fieldErrors[pathKey];

  const handleChange = (next: unknown) => onChange(path, next);

  if (schema.type === "string" && schema.enum) {
    return (
      <FieldWrapper
        label={schema.title ?? pathKey}
        description={schema.description}
        required={required}
        error={errorMsg}
      >
        <select
          value={(value as string) ?? ""}
          onChange={(e) => handleChange(e.target.value)}
          className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm"
          aria-invalid={!!errorMsg}
        >
          {schema.enum.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </FieldWrapper>
    );
  }

  if (schema.type === "string") {
    const isMultiline = !!(schema.minLength && schema.minLength > 80);

    if (isMultiline) {
      return (
        <FieldWrapper
          label={schema.title ?? pathKey}
          description={schema.description}
          required={required}
          error={errorMsg}
        >
          <textarea
            value={(value as string) ?? ""}
            onChange={(e) => handleChange(e.target.value)}
            rows={5}
            className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm"
            aria-invalid={!!errorMsg}
          />
        </FieldWrapper>
      );
    }

    return (
      <FieldWrapper
        label={schema.title ?? pathKey}
        description={schema.description}
        required={required}
        error={errorMsg}
      >
        <input
          type="text"
          value={(value as string) ?? ""}
          onChange={(e) => handleChange(e.target.value)}
          className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm"
          aria-invalid={!!errorMsg}
        />
      </FieldWrapper>
    );
  }

  if (schema.type === "number" || schema.type === "integer") {
    return (
      <FieldWrapper
        label={schema.title ?? pathKey}
        description={schema.description}
        required={required}
        error={errorMsg}
      >
        <input
          type="number"
          value={value == null ? "" : Number(value)}
          onChange={(e) =>
            handleChange(
              schema.type === "integer"
                ? Math.round(Number(e.target.value))
                : Number(e.target.value),
            )
          }
          className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm"
          aria-invalid={!!errorMsg}
        />
      </FieldWrapper>
    );
  }

  if (schema.type === "boolean") {
    return (
      <label className="flex items-center gap-2 py-2 text-sm">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => handleChange(e.target.checked)}
          className="size-4 rounded border-border"
        />
        <span>{schema.title ?? pathKey}</span>
      </label>
    );
  }

  if (schema.type === "array") {
    const arr = Array.isArray(value) ? value : [];
    return (
      <FieldWrapper
        label={schema.title ?? pathKey}
        description={schema.description}
        error={errorMsg}
      >
        <div className="space-y-2">
          {arr.map((item, i) => (
            <div
              key={i}
              className="flex items-center gap-2 rounded-lg border border-border bg-muted p-2"
            >
              <span className="text-xs text-muted-foreground">#{i + 1}</span>
              <span className="truncate text-sm">{JSON.stringify(item)}</span>
              <button
                type="button"
                onClick={() => {
                  const next = arr.filter((_, j) => j !== i);
                  handleChange(next);
                }}
                className="ml-auto text-xs text-destructive"
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => handleChange([...arr, ""])}
            className="rounded-lg border border-dashed border-border px-3 py-1.5 text-xs text-muted-foreground hover:border-primary hover:text-primary"
          >
            + Thêm
          </button>
        </div>
      </FieldWrapper>
    );
  }

  // Object without explicit type — recurse
  if (
    schema.type === "object" &&
    schema.properties &&
    Object.keys(schema.properties).length > 0
  ) {
    return (
      <div className="space-y-3">
        {Object.entries(schema.properties).map(([key, subSchema]) => (
          <SchemaField
            key={key}
            path={[...path, key]}
            schema={subSchema}
            value={(value as Record<string, unknown>)?.[key]}
            onChange={(p, v) => {
              const next = { ...(value as Record<string, unknown>) };
              next[p[p.length - 1]] = v;
              onChange(path, next);
            }}
            required={schema.required?.includes(key)}
            fieldErrors={fieldErrors}
          />
        ))}
      </div>
    );
  }

  return (
    <FieldWrapper label={schema.title ?? pathKey} error={errorMsg}>
      <pre className="rounded-lg border border-border bg-muted p-2 text-xs">
        {JSON.stringify(value ?? schema, null, 2)}
      </pre>
    </FieldWrapper>
  );
}

/* ── wrapper: label + error ─────────────────────────── */

interface FieldWrapperProps {
  label: string;
  description?: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}

export function FieldWrapper({
  label,
  description,
  required,
  error,
  children,
}: FieldWrapperProps) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-foreground">
        {label}
        {required && <span className="ml-1 text-status-fail">*</span>}
      </label>
      {description && (
        <p className="mb-2 text-xs text-muted-foreground">{description}</p>
      )}
      {children}
      {error && (
        <p className="mt-1.5 text-xs text-status-fail" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
