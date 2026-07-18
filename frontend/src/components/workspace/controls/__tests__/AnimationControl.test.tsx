/**
 * AnimationControl tests — task 5-2 Step 3 (AC-1 happy, AC-5 a11y keyboard slider).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AnimationControl, type AnimationControlValue } from "../AnimationControl";
import { ANIMATION_TYPES } from "@/lib/scene/constants";

const BASE_VALUE: AnimationControlValue = { type: "fade_in", delayMs: 500 };

describe("AnimationControl", () => {
  it("renders every Layout-Engine-approved animation type and none other (AC-1)", () => {
    render(<AnimationControl value={BASE_VALUE} onChange={() => {}} />);
    const select = screen.getByLabelText("Kiểu hiệu ứng") as HTMLSelectElement;
    const optionValues = Array.from(select.options).map((o) => o.value);
    expect(optionValues).toEqual([...ANIMATION_TYPES]);
  });

  it("changing the type select calls onChange with the new type", () => {
    const onChange = vi.fn();
    render(<AnimationControl value={BASE_VALUE} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Kiểu hiệu ứng"), { target: { value: "zoom_in" } });
    expect(onChange).toHaveBeenCalledWith({ ...BASE_VALUE, type: "zoom_in" });
  });

  it("AC-5: ArrowRight on the delay slider increases delay by one step", () => {
    const onChange = vi.fn();
    render(<AnimationControl value={BASE_VALUE} onChange={onChange} />);
    const slider = screen.getByLabelText("Độ trễ (delay)");
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    expect(onChange).toHaveBeenCalledWith({ ...BASE_VALUE, delayMs: 600 });
  });

  it("AC-5: ArrowLeft on the delay slider decreases delay by one step", () => {
    const onChange = vi.fn();
    render(<AnimationControl value={BASE_VALUE} onChange={onChange} />);
    const slider = screen.getByLabelText("Độ trễ (delay)");
    fireEvent.keyDown(slider, { key: "ArrowLeft" });
    expect(onChange).toHaveBeenCalledWith({ ...BASE_VALUE, delayMs: 400 });
  });

  it("clamps delay to [0, 5000] at the bounds", () => {
    const onChangeAtMax = vi.fn();
    render(
      <AnimationControl value={{ type: "fade_in", delayMs: 5000 }} onChange={onChangeAtMax} />,
    );
    fireEvent.keyDown(screen.getByLabelText("Độ trễ (delay)"), { key: "ArrowRight" });
    expect(onChangeAtMax).toHaveBeenCalledWith({ type: "fade_in", delayMs: 5000 });

    const onChangeAtMin = vi.fn();
    render(<AnimationControl value={{ type: "fade_in", delayMs: 0 }} onChange={onChangeAtMin} />);
    fireEvent.keyDown(screen.getAllByLabelText("Độ trễ (delay)")[1], { key: "ArrowLeft" });
    expect(onChangeAtMin).toHaveBeenCalledWith({ type: "fade_in", delayMs: 0 });
  });

  it("dragging the slider (change event) calls onChange with the new numeric value", () => {
    const onChange = vi.fn();
    render(<AnimationControl value={BASE_VALUE} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Độ trễ (delay)"), { target: { value: "1200" } });
    expect(onChange).toHaveBeenCalledWith({ ...BASE_VALUE, delayMs: 1200 });
  });
});
