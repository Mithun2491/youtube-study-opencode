<div align="center">

# 🎓 YouTube Study Agent

**Paste a YouTube link ➜ get clean, structured study notes ✨**

![Python](https://img.shields.io/badge/Python-3-3776AB?style=flat-square&logo=python&logoColor=white)
![yt-dlp](https://img.shields.io/badge/captions-yt--dlp-red?style=flat-square)
![OpenRouter](https://img.shields.io/badge/AI-OpenRouter-6D5BFF?style=flat-square)
![Platform](https://img.shields.io/badge/Windows-11-0078D4?style=flat-square&logo=windows&logoColor=white)
![Status](https://img.shields.io/badge/status-in%20progress-orange?style=flat-square)

*Small. Local. Honest about what it can and cannot see.* 🔍

</div>

---

## 🚀 What it does

You give it a YouTube URL. It reads the video's captions, sends them to an AI model of your choice, and saves a study guide you can read, edit and keep.

```text
🔗 YouTube URL  ➜  📝 captions  ➜  🤖 AI notes  ➜  📘 study guide (Markdown)
```

Each guide includes:

- 🧭 Overview and learning objectives
- 📖 Detailed explanations and terminology
- 💡 Practical examples and common pitfalls
- ❓ 10 interview questions with answers
- ⚡ Revision sheet and key takeaways

---

## ⚙️ How it works

| Step | What happens |
|:----:|--------------|
| 1️⃣ | Reads video metadata with yt-dlp |
| 2️⃣ | Loads English captions (the video itself is not downloaded) |
| 3️⃣ | Extracts frames, only if you give it a local video file |
| 4️⃣ | Sends the transcript to the AI in chunks |
| 5️⃣ | Merges everything into one final study guide |

📱 YouTube Shorts links are converted to normal watch links automatically.

---

## ⚡ Quick start (Windows, PowerShell)

**1️⃣ Create a virtual environment and install the two packages**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install requests yt-dlp
```

**2️⃣ Add your own key** 🔑

```powershell
Copy-Item .env.example .env
notepad .env
```

Fill in your OpenRouter key. The `.env` file is ignored by git and is never uploaded.

**3️⃣ Run it** ▶️

```powershell
python scripts\study.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Your notes appear here:

```text
study-notes/
  VIDEO_ID/
    note.md          <- the study guide
    transcript.md    <- timestamped transcript
    metadata.json    <- title, channel, duration
```

---

## 🖼️ Optional: analyze real video frames

Frames are only used when you provide a local video file. Install ffmpeg first, then:

```powershell
python scripts\study.py "URL" --video-file "videos\VIDEO_ID.mp4" --frame-interval 30
```

The header of `note.md` shows how many frames were sent to the model.

---

## 🧾 Honest limits

This tool is built to say what it did, and not more.

- 📝 It uses **captions only**. It does not watch the video.
- 🖼️ It sees images **only** if you pass `--video-file` and the model supports images.
- 🏷️ If there are no captions, the note is built from the **title and description only**, and the note says so at the top.
- 🚫 It does **not** control the YouTube player or skip ads.
- 🎯 The quality of the notes depends on the AI model you choose.

---

## 🛠️ Troubleshooting

| Message | What it means | What to do |
|---------|---------------|------------|
| `HTTP 429` 🚦 | YouTube is rate-limiting caption requests | Wait 30-60 minutes or switch network. The tool does not retry on purpose. |
| `This video is not available` 🔒 | Private, deleted or region-blocked | Try another video |
| `empty answer (finish_reason: length)` 🧠 | The model used all its tokens thinking | Raise `max_tokens` or change `OPENAI_MODEL` in `.env` |
| `Configure OPENAI_API_KEY...` 🔑 | `.env` is missing or empty | Check your `.env` file |

---

## 🔐 Privacy and safety

- 🔑 Your API key stays in `.env` on your own computer.
- 🙈 `.env`, `.venv`, `study-notes/` and downloaded videos are excluded from git.
- ☁️ Captions are sent to the AI provider you configure. Do not use it on content you are not allowed to share.

---

## 🗺️ Roadmap

These are plans, not finished features.

- [ ] 📊 Local web app: dashboard and video library
- [ ] ✍️ Editable rich-text note editor
- [ ] 🖼️ Screenshot gallery and Mermaid diagrams
- [ ] 📰 Blog-style reading page
- [ ] 📤 Export to HTML and Markdown

---

## 📄 License

Copyright (c) 2026 Mithun. All rights reserved.
Source is visible for viewing and learning only. Ask the author for permission before copying or reusing it.

---

<div align="center">

Built with ❤️ by [Mithun](https://github.com/Mithun2491)

</div>
