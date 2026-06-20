"""Generación de subtítulos ASS con efecto karaoke (resaltado palabra por palabra)."""

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


def _header(play_w: int, play_h: int, font_size: int, margin_v: int) -> str:
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


def build_karaoke_ass(
    words: list[Word],
    clip_start: float,
    out_path: Path,
    play_w: int = 1080,
    play_h: int = 1920,
    font_size: int = 64,
    margin_v: int = 220,
) -> Path:
    """Genera un .ass karaoke a partir de las palabras del clip.

    Los timestamps de entrada son absolutos respecto al crudo; se rebasan a relativos.
    """
    rel = [
        Word(text=w.text, start=w.start - clip_start, end=w.end - clip_start, speaker=w.speaker)
        for w in words
    ]
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
    content = _header(play_w, play_h, font_size, margin_v) + "\n".join(events) + "\n"
    out_path.write_text(content, encoding="utf-8")
    return out_path
