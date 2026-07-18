/**
 * ColorPicker tests — task 5-2 Step 2 (BR-2: preset + custom hex, contrast
 * warning is non-blocking).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ColorPicker } from "../ColorPicker";

describe("ColorPicker", () => {
  it("clicking a preset swatch calls onChange with that hex", () => {
    const onChange = vi.fn();
    render(<ColorPicker label="Màu chữ" value={null} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "#FFFFFF" }));
    expect(onChange).toHaveBeenCalledWith("#FFFFFF");
  });

  it("typing a custom hex calls onChange and does not block on low contrast", () => {
    const onChange = vi.fn();
    render(
      <ColorPicker
        label="Màu chữ"
        value={null}
        onChange={onChange}
        backgroundColor="#111111"
      />,
    );

    const input = screen.getByLabelText("Màu chữ — mã hex tuỳ chỉnh");
    fireEvent.change(input, { target: { value: "#222222" } });

    // Low-contrast custom color must still commit — BR-2 "không chặn".
    expect(onChange).toHaveBeenCalledWith("#222222");
  });

  it("shows a non-blocking contrast warning below the AA threshold (4.5:1)", () => {
    const onChange = vi.fn();
    // #222222 on #111111 background is far below 4.5:1.
    render(
      <ColorPicker
        label="Màu chữ"
        value="#222222"
        onChange={onChange}
        backgroundColor="#111111"
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/tương phản thấp/i);
  });

  it("does not show a warning when contrast is comfortably above AA threshold", () => {
    const onChange = vi.fn();
    render(
      <ColorPicker label="Màu chữ" value="#FFFFFF" onChange={onChange} backgroundColor="#0F172A" />,
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("clearing the custom hex input calls onChange(null)", () => {
    const onChange = vi.fn();
    render(<ColorPicker label="Màu chữ" value="#FFFFFF" onChange={onChange} />);
    const input = screen.getByLabelText("Màu chữ — mã hex tuỳ chỉnh");
    fireEvent.change(input, { target: { value: "" } });
    expect(onChange).toHaveBeenCalledWith(null);
  });
});
