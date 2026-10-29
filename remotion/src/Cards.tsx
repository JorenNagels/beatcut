// End card (credits) and lower third (a name or place on a shot).
import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame} from 'remotion';
import {FILM_FONT, Size, clamp01, easeOut, unit, useFilmFont} from './common';

export type EndCardProps = Size & {title: string; lines: string[]};

// the film title letter by letter, then the small lines; same layout as the drawtext credits
export const EndCard: React.FC<EndCardProps> = ({title, lines, width: W, height: H, fps}) => {
	useFilmFont();
	const frame = useCurrentFrame();
	const U = unit(W, H);
	const t = frame / fps;
	const letters = title.toUpperCase().split('');
	return (
		<AbsoluteFill>
			<div style={{position: 'absolute', top: H * 0.42, width: '100%', display: 'flex', justifyContent: 'center'}}>
				{letters.map((c, i) => {
					const k = easeOut((t - 0.6 - i * 0.04) / 0.5);
					return (
						<span key={i} style={{fontFamily: FILM_FONT, fontWeight: 600, fontSize: U * 0.046, color: 'white', whiteSpace: 'pre',
							letterSpacing: '0.45em', opacity: k, transform: `translateY(${(1 - k) * U * 0.03}px)`, display: 'inline-block',
							textShadow: '2px 2px 0 rgba(0,0,0,0.55)'}}>
							{c}
						</span>
					);
				})}
			</div>
			{lines.map((l, k) => {
				const a = easeOut((t - 0.6 - letters.length * 0.04 - 0.3 - 0.25 * k) / 0.6);
				return (
					<div key={k} style={{position: 'absolute', top: H * (0.54 + 0.05 * k), width: '100%', textAlign: 'center', opacity: a,
						fontFamily: FILM_FONT, fontWeight: 400, fontSize: U * 0.026, color: 'white', textShadow: '2px 2px 0 rgba(0,0,0,0.55)'}}>
						{l}
					</div>
				);
			})}
		</AbsoluteFill>
	);
};

export type LowerThirdProps = Size & {text: string; sub?: string; accent: string};

// a bar slides in from the left, the text is revealed behind it, everything slides out at the end
export const LowerThird: React.FC<LowerThirdProps> = ({text, sub, accent, width: W, height: H, fps, frames}) => {
	useFilmFont();
	const frame = useCurrentFrame();
	const U = unit(W, H);
	const inK = spring({frame, fps, config: {damping: 14, stiffness: 160}});
	const outK = clamp01((frame - (frames - fps * 0.4)) / (fps * 0.4));
	const x = U * 0.06 - outK * W * 0.6;
	const portrait = H > W;
	return (
		<AbsoluteFill>
			<div style={{position: 'absolute', left: x, bottom: H * (portrait ? 0.34 : 0.14), display: 'flex', alignItems: 'stretch'}}>
				<div style={{width: U * 0.012, background: accent, transform: `scaleY(${inK})`}} />
				<div style={{paddingLeft: U * 0.02, clipPath: `inset(0 ${(1 - inK) * 100}% 0 0)`}}>
					<div style={{fontFamily: FILM_FONT, fontWeight: 700, fontSize: U * 0.055, color: 'white', lineHeight: 1.1,
						textShadow: '0 2px 10px rgba(0,0,0,0.6)'}}>{text}</div>
					{sub && <div style={{fontFamily: FILM_FONT, fontWeight: 400, fontSize: U * 0.03, color: 'rgba(255,255,255,0.85)',
						letterSpacing: '0.2em', textTransform: 'uppercase', textShadow: '0 2px 8px rgba(0,0,0,0.6)'}}>{sub}</div>}
				</div>
			</div>
		</AbsoluteFill>
	);
};
