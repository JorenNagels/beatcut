// Kinetic title, 8 beats long, in five styles (event.yaml style.title_style):
//   slam         white flash, BIG word slams in with RGB split, sub wipes in (beat 2), tag pops (beat 4),
//                outline flip (beat 6), glitch-out (beat 7.5)  - the Python 16_title look, smoother
//   minimal      letters settle from wide spacing, a thin line draws, sub fades up; quiet fade out
//   handwritten  marker-pen word written left to right, underline drawn, tag sticker
//   glitch       constant RGB jitter, slice glitches on every beat, typed sub line, scanlines
//   vhs          VT323 camcorder look: PLAY / counter, scanlines, colour fringing, static at the end
import React from 'react';
import {AbsoluteFill, random, useCurrentFrame} from 'remotion';
import {loadFont as loadMarker} from '@remotion/google-fonts/PermanentMarker';
import {loadFont as loadVT} from '@remotion/google-fonts/VT323';
import {FILM_FONT, Full, Size, clamp01, easeOut, unit, useFilmFont} from './common';

const marker = loadMarker().fontFamily;
const vt = loadVT().fontFamily;

export type TitleProps = Size & {big: string; sub: string; tag: string; bpm: number; style: string};

const bigSize = (U: number, big: string) => U * 0.3 * Math.min(1, 5 / Math.max(5, big.length));

export const Title: React.FC<TitleProps> = (p) => {
	useFilmFont();
	const frame = useCurrentFrame();
	const t = frame / p.fps;
	const beat = 60 / p.bpm;
	const b = t / beat;
	const U = unit(p.width, p.height);
	const S = {slam: Slam, minimal: Minimal, handwritten: Handwritten, glitch: Glitch, vhs: Vhs}[p.style] || Slam;
	return <S {...p} t={t} b={b} beat={beat} U={U} frame={frame} />;
};

type Inner = TitleProps & {t: number; b: number; beat: number; U: number; frame: number};

const Word: React.FC<{text: string; size: number; color?: string; outline?: number; font?: string; spacing?: string; style?: React.CSSProperties}> = ({
	text, size, color = 'white', outline = 0, font = FILM_FONT, spacing = '0.15em', style,
}) => (
	<div
		style={{
			fontFamily: font, fontWeight: 700, fontSize: size, lineHeight: 1, letterSpacing: spacing, whiteSpace: 'nowrap',
			color: outline ? 'transparent' : color, WebkitTextStroke: outline ? `${outline}px ${color}` : undefined, ...style,
		}}
	>
		{text}
	</div>
);

// centred at (cx, cy) with a scale
const At: React.FC<{x: number; y: number; scale?: number; rotate?: number; children: React.ReactNode; style?: React.CSSProperties}> = ({
	x, y, scale = 1, rotate = 0, children, style,
}) => (
	<div style={{position: 'absolute', left: x, top: y, transform: `translate(-50%, -50%) scale(${scale}) rotate(${rotate}deg)`, ...style}}>
		{children}
	</div>
);

// horizontal slices of a layer shifted sideways: the glitch-out
const Slices: React.FC<{seed: number; W: number; H: number; children: React.ReactNode}> = ({seed, W, H, children}) => (
	<>
		{Array.from({length: 9}).map((_, i) => {
			const y0 = random(`y${seed}-${i}`) * H;
			const h = 8 + random(`h${seed}-${i}`) * H * 0.06;
			const dx = (random(`x${seed}-${i}`) - 0.5) * W * 0.16;
			return (
				<Full key={i} style={{clipPath: `inset(${y0}px 0 ${Math.max(0, H - y0 - h)}px 0)`, transform: `translateX(${dx}px)`}}>
					{children}
				</Full>
			);
		})}
	</>
);

