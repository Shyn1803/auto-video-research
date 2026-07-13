import {Img, interpolate, useCurrentFrame} from 'remotion';

export const Media = ({src, kenBurns = true}: {src: string; kenBurns?: boolean}) => {
  const frame = useCurrentFrame();
  return <Img src={src} style={{width: '100%', height: '100%', objectFit: 'cover', scale: kenBurns ? interpolate(frame, [0, 180], [1, 1.08], {extrapolateRight: 'clamp'}) : 1}} />;
};
