// The whole film's graphics in one transparent track: every item (title, captions, end card, lower third, the
// film's own graphics) at its frame. 14_render lays this over the film frame by frame, so nothing depends on
// timestamps lining up. A film's own component with a built-in's name (e.g. Title) replaces the built-in.
import React from 'react';
import {Sequence} from 'remotion';
import {EVENT} from 'beatcut-event';
import {Captions} from './Captions';
import {EndCard, LowerThird} from './Cards';
import {Size} from './common';
import {Callout, Pop} from './Text';
import {Title} from './Title';

const COMPONENTS: Record<string, React.FC<any>> = {Title, Captions, EndCard, LowerThird, Pop, Callout, ...EVENT};

export type Item = {from: number; composition: string; props: Record<string, unknown> & {frames: number}};
export type OverlayProps = Size & {items: Item[]};

export const Overlay: React.FC<OverlayProps> = ({items, width, height, fps}) => (
	<>
		{items.map((it, k) => {
			const C = COMPONENTS[it.composition];
			if (!C) throw new Error(`no graphic called ${it.composition} (built-in or in the event's graphics/ folder)`);
			return (
				<Sequence key={k} from={it.from} durationInFrames={Math.max(1, it.props.frames)} layout="absolute-fill">
					<C {...it.props} width={width} height={height} fps={fps} />
				</Sequence>
			);
		})}
	</>
);
