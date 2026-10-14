---
name: h3-prompt-writing
description: Write MiniMax H3 video generation prompts for T2VA, I2VA, FL2VA, L2VA, and Ref2VA. Use when rewriting multimodal requests into H3 prompt structures, composing integrated_multimodal_description, overall_soundscape, and non_diegetic_music, aligning keyframes, or defining reference labels for images, videos, and audio.
compatibility: Portable to any agent that can read local files — no external API calls, MiniMax Hub tools, or proprietary runtime required. The agents/openai.yaml file only adds optional ChatGPT/Codex UI metadata; it does not restrict the skill to OpenAI agents.
---

# H3 Prompt Writing

## 🔴 Mandatory Rule: Never Generate Subtitles

**Every prompt you write must be subtitle-free.** This is a hard rule, not a stylistic preference — H3 frequently "paints" the `<d>` dialogue onto the picture as burned-in subtitles (measured: ~1/3 of episodes, ~17% of dialogue lines). Treat any on-screen subtitle as a defect.

| # | Rule | Implementation |
|---|---|---|
| 1 | **Anti-subtitle clause, verbatim, every time** | Copy this exact sentence into the **opening of `summary` or `detailed_description`** — do not paraphrase, translate, shorten, or drop it:<br>`No subtitles, captions, or on-screen text appear at any point in the video.` |
| 2 | **Never stack stronger bans** | A hand-written `ABSOLUTE RULE` block was measured to have **zero or negative effect** (one episode went from 1 subtitle to 3). Stick to the official clause above; extra forbidding language is wasted effort. |
| 3 | **Dialogue is audio only** | `<d>[Language]text</d>` produces sound. Never describe the line as being "displayed as text", "shown at the bottom of the screen", "rendered as a caption", or any on-screen presentation of the words. |
| 4 | **Only physical prop text is allowed** | Text on a signboard / ledger / letter / receipt that physically exists in the scene may be described — but never in subtitle styling (no black bar, no centered outlined caption, no appear/disappear timed to the line). |
| 5 | **Self-check before delivering** | Run `grep -c "No subtitles, captions, or on-screen text appear at any point in the video." <episode>.md`; the count **must be ≥ 1**. If it is 0, the prompt is not finished. |

**Exception — only when the user explicitly asks for subtitles**: still generate the clip subtitle-free and add them afterwards with ffmpeg `drawtext` on the finished video. Never ask the video model to draw them; model-drawn subtitles have uncontrollable font/position/timing and cannot be edited or removed later.

## 🔴 Mandatory Rule: Bind Every Line to a Visible Speaking Mouth

**H3 has no concept of a "speaker."** It generates picture and 32kHz stereo audio in one joint pass and performs no separate speech alignment — it simply **assigns each line to whichever mouth is visible and moving in frame**. Left unspecified, this causes two failure modes:

| Symptom | What H3 does |
|---|---|
| The speaker is the camera (POV / first person) | The speaker is off-screen, so the model attaches the voice to **the one visible face** — that character's mouth moves. A line assigned to an off-screen character is effectively re-assigned to the on-screen subject. |
| Two characters in frame, one line of dialogue | With no listener designated, the line is **split across both visible mouths** — both characters move their mouths. (Named as a known failure mode in the official dialogue guide.) |

| # | Rule | Implementation |
|---|---|---|
| 1 | **Bind every line to a named mouth** | Prefix each line with the subject label and a mouth action: `<Subject 1>'s mouth moves as he says <d>[Chinese]…</d>`. Every other character visible in the same shot gets `mouth stays closed and still`. |
| 2 | **Voice-over / POV must declare closed lips** | Write `says in an off-screen voiceover:` and immediately follow it with `while the visible subject's lips remain completely closed.` Do **not** use verbs such as "explains", "introduces", or "narrates" for a character who is on screen — they imply that character is speaking. |
| 3 | **Prefer solo shots for dialogue** | For any exchange, the safest and default treatment is `a single medium close-up of <Subject 1> alone in frame`, stating that the other person `is not in frame`. This is more reliable than lengthening a two-shot prompt. |
| 4 | **Self-check before delivering** | `grep -c "mouth moves" <episode>.md` must be approximately equal to the number of dialogue lines; `mouth stays closed` must appear at least once in any shot that shares two or more characters. |
| 5 | **Self-check the timing source** | Derive clip length from total line duration (`≈ Σ characters ÷ 5 chars/s + 0.35s per gap + 0.6s opening`), then align shot timestamps to the line landing points — misaligned timestamps move the speaker into the wrong shot and desync mouth and voice. |

