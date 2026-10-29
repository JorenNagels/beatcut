// Word-by-word captions (TikTok / Reels style) for one stretch of speech. 14_render passes the word groups already
// timed on the film timeline (subs_lib.caption_groups): each group shows 1-3 words, the current word is highlighted
// and pops, a new group springs in, an emoji (when one fits the words) bounces in after the group.
import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame} from 'remotion';
import {FILM_FONT, Size, useFilmFont} from './common';

export type Step = {a: number; b: number; i: number};
export type Group = {words: string[]; steps: Step[]; emoji?: string};
export type CaptionsProps = Size & {groups: Group[]; start: number; highlight: string; bottom: number; size: number};

export const Captions: React.FC<CaptionsProps> = ({groups, start, highlight, bottom, size, fps}) => {
	useFilmFont();
	const frame = useCurrentFrame();
	const T = start + frame / fps;
	const g = groups.find((x) => x.steps[0].a <= T && T < x.steps[x.steps.length - 1].b);
	if (!g) return null;
	const step = [...g.steps].reverse().find((s) => s.a <= T) || g.steps[0];
	const f = (sec: number) => Math.round((sec - start) * fps);
	const enter = spring({frame: frame - f(g.steps[0].a), fps, config: {damping: 12, stiffness: 220, mass: 0.6}});
	const pop = spring({frame: frame - f(step.a), fps, config: {damping: 10, stiffness: 300, mass: 0.5}});
	const emojiIn = spring({frame: frame - f(g.steps[0].a) - 3, fps, config: {damping: 8, stiffness: 180}});
	const stroke = Math.max(2, size * 0.12);
	return (
		<AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: bottom}}>
			<div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', alignItems: 'center', gap: size * 0.28, maxWidth: '88%',
				transform: `scale(${0.7 + 0.3 * enter})`}}>
				{g.words.map((w, i) => (
					<span key={i} style={{
						fontFamily: FILM_FONT, fontWeight: 800, fontSize: size, lineHeight: 1.05, textTransform: 'uppercase',
						color: i === step.i ? highlight : 'white', WebkitTextStroke: `${stroke}px black`, paintOrder: 'stroke fill',
						textShadow: `0 ${size * 0.06}px ${size * 0.12}px rgba(0,0,0,0.55)`,
						display: 'inline-block', transform: i === step.i ? `scale(${1 + 0.12 * (1 - pop) + 0.06}) rotate(${-2 * (1 - pop)}deg)` : 'none',
					}}>
						{w}
					</span>
				))}
				{g.emoji && (
					<span style={{fontSize: size * 1.1, lineHeight: 1, display: 'inline-block',
						transform: `scale(${emojiIn}) translateY(${(1 - emojiIn) * size * 0.4}px)`}}>
						{g.emoji}
					</span>
				)}
			</div>
		</AbsoluteFill>
	);
};
