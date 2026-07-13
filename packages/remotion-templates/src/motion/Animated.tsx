import {Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {ReactNode} from 'react';

type AnimatedProps = {
  children: ReactNode;
  preset: string;
  motionIntensity?: number;
};

export const Animated = ({children, preset, motionIntensity = 6}: AnimatedProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const duration = Math.round((450 + motionIntensity * 25) / (1000 / fps));
  const progress = interpolate(frame, [0, duration], [0, 1], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        opacity: progress,
        translate: preset === 'slideUp' ? `0 ${interpolate(progress, [0, 1], [24, 0])}px` : '0 0',
        scale: preset === 'zoomIn' ? interpolate(progress, [0, 1], [0.92, 1]) : 1,
      }}
    >
      {children}
    </div>
  );
};
