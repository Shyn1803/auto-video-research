/**
 * VoicePanel tests — task 5-2 Step 5 (AC-3 biên/BR-3).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VoicePanel, type VoicePanelValue } from "../VoicePanel";

const BASE_VALUE: VoicePanelValue = {
  text: "Xin chào các bạn",
  voiceId: "vi-VN-female-1",
  speed: 1.0,
};

describe("VoicePanel", () => {
  it("renders text/voice/speed and reports changes (AC-1 happy)", () => {
    const onChange = vi.fn();
    render(
      <VoicePanel
        value={BASE_VALUE}
        onChange={onChange}
        hasProducedAudio={false}
        producedAudioText={BASE_VALUE.text}
      />,
    );

    fireEvent.change(screen.getByLabelText("Lời đọc (voice-over)"), {
      target: { value: "Xin chào các bạn nhé" },
    });
    expect(onChange).toHaveBeenCalledWith({ ...BASE_VALUE, text: "Xin chào các bạn nhé" });

    fireEvent.change(screen.getByLabelText("Giọng"), { target: { value: "vi-VN-male-1" } });
    expect(onChange).toHaveBeenCalledWith({ ...BASE_VALUE, voiceId: "vi-VN-male-1" });
  });

  it("AC-3/BR-3: no stale badge when the scene has never been produced", () => {
    render(
      <VoicePanel
        value={{ ...BASE_VALUE, text: "changed" }}
        onChange={() => {}}
        hasProducedAudio={false}
        producedAudioText={BASE_VALUE.text}
      />,
    );
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("AC-3/BR-3: no stale badge when produced audio's text still matches", () => {
    render(
      <VoicePanel
        value={BASE_VALUE}
        onChange={() => {}}
        hasProducedAudio
        producedAudioText={BASE_VALUE.text}
      />,
    );
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("AC-3/BR-3: stale badge appears once voice text diverges from the produced audio's text", () => {
    render(
      <VoicePanel
        value={{ ...BASE_VALUE, text: "Xin chào các bạn, hôm nay" }}
        onChange={() => {}}
        hasProducedAudio
        producedAudioText={BASE_VALUE.text}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("giọng đọc sẽ tạo lại");
  });

  it("reports the stale flag to the caller via onStaleChange", () => {
    const onStaleChange = vi.fn();
    render(
      <VoicePanel
        value={{ ...BASE_VALUE, text: "edited" }}
        onChange={() => {}}
        hasProducedAudio
        producedAudioText={BASE_VALUE.text}
        onStaleChange={onStaleChange}
      />,
    );
    expect(onStaleChange).toHaveBeenCalledWith(true);
  });

  it("speed slider is keyboard/drag operable within [0.8, 1.3]", () => {
    const onChange = vi.fn();
    render(
      <VoicePanel
        value={BASE_VALUE}
        onChange={onChange}
        hasProducedAudio={false}
        producedAudioText={BASE_VALUE.text}
      />,
    );
    const slider = screen.getByLabelText("Tốc độ") as HTMLInputElement;
    expect(slider.min).toBe("0.8");
    expect(slider.max).toBe("1.3");
    fireEvent.change(slider, { target: { value: "1.2" } });
    expect(onChange).toHaveBeenCalledWith({ ...BASE_VALUE, speed: 1.2 });
  });
});
