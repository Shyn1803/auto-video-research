/**
 * TextControl tests — task 5-2 Step 1 (AC-1 happy, AC-4/BR-4 bold marker).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TextControl, type TextControlValue } from "../TextControl";
import { applyBoldMarker } from "../BoldButton";

const BASE_VALUE: TextControlValue = {
  content: "hello world",
  role: "body",
  position: "center",
  color: null,
  highlightColor: null,
};

describe("applyBoldMarker (pure)", () => {
  it("wraps a selection in ** markers", () => {
    const result = applyBoldMarker("hello world", 0, 5);
    expect(result.text).toBe("**hello** world");
    expect(result.selectionStart).toBe(2);
    expect(result.selectionEnd).toBe(7);
  });

  it("inserts an empty **** pair with cursor centered when nothing selected", () => {
    const result = applyBoldMarker("hi", 2, 2);
    expect(result.text).toBe("hi****");
    expect(result.selectionStart).toBe(4);
    expect(result.selectionEnd).toBe(4);
  });
});

describe("TextControl", () => {
  it("renders content/role/position and reports changes (AC-1 happy)", () => {
    const onChange = vi.fn();
    render(<TextControl value={BASE_VALUE} onChange={onChange} />);

    const textarea = screen.getByLabelText("Nội dung") as HTMLTextAreaElement;
    expect(textarea.value).toBe("hello world");

    fireEvent.change(textarea, { target: { value: "hello there" } });
    expect(onChange).toHaveBeenCalledWith({ ...BASE_VALUE, content: "hello there" });

    fireEvent.change(screen.getByLabelText("Vai trò"), { target: { value: "heading" } });
    expect(onChange).toHaveBeenCalledWith({ ...BASE_VALUE, role: "heading" });

    fireEvent.change(screen.getByLabelText("Vị trí"), { target: { value: "top" } });
    expect(onChange).toHaveBeenCalledWith({ ...BASE_VALUE, position: "top" });
  });

  it("BR-4: clicking the B button wraps the current selection in ** markers", () => {
    const onChange = vi.fn();
    render(<TextControl value={BASE_VALUE} onChange={onChange} />);

    const textarea = screen.getByLabelText("Nội dung") as HTMLTextAreaElement;
    textarea.focus();
    textarea.setSelectionRange(0, 5); // "hello"

    fireEvent.click(screen.getByRole("button", { name: /in đậm/i }));

    expect(onChange).toHaveBeenCalledWith({ ...BASE_VALUE, content: "**hello** world" });
  });

  it("BR-4: Ctrl+B inserts the bold marker without the user typing **", () => {
    const onChange = vi.fn();
    render(<TextControl value={BASE_VALUE} onChange={onChange} />);

    const textarea = screen.getByLabelText("Nội dung") as HTMLTextAreaElement;
    textarea.focus();
    textarea.setSelectionRange(6, 11); // "world"

    fireEvent.keyDown(textarea, { key: "b", ctrlKey: true });

    expect(onChange).toHaveBeenCalledWith({ ...BASE_VALUE, content: "hello **world**" });
  });

  it("disables all controls when disabled=true (readonly station)", () => {
    render(<TextControl value={BASE_VALUE} onChange={() => {}} disabled />);
    expect(screen.getByLabelText("Nội dung")).toBeDisabled();
    expect(screen.getByLabelText("Vai trò")).toBeDisabled();
    expect(screen.getByLabelText("Vị trí")).toBeDisabled();
    expect(screen.getByRole("button", { name: /in đậm/i })).toBeDisabled();
  });
});