**Diagnose in order, one variable at a time**: ① who is speaking → ② are the words correct → ③ is the lip timing correct. Check the audio first, then speaker assignment, then mouth timing.

**Fallback when a POV clip still misbehaves**: generate the shot with no dialogue (ambience only) and add the voice-over in post — an off-screen line never needs lip-sync.

## Workflow

1. Identify the input mode: T2VA, I2VA, FL2VA, L2VA, or full-reference Ref2VA.
2. For base text/keyframe modes, read `references/base-en.txt` and follow its final prompt structure.
3. For full-reference mode, read `references/ref-en.txt` and follow its six-section rewrite format.
4. Preserve the exact field names, section order, labels, and timing notation from the selected guide.

## Base Modes

- T2VA: build the full audiovisual timeline from text.
- I2VA: start from the first frame and develop forward from it.
- FL2VA: describe the continuous path between the first and last frames.
- L2VA: infer a plausible opening and converge to the supplied last frame.

Use `integrated_multimodal_description`, `overall_soundscape`, and `non_diegetic_music` in the order shown in `references/base-en.txt`.

## Full-Reference Mode

Ref2VA rewrites use `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, and `non_diegetic_music` in that order. Reference labels stay consistent across all sections.

Read `references/ref-en.txt` for label rules, retention analysis, and complete examples.

## Output Rules

- **🔴 Subtitles are forbidden by default** — the verbatim anti-subtitle clause must be in every prompt (see Mandatory Rule above). Physical prop text is the only permitted on-screen text.
- **🔴 Every dialogue line is bound to a visible mouth** — `<Subject N>'s mouth moves as …` for the speaker, `mouth stays closed and still` for everyone else in frame (see the speaker-binding Mandatory Rule above).
- Write rewrite sections in English; preserve dialogue, lyrics, and visible scene text in their original language.
- Describe each shot by composition, subjects, environment, actions, camera, sound, and the exact point where referenced content appears.
- Avoid plot summaries, unresolved reference labels, and timing that does not match the requested duration.

## Audio Control Rules

When the video requires **only sound effects and human voice** (no subtitles, no background music):

| Rule | Implementation |
|---|---|
| No subtitles (🔴 mandatory) | All dialogue is audio-only via `<d>[Language]text</d>`. Add the verbatim clause "No subtitles, captions, or on-screen text appear at any point in the video." to the opening of `summary` or `detailed_description`. See the Mandatory Rule section above. |
| No background music | Set `non_diegetic_music` to `N/A`. Do not describe any score or audience-only music. |
| Only sound effects | Put environmental and physical sounds in `overall_soundscape` (wind, footsteps, fabric rustling, crowd murmurs, etc.). |
| Only human voice | All dialogue in `detailed_description` with `<Subject N> (Sx)` speaker IDs and `<d>` tags. No narration or voice-over unless explicitly requested. |

### Audio-Minimal Template

```text
overall_soundscape: [Environmental ambience and physical sound effects only.]

non_diegetic_music: N/A
```

Add this anti-subtitle clause to `summary` or `detailed_description` — **verbatim, every prompt, no exceptions**:
```text
No subtitles, captions, or on-screen text appear at any point in the video.
```
## Tips for Better Results
- Always match the total duration of the description to the requested video length (4–15 seconds).
- Keep reference labels consistent (e.g. `<Picture 1>`, `<Video 1>`, `<Audio 1>`) across every section.
- Prefer concrete visual and audio details over abstract words like "cinematic" or "beautiful".
- When using keyframes (I2VA / FL2VA / L2VA), clearly state how the first and/or last frame connects to the timeline.
- **On-screen text (signboards, ledgers, letters, receipts): spell out four things** — character count, reading order, literal content, and a legibility demand. Proven pattern (10+ instances rendered correctly across one project): `carved down its centre in one vertical column are six large Chinese characters read top to bottom — <literal text> — cut deep into the wood with bold, vigorous, fully legible strokes.` Always follow it with an explicit statement of when the text is fully lit and legible (which shot), so the model knows it must survive the camera move.
- **When the same physical prop carries different faces (front/back, multiple plaques), state in `subject_definitions` exactly which face this prompt uses** and quote its literal characters — do not describe it only by the prop's generic name. A wrong-face mix-up renders cleanly and is invisible until you read the close-up frame (see h3-drama-producer Step 4.1 / Step 10).
- For text of 5+ characters, lock it with a dedicated prop image first (h3-drama-producer Step 5) instead of relying on the video model alone — prompt wording cannot reliably fix long strings.
