"""Generación de subtítulos ASS: karaoke (educativo) y social (Shorts/Reels)."""

from __future__ import annotations

from pathlib import Path

from .models import Word

# Colores en formato ASS (&HAABBGGRR&)
_WHITE = "&H00FFFFFF"
_HIGHLIGHT = "&H0000D7FF"   # amarillo/dorado (BGR)
_OUTLINE = "&H00000000"


def _fmt_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs == 100:
        cs = 0
        s += 1
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _group_lines(words: list[Word], max_chars: int = 22) -> list[list[Word]]:
    lines: list[list[Word]] = []
    cur: list[Word] = []
    cur_len = 0
    for w in words:
        wl = len(w.text.strip())
        if cur and (cur_len + wl > max_chars or cur[-1].text.strip().endswith((".", "?", "!"))):
            lines.append(cur)
            cur, cur_len = [], 0
        cur.append(w)
        cur_len += wl + 1
    if cur:
        lines.append(cur)
    return lines


def _group_lines_by_words(words: list[Word], max_words: int = 5) -> list[list[Word]]:
    lines: list[list[Word]] = []
    cur: list[Word] = []
    for w in words:
        cur.append(w)
        ends = w.text.strip().endswith((".", "?", "!"))
        if len(cur) >= max_words or ends:
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    return lines


def _rel_words(words: list[Word], clip_start: float) -> list[Word]:
    return [
        Word(text=w.text, start=w.start - clip_start, end=w.end - clip_start, speaker=w.speaker)
        for w in words
    ]


def _karaoke_header(play_w: int, play_h: int, font_size: int, margin_v: int) -> str:
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_w}
PlayResY: {play_h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Montserrat,{font_size},{_HIGHLIGHT},{_WHITE},{_OUTLINE},&H64000000,-1,0,0,0,100,100,0,0,1,4,2,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _social_header(play_w: int, play_h: int, font_size: int, margin_v: int) -> str:
    # Anton si esta instalada; libass hace fallback a Arial Black / sans bold.
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_w}
PlayResY: {play_h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Social,Anton,{font_size},{_WHITE},{_WHITE},{_OUTLINE},&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def build_karaoke_ass(
    words: list[Word],
    clip_start: float,
    out_path: Path,
    play_w: int = 1080,
    play_h: int = 1920,
    font_size: int = 64,
    margin_v: int = 220,
) -> Path:
    """Genera un .ass karaoke a partir de las palabras del clip."""
    rel = _rel_words(words, clip_start)
    lines = _group_lines(rel)

    events: list[str] = []
    for line in lines:
        if not line:
            continue
        start = _fmt_time(line[0].start)
        end = _fmt_time(line[-1].end)
        parts: list[str] = []
        for w in line:
            dur_cs = max(1, int(round((w.end - w.start) * 100)))
            parts.append(f"{{\\k{dur_cs}}}{w.text.strip()} ")
        text = "".join(parts).strip()
        events.append(f"Dialogue: 0,{start},{end},Karaoke,,0,0,0,,{text}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = _karaoke_header(play_w, play_h, font_size, margin_v) + "\n".join(events) + "\n"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def build_social_ass(
    words: list[Word],
    clip_start: float,
    out_path: Path,
    play_w: int = 1080,
    play_h: int = 1920,
    font_size: int = 72,
    margin_v: int = 180,
    max_words: int = 5,
) -> Path:
    """Subtitulos estilo Shorts: lineas cortas, bold, sin karaoke."""
    rel = _rel_words(words, clip_start)
    lines = _group_lines_by_words(rel, max_words=max_words)

    events: list[str] = []
    for line in lines:
        if not line:
            continue
        start = _fmt_time(line[0].start)
        end = _fmt_time(line[-1].end)
        text = " ".join(w.text.strip() for w in line)
        events.append(f"Dialogue: 0,{start},{end},Social,,0,0,0,,{text}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = _social_header(play_w, play_h, font_size, margin_v) + "\n".join(events) + "\n"
    out_path.write_text(content, encoding="utf-8")
    return out_path


def build_ass(
    words: list[Word],
    clip_start: float,
    out_path: Path,
    *,
    style: str = "karaoke",
    play_w: int = 1080,
    play_h: int = 1920,
    font_size: int | None = None,
    margin_v: int | None = None,
    max_words: int = 5,
) -> Path:
    """Dispatcher: style=karaoke|social."""
    if style == "social":
        return build_social_ass(
            words,
            clip_start,
            out_path,
            play_w=play_w,
            play_h=play_h,
            font_size=font_size or (72 if play_h >= play_w else 56),
            margin_v=margin_v or (180 if play_h >= play_w else 90),
            max_words=max_words,
        )
    return build_karaoke_ass(
        words,
        clip_start,
        out_path,
        play_w=play_w,
        play_h=play_h,
        font_size=font_size or (64 if play_h >= play_w else 48),
        margin_v=margin_v or (220 if play_h >= play_w else 80),
    )


STYLE_META: dict[str, dict[str, str]] = {
    "karaoke": {"style_label": "Karaoke (educativo)", "font": "Montserrat"},
    "social": {"style_label": "Social (Shorts/Reels)", "font": "Anton"},
}


def sample_caption_lines(
    words: list[Word],
    clip_start: float,
    *,
    style: str = "karaoke",
    max_words: int = 5,
    max_lines: int = 2,
) -> list[str]:
    """Primeras líneas de subtítulo como texto plano (sin ASS completo)."""
    rel = _rel_words(words, clip_start)
    if style == "social":
        groups = _group_lines_by_words(rel, max_words=max_words)
    else:
        groups = _group_lines(rel)
    lines: list[str] = []
    for group in groups[:max_lines]:
        if not group:
            continue
        lines.append(" ".join(w.text.strip() for w in group))
    return lines


def caption_preview_samples(
    words: list[Word],
    clip_start: float,
    *,
    caption_style: str = "karaoke",
    max_words: int = 5,
    max_lines: int = 2,
) -> list[dict[str, object]]:
    """Muestras livianas según render_prefs.caption_style (karaoke | social | both)."""
    presets = (
        ["karaoke", "social"]
        if caption_style == "both"
        else ["social"] if caption_style == "social" else ["karaoke"]
    )
    out: list[dict[str, object]] = []
    for preset in presets:
        meta = STYLE_META[preset]
        out.append(
            {
                "style": preset,
                "style_label": meta["style_label"],
                "font": meta["font"],
                "sample_lines": sample_caption_lines(
                    words,
                    clip_start,
                    style=preset,
                    max_words=max_words,
                    max_lines=max_lines,
                ),
            }
        )
    return out
