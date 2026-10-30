// Two general graphics a plan can put on any shot (gfx={"use": "Pop", "text": "SEND IT 🚀"}), and the examples to
// copy when writing a film's own: Pop (TikTok-style words that pop in on the beat) and Callout (a ring drawn
// around someone, with a label).
import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {FILM_FONT, GfxProps, beatAt, easeOut, exit, pop, pulse, unit, useFilmFont} from './lib';

export type PopProps = GfxProps & {
	text: string;
	y?: number;            // vertical centre, 0-1 of the frame (default 0.5; shorts: keep away from the bottom UI)
	size?: number;         // text height, fraction of the 16:9 frame height (default 0.13)
	color?: string;
	hi?: number[];         // indices of the words in the accent colour (default: the last word)
	tilt?: number;         // degrees (default -4)
	onBeat?: boolean;      // one word per beat (default true when beats are close enough, else every 0.12 s)
};

// words pop in one by one (overshooting spring, a little rotation), the whole line bumps on every beat, then shrinks away
export const Pop: React.FC<PopProps> = (p) => {
	useFilmFont();
	const frame = useCurrentFrame();
	const {width: W, height: H, fps} = p;
	const U = unit(W, H), t = frame / fps;
	const words = p.text.split(/\s+/).filter(Boolean);
	const hi = p.hi ?? [words.length - 1];
	const ahead = p.beats.filter((b) => b >= -0.05);
	const beatGap = ahead.length > 1 ? ahead[1] - ahead[0] : 1;
	const onBeat = p.onBeat ?? beatGap < 0.6;
	const start = (i: number) => (onBeat && ahead[i] !== undefined ? Math.max(0, ahead[i]) : i * 0.12);
	const out = exit(frame, p, 0.22);
	const bump = 1 + 0.06 * pulse(t, p.beats, 0.12) * (beatAt(t, p.beats) >= 0 ? 1 : 0);
	const fs = U * (p.size ?? 0.13);
	return (
		<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
			<div style={{position: 'absolute', top: H * (p.y ?? 0.5), left: 0, right: 0, transform: `translateY(-50%) rotate(${p.tilt ?? -4}deg) scale(${bump * (1 - out)})`,
				display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: `0 ${fs * 0.28}px`, padding: `0 ${W * 0.06}px`, opacity: 1 - out}}>
				{words.map((w, i) => {
					const k = pop(frame, fps, start(i));
					return (
						<span key={i} style={{fontFamily: FILM_FONT, fontWeight: 800, fontSize: fs, lineHeight: 1.05, display: 'inline-block',
							color: hi.includes(i) ? p.accent : p.color ?? 'white', textTransform: 'uppercase',
							WebkitTextStroke: `${fs * 0.045}px black`, paintOrder: 'stroke fill',
							textShadow: `0 ${fs * 0.06}px 0 rgba(0,0,0,0.9)`,
							opacity: Math.min(1, k * 3), transform: `scale(${k}) rotate(${(1 - k) * (i % 2 ? 14 : -14)}deg)`}}>
							{w}
						</span>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};

export type CalloutProps = GfxProps & {
	x: number; y: number;  // centre of the subject, 0-1 of the frame
	r?: number;            // ring radius, fraction of the 16:9 frame height (default 0.09)
	text?: string;
	side?: 'left' | 'right';
};

// a hand-drawn-looking ring around the subject, then a line out to the label
export const Callout: React.FC<CalloutProps> = (p) => {
	useFilmFont();
	const frame = useCurrentFrame();
	const {width: W, height: H, fps} = p;
	const U = unit(W, H), t = frame / fps;
	const cx = p.x * W, cy = p.y * H, r = U * (p.r ?? 0.09);
	const side = p.side ?? (p.x > 0.6 ? 'left' : 'right');
	const ring = easeOut(t / 0.45), line = easeOut((t - 0.35) / 0.25), label = pop(frame, fps, 0.5);
	const out = exit(frame, p, 0.2);
	const circ = 2 * Math.PI * r * 1.08;
	const dir = side === 'right' ? 1 : -1;
	const lx = cx + dir * r * 0.9, ly = cy - r * 0.9, ex = lx + dir * U * 0.12, ey = ly - U * 0.08;
	return (
		<AbsoluteFill style={{opacity: 1 - out}}>
			<svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
				<ellipse cx={cx} cy={cy} rx={r * 1.08} ry={r} fill="none" stroke={p.accent} strokeWidth={U * 0.008} strokeLinecap="round"
					strokeDasharray={circ} strokeDashoffset={circ * (1 - ring)} transform={`rotate(-80 ${cx} ${cy})`}
					style={{filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.6))'}} />
				<line x1={lx} y1={ly} x2={lx + (ex - lx) * line} y2={ly + (ey - ly) * line} stroke={p.accent} strokeWidth={U * 0.006}
					strokeLinecap="round" style={{filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.6))'}} />
			</svg>
			{p.text && (
				<div style={{position: 'absolute', top: ey, left: side === 'right' ? ex + U * 0.012 : undefined,
					right: side === 'left' ? W - ex + U * 0.012 : undefined, transform: `translateY(-50%) scale(${label})`,
					transformOrigin: side === 'right' ? 'left center' : 'right center',
					fontFamily: FILM_FONT, fontWeight: 700, fontSize: U * 0.05, color: 'white', whiteSpace: 'nowrap',
					textShadow: '0 2px 8px rgba(0,0,0,0.8)'}}>
					{p.text}
				</div>
			)}
		</AbsoluteFill>
	);
};
