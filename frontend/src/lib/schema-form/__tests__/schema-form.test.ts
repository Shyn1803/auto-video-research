/**
 * schema-form tests — AC-4 coverage.
 *
 * Add an optional field to the schema fixture → control renders with
 * zero FE code changes.
 */

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { FieldWrapper, SchemaField } from "@/lib/schema-form/generate";

/* ── FieldWrapper renders label + children ───────────── */

describe("FieldWrapper", () => {
  it("renders label and child", () => {
    render(
      <FieldWrapper label="Tiêu đề">
        <input data-testid="inp" />
      </FieldWrapper>,
    );
    expect(screen.getByText("Tiêu đề")).toBeDefined();
    expect(screen.getByTestId("inp")).toBeDefined();
  });

  it("shows required asterisk when required", () => {
    render(
      <FieldWrapper label="Mô tả" required>
        <input />
      </FieldWrapper>,
    );
    const label = screen.getByText("Mô tả");
    expect(label.innerHTML).toContain("*");
  });

  it("shows error message", () => {
    render(
      <FieldWrapper label="Giọng" error="Bắt buộc nhập">
        <input />
      </FieldWrapper>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Bắt buộc nhập");
  });
});

/* ── SchemaField — AC-4: new optional field auto-renders ── */

describe("SchemaField — AC-4 schema-driven", () => {
  const schemaString: Parameters<typeof SchemaField>[0]["schema"] = {
    type: "string",
    title: "Tiêu đề",
  };

  it("renders input for string", () => {
    render(
      <SchemaField
        path={["title"]}
        schema={schemaString}
        value=""
        onChange={() => {}}
      />,
    );
    expect(screen.getByRole("textbox")).toBeDefined();
  });

  it("renders number for number", () => {
    render(
      <SchemaField
        path={["duration_ms"]}
        schema={{ type: "number" }}
        value={6000}
        onChange={() => {}}
      />,
    );
    expect(screen.getByRole("spinbutton")).toBeDefined();
  });

  it("renders select for enum", () => {
    render(
      <SchemaField
        path={["layout_override"]}
        schema={{ type: "string", enum: ["Hero", "TextFocus", "MediaText"] }}
        value=""
        onChange={() => {}}
      />,
    );
    const sel = screen.getByRole("combobox");
    expect(sel).toBeDefined();
    expect(sel.children.length).toBe(3);
  });

  it("renders checkbox for boolean", () => {
    render(
      <SchemaField
        path={["sticky"]}
        schema={{ type: "boolean", title: "Ghim" }}
        value={false}
        onChange={() => {}}
      />,
    );
    expect(screen.getByRole("checkbox")).toBeDefined();
    expect(screen.getByText("Ghim")).toBeDefined();
  });

  it("renders array editor", () => {
    render(
      <SchemaField
        path={["bullets"]}
        schema={{ type: "array" }}
        value={["a", "b"]}
        onChange={() => {}}
      />,
    );
    expect(screen.getByText("#1")).toBeDefined();
    expect(screen.getByText("#2")).toBeDefined();
  });

  it("AC-4: adding an optional field to schema fixture renders it with zero FE changes",
    () => {
      // fixture gets a new optional string field called "caption_override"
      // — frontend should pick it up without any new component code.
      render(
        <SchemaField
          path={["caption_override"]}
          schema={{ type: "string", title: "Phụ đề caption" }}
          value={undefined}
          onChange={() => {}}
          required={false}
        />,
      );
      expect(screen.getByText("Phụ đề caption")).toBeDefined();
      expect(screen.getByRole("textbox")).toBeDefined();
    },
  );
});
