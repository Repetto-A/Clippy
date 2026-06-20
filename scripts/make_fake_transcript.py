"""Genera un transcript.json sintetico para smoke-testear el pipeline sin ASR real."""

from pathlib import Path

from video_clipper import storage
from video_clipper.config import settings
from video_clipper.models import Transcript, Word
from video_clipper.transcribe import _group_into_segments

TEXT = (
    "Lo mas importante para usar bien la inteligencia artificial es saber lo que queres. "
    "El truco esta en comunicar con claridad el objetivo. "
    "Aca ven un ejemplo concreto de como la gente usa ChatGPT en su dia a dia. "
    "Fijense que la mayoria lo usa para buscar informacion especifica y para aprender. "
    "El error mas comun es pedir cosas vagas y esperar magia. "
    "La clave entonces es darle contexto, ejemplos y un objetivo claro al modelo."
)


def main() -> None:
    tokens = TEXT.split(" ")
    words: list[Word] = []
    t = 2.0
    for tok in tokens:
        dur = 0.18 + min(0.5, len(tok) * 0.05)
        words.append(Word(text=tok, start=round(t, 2), end=round(t + dur, 2)))
        t += dur + 0.06
    segments = _group_into_segments(words)
    transcript = Transcript(language="es", duration=words[-1].end, words=words, segments=segments)

    frag = Path("_analysis/fragmento.mp4")
    workdir = settings.source_workdir(frag)
    workdir.mkdir(parents=True, exist_ok=True)
    storage.save_transcript(transcript, workdir)
    print(f"transcript.json: {len(words)} palabras, {len(segments)} segmentos")


if __name__ == "__main__":
    main()
