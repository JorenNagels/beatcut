// The compositions 14_render uses. Size, fps and length come from the props (calculateMetadata), so one bundle
// serves every format. `npm run studio` opens them with the default props below to tweak the look.
import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {Captions, CaptionsProps} from './Captions';
import {EndCard, EndCardProps, LowerThird, LowerThirdProps} from './Cards';
import {Size} from './common';
import {Overlay, OverlayProps} from './Overlay';
import {Callout, CalloutProps, Pop, PopProps} from './Text';
import {Title, TitleProps} from './Title';

const meta: CalculateMetadataFunction<Size> = ({props}) => ({
	width: props.width, height: props.height, fps: props.fps, durationInFrames: Math.max(1, props.frames),
});
const size: Size = {width: 1920, height: 1080, fps: 30, frames: 100};
const music = {beats: [0.2, 0.62, 1.04, 1.45, 1.87, 2.29, 2.7], bars: [0.2, 1.87], accent: '#FFE600'};

export const Root: React.FC = () => (
	<>
		<Composition id="Overlay" component={Overlay} calculateMetadata={meta as CalculateMetadataFunction<OverlayProps>}
			defaultProps={{...size, frames: 150, items: [
				{from: 0, composition: 'Title', props: {frames: 100, big: 'IBIZA', sub: 'SUMMER', tag: '2027', bpm: 144, style: 'slam'}},
				{from: 100, composition: 'LowerThird', props: {frames: 50, text: 'Sam', sub: 'the one who fell', accent: '#FFE600'}},
			]} as OverlayProps}
			width={1920} height={1080} fps={30} durationInFrames={150} />
		<Composition id="Title" component={Title} calculateMetadata={meta as CalculateMetadataFunction<TitleProps>}
			defaultProps={{...size, big: 'IBIZA', sub: 'SUMMER', tag: '2027', bpm: 144, style: 'slam'} as TitleProps}
			width={1920} height={1080} fps={30} durationInFrames={100} />
		<Composition id="Captions" component={Captions} calculateMetadata={meta as CalculateMetadataFunction<CaptionsProps>}
			defaultProps={{...size, width: 1080, height: 1920, frames: 90, start: 0, highlight: '#FFE600', bottom: 576, size: 108,
				groups: [{words: ['oh', 'my', 'god'], steps: [{a: 0.1, b: 0.5, i: 0}, {a: 0.5, b: 0.9, i: 1}, {a: 0.9, b: 1.6, i: 2}], emoji: '😱'},
					{words: ['let\'s', 'go'], steps: [{a: 1.8, b: 2.2, i: 0}, {a: 2.2, b: 2.9, i: 1}], emoji: '🚀'}]} as CaptionsProps}
			width={1080} height={1920} fps={30} durationInFrames={90} />
		<Composition id="EndCard" component={EndCard} calculateMetadata={meta as CalculateMetadataFunction<EndCardProps>}
			defaultProps={{...size, frames: 150, title: 'Ibiza 2027', lines: ['Music:  Artist – Song']} as EndCardProps}
			width={1920} height={1080} fps={30} durationInFrames={150} />
		<Composition id="LowerThird" component={LowerThird} calculateMetadata={meta as CalculateMetadataFunction<LowerThirdProps>}
			defaultProps={{...size, frames: 90, text: 'Sam', sub: 'the one who fell', accent: '#FFE600'} as LowerThirdProps}
			width={1920} height={1080} fps={30} durationInFrames={90} />
		<Composition id="Pop" component={Pop} calculateMetadata={meta as CalculateMetadataFunction<PopProps>}
			defaultProps={{...size, ...music, frames: 90, text: 'send it 🚀'} as PopProps}
			width={1920} height={1080} fps={30} durationInFrames={90} />
		<Composition id="Callout" component={Callout} calculateMetadata={meta as CalculateMetadataFunction<CalloutProps>}
			defaultProps={{...size, ...music, frames: 90, x: 0.4, y: 0.45, text: 'Vincent 👀'} as CalloutProps}
			width={1920} height={1080} fps={30} durationInFrames={90} />
	</>
);
