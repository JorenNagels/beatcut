# Graphics: a look of its own for every film

Every film gets its own graphics: title, text on moments, running gags, end card. They are written for this film,
not picked from a menu. Graphics are React components rendered by Remotion (`remotion/`, needs
`python install.py --remotion` and Node.js 18+) into one transparent track that the renderer lays over the shots.

## When
After the first preview cut exists (the plan is roughly right) and before the feedback rounds get detailed. Show
the user a proposal first (2-4 lines plus a contact sheet), then build. Recheck after every plan change that moves shots.

## Design the look (before writing code)
Start from the footage and the feel, not from the previous film. Decide:
- **Title**: what it does on the beat, which letters/words, how it leaves. Think about the event: a ski trip can
  drop letters in snow; a festival can be a glitchy poster; a wedding gets slow handwriting; a city trip a
  metro-map line; a birthday confetti and a big number.
- **Moment text** (TikTok-style): one-word reactions on the funniest beats ("NIEEEUW 😂", "SEND IT 🚀"), a callout
  ring around the person who is about to fall, a running gag (a fall counter, a "beers: 4" tally, a day counter).
  Few and well-timed beats many: 3-10 in a 4-minute film, more in a short.
- **Font, accent colour, motion style**: one font family, one accent (`style.accent`), one way things enter and
  leave (pop / slide / type / drop). Keep it consistent.
- **Mute zones**: 9:16 shorts keep text out of the bottom ~20 % and the right edge (app buttons); landscape films
  keep text off faces and inside the letterbox.
Ask the user only what the footage can't answer (inside jokes, names, nicknames, what the running gag is).

## Where things go
- `<event>/graphics/*.tsx`: the film's own components, one or more per file, `export const Name: React.FC<...>`.
  Other files there (png, svg, ttf, ...) are static files: `staticFile('logo.png')`.
- A component named `Title`, `Captions`, `EndCard` or `LowerThird` replaces the built-in one. Or name it
  freely and set `style.title_style: SkiTitle` in event.yaml.
- Placing graphics in `plan.py`:
  ```python
  pins["jump1"] = pin(..., gfx={"use": "Pop", "text": "send it 🚀", "at": 0.3, "dur": 1.6})   # on a shot
  s["gfx"] = [{"use": "Callout", "x": 0.42, "y": 0.4, "text": "Vincent 👀"}, {...}]          # several
  graphic("DayCard", t=tb(40), dur=2.0, day="Day 3", text="Snowstorm")                       # timeline time
  ```
  `at`/`dur` are seconds from the shot's start (dur default: to its end). Everything else goes to the component
  as props. A loop at the end of the plan (over `segs`) is the easy way to do running gags (see the ski event:
  `FallCount` on every crash).

## Writing a component
```tsx
import React from 'react';
import {AbsoluteFill, useCurrentFrame, interpolate, random} from 'remotion';
import {GfxProps, FILM_FONT, useFilmFont, unit, pop, pulse, exit, easeOut} from 'beatcut';

export const DayCard: React.FC<GfxProps & {day: string}> = (p) => {
	useFilmFont();                                   // the film's font (style.font) as FILM_FONT
	const frame = useCurrentFrame(), t = frame / p.fps;
	const U = unit(p.width, p.height);               // size everything in U (16:9-height), never in pixels
	...
};
```
Every component gets: `width, height, fps, frames` (its length), `beats` and `bars` (music times in seconds from
its first frame; negative = before it), `accent`, plus the plan's props. Helpers in `beatcut`
(`remotion/src/lib.ts`): `pop(frame, fps, delay)` springy 0→1, `pulse(t, beats)` 1 on each beat decaying,
`beatAt(t, beats)`, `exit(frame, p)` 0→1 over the end, `easeOut/easeIn/easeInOut`, `clamp01`. Use Remotion's
`random(seed)` (never Math.random: frames render in parallel) and `interpolate`/`spring`. Plain CSS, SVG and
`@remotion/google-fonts` work. Examples to copy: `remotion/src/Text.tsx` (Pop, Callout), `Title.tsx` (five
title styles), `Cards.tsx`, and earlier events' `graphics/` folders.

## Check, then render
```
python beatcut.py <event> gfx list          # every graphic: number, time, component, text
python beatcut.py <event> gfx 3             # 6 stills of graphic 3 over its shots -> render/gfx/check_3.jpg
python beatcut.py <event> gfx               # one still per graphic -> check_all.jpg
```
Look at the sheet (Read the jpg): readable on bright snow/sky? off faces? inside the frame on 9:16? lands on the
beat? Fix and repeat; it takes seconds. Then `14_render preview`; only the shots under changed graphics are
re-rendered. A graphic error (unknown component, TypeScript/React error) stops the render with the message.

## When a graphic is good for every film
Move it into `remotion/src/` (and BUILTIN in `pipeline/graphics_lib.py`) as a built-in, in the repo, with
generic props. Event-specific jokes stay in the event folder.
