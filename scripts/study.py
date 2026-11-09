import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import base64
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]

def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-2000:])
    return p.stdout

def normalize_url(url):
    # Turn a Shorts link into a normal watch link
    m = re.search(r"youtube\.com/shorts/([A-Za-z0-9_-]{11})", url)
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    return url

def timestamp(value):
    parts = value.replace(",", ".").split(":")
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = 0, parts[0], parts[1]
    else:
        raise ValueError(value)
    return int(h) * 3600 + int(m) * 60 + float(s)

def fmt(seconds):
    if seconds is None:
        return "untimed"
    seconds = int(seconds)
    return f"{seconds//3600:02}:{(seconds%3600)//60:02}:{seconds%60:02}"

def parse_vtt(path):
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\n\s*\n", raw)
    cues = []
    for block in blocks:
        lines = [x.strip() for x in block.splitlines() if x.strip()]
        index = next((i for i, x in enumerate(lines) if "-->" in x), None)
        if index is None:
            continue
        try:
            start = timestamp(lines[index].split("-->")[0].strip().split()[0])
        except ValueError:
            continue
        text = " ".join(lines[index+1:])
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text and (not cues or cues[-1]["text"] != text):
            cues.append({"start": start, "text": text})
    return cues

def api_call(messages):
    key = os.getenv("OPENAI_API_KEY", "").strip()
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "").strip()
    if not key or not model:
        raise RuntimeError("Configure OPENAI_API_KEY and OPENAI_MODEL in .env")
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 12000
    }).encode()
    req = Request(
        base + "/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json"
        }
    )
    try:
        with urlopen(req, timeout=240) as response:
            data = json.loads(response.read())
    except HTTPError as e:
        raise RuntimeError(f"API error {e.code}: {e.read().decode(errors='replace')[:1000]}")

    # OpenRouter can return HTTP 200 with an error inside the JSON
    if "error" in data:
        err = data["error"]
        msg = err.get("message", err) if isinstance(err, dict) else err
        raise RuntimeError(f"OpenRouter returned an error: {msg}")

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter returned no choices.")

    choice = choices[0]
    content = (choice.get("message") or {}).get("content")

    # Some models return a list of parts instead of a string
    if isinstance(content, list):
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))

    if not content or not content.strip():
        raise RuntimeError(
            f"The model returned an empty answer (finish_reason: {choice.get('finish_reason')}). "
            "If it says 'length', raise max_tokens. Otherwise try again or change OPENAI_MODEL."
        )
    return content.strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--video-file", type=Path)
    parser.add_argument("--transcript", type=Path)
    parser.add_argument("--frame-interval", type=int, default=90)
    args = parser.parse_args()
    args.url = normalize_url(args.url)

    load_env()
    print("[1/5] Reading video metadata...")
    meta = json.loads(run([
        sys.executable, "-m", "yt_dlp",
        "--dump-single-json", "--skip-download", "--no-warnings", args.url
    ]))

    vid = re.sub(r"[^A-Za-z0-9_-]", "_", meta.get("id", "video"))
    out = ROOT / "study-notes" / vid
    out.mkdir(parents=True, exist_ok=True)

    info = {
        "title": meta.get("title"),
        "channel": meta.get("channel") or meta.get("uploader"),
        "url": meta.get("webpage_url", args.url),
        "duration": meta.get("duration")
    }
    (out / "metadata.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    print("[2/5] Loading captions...")
    metadata_only = False
    source = None
    if args.transcript:
        source = args.transcript
    else:
        capdir = out / "_captions"
        capdir.mkdir(exist_ok=True)
        template = str(capdir / "%(id)s.%(ext)s")
        p = subprocess.run([
            sys.executable, "-m", "yt_dlp",
            "--skip-download", "--write-subs", "--write-auto-subs",
            "--sub-langs", "en.*,en", "--sub-format", "vtt/best",
            "--sleep-requests", "2", "--sleep-subtitles", "5",
            "--output", template, args.url
        ], capture_output=True, text=True)
        err = p.stderr or ""
        candidates = sorted(capdir.glob("*.vtt"))
        if candidates:
            source = candidates[0]
        elif "429" in err or "Too Many Requests" in err:
            raise RuntimeError(
                "YouTube is rate-limiting caption requests (HTTP 429). "
                "Nothing was processed and no notes were created.\n"
                "    Wait 30-60 minutes (or switch network), then try again. "
                "I am not retrying, because that makes the limit last longer."
            )
        elif p.returncode:
            raise RuntimeError("Caption download failed:\n" + err[-800:])
        else:
            metadata_only = True

    if metadata_only:
        desc = (meta.get("description") or "").strip()
        if not desc:
            raise RuntimeError(
                "No captions found and the video has no description. "
                "Nothing to build notes from. Supply --transcript FILE."
            )
        print("    No captions found. Using title + description only.")
        cues = [{"start": None,
                 "text": f"Title: {info['title']}\n\nDescription:\n{desc}"}]
    elif source.suffix.lower() in (".vtt", ".srt"):
        cues = parse_vtt(source)
    else:
        cues = [{"start": None, "text": source.read_text(encoding="utf-8-sig")}]

    if not cues:
        raise RuntimeError("Transcript is empty.")

    transcript = "\n".join(
        f"[{fmt(c['start'])}] {c['text']}" if c["start"] is not None else c["text"]
        for c in cues
    )
    (out / "transcript.md").write_text("# Transcript\n\n" + transcript, encoding="utf-8")

    frames = []
    if args.video_file:
        print("[3/5] Extracting visual frames...")
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg was not found on PATH, so frames cannot be extracted.")
        frame_dir = out / "frames"
        frame_dir.mkdir(exist_ok=True)
        pattern = str(frame_dir / "frame_%04d.jpg")
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", str(args.video_file.resolve()),
            "-vf", f"fps=1/{args.frame_interval},scale='min(1280,iw)':-2",
            "-q:v", "4", pattern
        ])
        frames = sorted(frame_dir.glob("*.jpg"))
    else:
        print("[3/5] Visual frames skipped (no --video-file given).")

    print("[4/5] Analyzing transcript...")
    prefix = ""
    if metadata_only:
        prefix = (
            "NOTE: This is only the video's title and description, NOT its transcript. "
            "State this clearly and do not claim to know what is said or shown in the video.\n\n"
        )
    chunks = [transcript[i:i+9000] for i in range(0, len(transcript), 9000)]
    notes = []
    for i, chunk in enumerate(chunks, 1):
        content = [{
            "type": "text",
            "text": (
                prefix +
                "Create detailed technical study notes from this transcript section. "
                "Preserve timestamps. Explain concepts, extract supported code and commands, "
                "and do not invent facts.\n\n" + chunk
            )
        }]
        if frames:
            for frame in frames[(i-1)*4:i*4]:
                image_data = base64.b64encode(frame.read_bytes()).decode()
                content.append({"type": "image_url", "image_url": {
                    "url": "data:image/jpeg;base64," + image_data
                }})
        notes.append(api_call([
            {"role": "system", "content": "You are a careful technical educator."},
            {"role": "user", "content": content}
        ]))

    print("[5/5] Creating final study guide...")
    final = api_call([
        {"role": "system", "content": "Create evidence-based Markdown study guides."},
        {"role": "user", "content":
            prefix +
            "Consolidate these notes. Include overview, learning objectives, "
            "detailed explanations, terminology, practical examples, pitfalls, "
            "10 interview questions with answers, revision sheet and key takeaways. "
            "Separate visual observations from transcript content. Do not invent facts.\n\n"
            + "\n\n".join(notes)}
    ])

    source_line = (
        "- Source: TITLE + DESCRIPTION ONLY (no captions found; not based on the video content)\n"
        if metadata_only else "- Source: captions/transcript\n"
    )
    header = (
        f"# {info['title']}\n\n"
        f"- Channel: {info['channel']}\n"
        f"- URL: {info['url']}\n"
        f"{source_line}"
        f"- Visual frames analyzed: {len(frames)}\n\n---\n\n"
    )
    (out / "note.md").write_text(header + final, encoding="utf-8")
    print(f"\nSUCCESS! Notes saved to: {out}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)