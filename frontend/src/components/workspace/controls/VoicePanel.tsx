/**
 * VoicePanel — task 5-2 Step 5, BR-3.
 *
 * Textarea for `VoiceSpec.text`, giọng nam/nữ select (`voice_id`), tốc độ
 * (`speed`, 0.8–1.3 per backend/app/schemas/scene.py:118-124). If the scene
 * was already produced (has `audio` — passed in as `hasProducedAudio`) and
 * the voice text changes from what it was when audio was produced, the old
 * audio is stale: show the "giọng đọc sẽ tạo lại" badge (BR-3) and report it
 * via `onStaleChange` so the caller can flag the scene / drive re-produce
 * (the actual re-produce trigger is task 6-1 BR-4 — out of scope here, this
 * control only owns the badge/flag).
 */

"use client";

import { useEffect, useState } from "react";
import { VOICE_OPTIONS, VOICE_SPEED_MIN, VOICE_SPEED_MAX, VOICE_SPEED_STEP } from "@/lib/scene/constants";

export interface VoicePanelValue {
  text: string;
  voiceId: string;
  speed: number;
}

export interface VoicePanelProps {
  value: VoicePanelValue;
  onChange: (next: VoicePanelValue) => void;
  /** True once this scene has a produced `voice.audio` asset. */
  hasProducedAudio: boolean;
  /** The voice text as it was at the time audio was last produced — compared
   * against `value.text` to detect a stale-triggering edit. */
  producedAudioText: string;
  /** Reports whether the current edit has made the produced audio stale. */
  onStaleChange?: (stale: boolean) => void;
  disabled?: boolean;
}

export function VoicePanel({
  value,
  onChange,
  hasProducedAudio,
  producedAudioText,
  onStaleChange,
  disabled,
}: VoicePanelProps) {
  const isStale = hasProducedAudio && value.text !== producedAudioText;

  // Report the derived stale flag to the caller whenever it changes, rather
  // than making the caller re-derive the same comparison.
  const [lastReported, setLastReported] = useState<boolean | null>(null);
  useEffect(() => {
    if (onStaleChange && lastReported !== isStale) {
      onStaleChange(isStale);
      setLastReported(isStale);
    }
  }, [isStale, onStaleChange, lastReported]);

  return (
    <div className="space-y-3" aria-label="Điều khiển giọng đọc">
      <div className="flex items-center justify-between">
        <label htmlFor="voice-panel-text" className="text-sm font-medium text-foreground">
          Lời đọc (voice-over)
        </label>
        {isStale && (
          <span
            role="status"
            className="inline-flex items-center gap-1 rounded-full border border-status-warn/40 bg-status-warn/10 px-2.5 py-0.5 text-xs font-medium text-status-warn"
          >
            ⚠ giọng đọc sẽ tạo lại
          </span>
        )}
      </div>
      <textarea
        id="voice-panel-text"
        value={value.text}
        disabled={disabled}
        maxLength={500}
        rows={4}
        onChange={(e) => onChange({ ...value, text: e.target.value })}
        className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm disabled:opacity-60"
      />

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="voice-panel-voice" className="mb-1 block text-sm font-medium text-foreground">
            Giọng
          </label>
          <select
            id="voice-panel-voice"
            value={value.voiceId}
            disabled={disabled}
            onChange={(e) => onChange({ ...value, voiceId: e.target.value })}
            className="w-full rounded-lg border border-border bg-muted px-3 py-2 text-sm disabled:opacity-60"
          >
            {VOICE_OPTIONS.map((voice) => (
              <option key={voice.id} value={voice.id}>
                {voice.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between">
            <label htmlFor="voice-panel-speed" className="text-sm font-medium text-foreground">
              Tốc độ
            </label>
            <span className="text-xs text-muted-foreground" aria-hidden="true">
              {value.speed.toFixed(2)}x
            </span>
          </div>
          <input
            id="voice-panel-speed"
            type="range"
            min={VOICE_SPEED_MIN}
            max={VOICE_SPEED_MAX}
            step={VOICE_SPEED_STEP}
            value={value.speed}
            disabled={disabled}
            aria-valuemin={VOICE_SPEED_MIN}
            aria-valuemax={VOICE_SPEED_MAX}
            aria-valuenow={value.speed}
            onChange={(e) => onChange({ ...value, speed: Number(e.target.value) })}
            className="w-full accent-primary disabled:opacity-60"
          />
        </div>
      </div>
    </div>
  );
}
