import {Img} from 'remotion';

export const Watermark = ({src}: {src: string}) => <Img src={src} style={{position: 'absolute', right: 32, top: 32, width: 96}} />;