const Slam: React.FC<Inner> = ({width: W, height: H, big, sub, tag, t, b, beat, U}) => {
	if (b >= 7.85) return null;
	const k = easeOut(t / 0.16);
	const shake = b % 1 < 0.12 ? [(random(`sx${Math.floor(b)}`) - 0.5) * 12 * (U / 1080), (random(`sy${Math.floor(b)}`) - 0.5) * 12 * (U / 1080)] : [0, 0];
	const cx = W / 2 + shake[0], cy = H * 0.44 + shake[1];
	const size = bigSize(U, big), scale = 1.7 - 0.7 * k;
	const split = (1 - k) * U * 0.03 + (b % 1 < 0.1 ? U * 0.006 : 0);
	const outline = b >= 6 && b < 7 ? Math.max(2, size / 40) : 0;
	const pSub = easeOut(((b - 2) * beat) / 0.14);
	const pTag = ((b - 4) * beat) / 0.18;
	const tagScale = pTag < 1 ? 1 + 0.35 * Math.exp(-6 * pTag) * Math.cos(10 * pTag) : 1;
	const layer = (
		<>
			{split > 0.5 && (
				<>
					<At x={cx - split} y={cy} scale={scale} style={{opacity: 0.75, mixBlendMode: 'screen'}}><Word text={big.toUpperCase()} size={size} color="rgb(255,40,60)" outline={outline} /></At>
					<At x={cx + split} y={cy} scale={scale} style={{opacity: 0.75, mixBlendMode: 'screen'}}><Word text={big.toUpperCase()} size={size} color="rgb(40,220,255)" outline={outline} /></At>
				</>
			)}
			<At x={cx} y={cy} scale={scale} style={{opacity: clamp01(t / 0.05)}}><Word text={big.toUpperCase()} size={size} outline={outline} /></At>
			{b >= 2 && sub && (
				<At x={cx} y={cy + size * 0.8} style={{clipPath: `inset(0 ${(1 - pSub) * 100}% 0 0)`}}>
					<Word text={sub.toUpperCase()} size={U * 0.055} spacing="0.5em" style={{fontWeight: 600}} />
				</At>
			)}
			{b >= 4 && tag && (
				<div style={{position: 'absolute', right: W / 2 - size * big.length * 0.33 - shake[0], top: cy - size * 0.5 - U * 0.1 + shake[1],
					transform: `scale(${tagScale})`, transformOrigin: 'right bottom', background: 'white', padding: `${U * 0.012}px ${U * 0.025}px`}}>
					<Word text={tag} size={U * 0.06} color="rgb(15,15,15)" spacing="0.05em" />
				</div>
			)}
		</>
	);
	return (
		<AbsoluteFill style={{background: 'rgba(0,0,0,0.27)'}}>
			{b >= 7.5 ? <Slices seed={Math.floor(t * 30)} W={W} H={H}>{layer}</Slices> : layer}
			{t < 0.1 && <AbsoluteFill style={{background: 'white', opacity: 0.92 * (1 - t / 0.1)}} />}
		</AbsoluteFill>
	);
};

const Minimal: React.FC<Inner> = ({width: W, height: H, big, sub, tag, b, U}) => {
	const out = 1 - clamp01((b - 7.4) / 0.6);
	const size = bigSize(U, big) * 0.8;
	const k = easeOut(b / 1.2);
	return (
		<AbsoluteFill style={{background: `rgba(0,0,0,${0.2 * out})`, opacity: out}}>
			<At x={W / 2} y={H * 0.45} style={{opacity: k}}>
				<Word text={big.toUpperCase()} size={size} spacing={`${0.6 - 0.35 * k}em`} style={{fontWeight: 300}} />
			</At>
			<div style={{position: 'absolute', left: W / 2, top: H * 0.45 + size * 0.62, height: Math.max(2, U * 0.004), background: 'white',
				width: W * 0.36 * easeOut(b - 1), transform: 'translateX(-50%)'}} />
			{sub && (
				<At x={W / 2} y={H * 0.45 + size * 0.85 + (1 - easeOut(b - 2)) * U * 0.03} style={{opacity: easeOut(b - 2)}}>
					<Word text={sub.toUpperCase()} size={U * 0.045} spacing="0.6em" style={{fontWeight: 400}} />
				</At>
			)}
			{tag && (
				<At x={W / 2} y={H * 0.45 - size * 0.75} style={{opacity: easeOut(b - 4)}}>
					<Word text={tag} size={U * 0.035} spacing="0.4em" style={{fontWeight: 400}} />
				</At>
			)}
		</AbsoluteFill>
	);
};

const Handwritten: React.FC<Inner> = ({width: W, height: H, big, sub, tag, b, U}) => {
	const out = 1 - clamp01((b - 7.5) / 0.5);
	const size = bigSize(U, big) * 0.95;
	const write = clamp01(b / 1.6);
	const line = clamp01((b - 2) / 0.8);
	const tagK = b >= 4 ? 1 + 0.3 * Math.exp(-5 * (b - 4)) * Math.cos(9 * (b - 4)) : 0;
	const lw = Math.min(W * 0.8, size * big.length * 0.62);
	return (
		<AbsoluteFill style={{background: `rgba(0,0,0,${0.22 * out})`, opacity: out}}>
			<At x={W / 2} y={H * 0.42} rotate={-4} style={{clipPath: `inset(-20% ${(1 - write) * 100}% -20% -5%)`}}>
				<Word text={big} size={size} font={marker} spacing="0.02em" style={{fontWeight: 400, textShadow: '0 4px 18px rgba(0,0,0,0.45)'}} />
			</At>
			<svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
				<path d={`M ${W / 2 - lw / 2} ${H * 0.42 + size * 0.55} q ${lw / 2} ${-U * 0.03} ${lw} ${U * 0.01}`}
					stroke="white" strokeWidth={U * 0.012} fill="none" strokeLinecap="round"
					strokeDasharray={lw * 1.1} strokeDashoffset={lw * 1.1 * (1 - line)} />
			</svg>
			{sub && (
				<At x={W / 2} y={H * 0.42 + size * 0.85} style={{opacity: easeOut((b - 3) / 0.6)}}>
					<Word text={sub.toUpperCase()} size={U * 0.05} spacing="0.35em" style={{fontWeight: 500}} />
				</At>
			)}
			{tag && b >= 4 && (
				<At x={W / 2 + lw * 0.42} y={H * 0.42 - size * 0.62} scale={tagK} rotate={8}
					style={{background: 'rgb(255,214,0)', padding: `${U * 0.01}px ${U * 0.022}px`, boxShadow: '0 6px 16px rgba(0,0,0,0.35)'}}>
					<Word text={tag} size={U * 0.05} font={marker} color="rgb(20,20,20)" spacing="0.02em" style={{fontWeight: 400}} />
				</At>
			)}
		</AbsoluteFill>
	);
};

const Glitch: React.FC<Inner> = ({width: W, height: H, big, sub, tag, t, b, U, frame}) => {
	if (b >= 7.9) return null;
	const size = bigSize(U, big);
	const hit = b % 1 < 0.1;                                  // strong glitch on every beat
	const j = (s: string) => (random(`${s}${frame}`) - 0.5) * U * (hit ? 0.03 : 0.006);
	const typed = sub ? sub.toUpperCase().slice(0, Math.max(0, Math.floor((b - 2) * 8))) : '';
	const cursor = b >= 2 && Math.floor(t * 4) % 2 === 0 ? '█' : '';
	const layer = (
		<>
			<At x={W / 2 + j('r')} y={H * 0.44 + j('ry')} style={{mixBlendMode: 'screen', opacity: 0.85}}><Word text={big.toUpperCase()} size={size} color="rgb(255,0,80)" /></At>
			<At x={W / 2 + j('c')} y={H * 0.44 + j('cy')} style={{mixBlendMode: 'screen', opacity: 0.85}}><Word text={big.toUpperCase()} size={size} color="rgb(0,240,255)" /></At>
			<At x={W / 2} y={H * 0.44}><Word text={big.toUpperCase()} size={size} /></At>
			{b >= 2 && sub && (
				<At x={W / 2} y={H * 0.44 + size * 0.8}><Word text={typed + cursor} size={U * 0.05} spacing="0.3em" style={{fontFamily: 'Consolas, monospace'}} /></At>
			)}
			{b >= 4 && tag && (Math.floor(frame / 2) % 5 !== 0 || b > 4.6) && (
				<At x={W / 2} y={H * 0.44 - size * 0.72} style={{background: 'white', padding: `0 ${U * 0.02}px`}}>
					<Word text={tag} size={U * 0.05} color="black" spacing="0.2em" />
				</At>
			)}
		</>
	);
	return (
		<AbsoluteFill style={{background: 'rgba(0,0,0,0.32)'}}>
			{hit || b >= 7.4 ? <Slices seed={frame} W={W} H={H}>{layer}</Slices> : layer}
			<AbsoluteFill style={{background: `repeating-linear-gradient(0deg, rgba(0,0,0,0.18) 0px, rgba(0,0,0,0.18) 1px, transparent 2px, transparent ${Math.max(3, U / 270)}px)`}} />
		</AbsoluteFill>
	);
};

const Vhs: React.FC<Inner> = ({width: W, height: H, big, sub, tag, t, b, U, frame, fps}) => {
	const size = bigSize(U, big) * 1.1;
	const wob = Math.sin(t * 9) * U * 0.004 + (random(`w${Math.floor(frame / 3)}`) - 0.5) * U * 0.004;
	const glow = '0 0 8px rgba(255,255,255,0.6)';
	const secs = Math.floor(frame / fps);
	const band = ((t * 0.35) % 1) * H;
	const staticOut = b >= 7.5;
	return (
		<AbsoluteFill style={{background: 'rgba(10,10,30,0.25)', fontFamily: vt}}>
			{!staticOut && (
				<>
					<div style={{position: 'absolute', left: U * 0.06, top: U * 0.05, fontFamily: vt, fontSize: U * 0.06, color: 'white', textShadow: glow}}>PLAY ▶</div>
					<div style={{position: 'absolute', right: U * 0.06, top: U * 0.05, fontFamily: vt, fontSize: U * 0.06, color: 'white', textShadow: glow}}>
						{tag ? `${tag}  ` : ''}0:00:{String(secs).padStart(2, '0')}
					</div>
					<At x={W / 2 + wob - U * 0.004} y={H * 0.46} style={{opacity: 0.8, mixBlendMode: 'screen'}}><Word text={big.toUpperCase()} size={size} font={vt} color="rgb(255,40,40)" spacing="0.08em" style={{fontWeight: 400}} /></At>
					<At x={W / 2 + wob + U * 0.004} y={H * 0.46} style={{opacity: 0.8, mixBlendMode: 'screen'}}><Word text={big.toUpperCase()} size={size} font={vt} color="rgb(40,120,255)" spacing="0.08em" style={{fontWeight: 400}} /></At>
					<At x={W / 2 + wob} y={H * 0.46}><Word text={big.toUpperCase()} size={size} font={vt} spacing="0.08em" style={{fontWeight: 400, textShadow: glow}} /></At>
					{b >= 2 && sub && (
						<At x={W / 2 + wob} y={H * 0.46 + size * 0.7}><Word text={sub.toUpperCase()} size={U * 0.065} font={vt} spacing="0.3em" style={{fontWeight: 400, textShadow: glow}} /></At>
					)}
					<div style={{position: 'absolute', left: 0, right: 0, top: band, height: U * 0.03, background: 'rgba(255,255,255,0.08)', filter: 'blur(2px)'}} />
				</>
			)}
			{staticOut && (
				<AbsoluteFill style={{opacity: 0.7, background: `repeating-linear-gradient(${random(`n${frame}`) * 180}deg, rgba(255,255,255,0.5) 0px, rgba(0,0,0,0.5) 2px, rgba(128,128,128,0.4) 3px)`}} />
			)}
			<AbsoluteFill style={{background: `repeating-linear-gradient(0deg, rgba(0,0,0,0.22) 0px, rgba(0,0,0,0.22) 1px, transparent 2px, transparent ${Math.max(3, U / 270)}px)`}} />
		</AbsoluteFill>
	);
};
