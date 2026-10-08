import streamlit as st
import os
import re
import json
import subprocess
import shutil
import urllib.request
import yt_dlp

# Auto-locate ffmpeg
def get_ffmpeg_binary():
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    return "ffmpeg"

FFMPEG_BIN = get_ffmpeg_binary()

# --- PAGE SETUP ---
st.set_page_config(page_title="AI 4K Video Repurposing Studio", page_icon="⚡", layout="wide")
st.title("⚡ AI 4K Video Repurposing Studio")
st.caption("Turn any YouTube video into **5x 4K Viral Shorts (9:16)** OR a **10-Minute 4K Long-Form Mastercut (16:9)**.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎯 Mode Selection")
    app_mode = st.radio("Select Creation Mode", ["5x 4K Viral Shorts (Vertical 9:16)", "10-Minute 4K Long-Form Mastercut (16:9)"])

    st.markdown("---")
    st.header("🤖 AI Engine")
    ai_engine = st.selectbox("AI Engine", ["Smart Algorithmic Engine (Instant)", "Ollama (Local Llama 3 - PC Only)"])
    ollama_model = "llama3.2"
    if "Ollama" in ai_engine:
        ollama_model = st.text_input("Ollama Model", value="llama3.2")

    st.markdown("---")
    st.header("🎬 Render Settings")
    target_duration_min = 10
    if "Shorts" in app_mode:
        render_resolution = st.selectbox("Resolution", ["4K Ultra HD Vertical (2160x3840)", "Full HD Vertical (1080x1920)"])
    else:
        render_resolution = st.selectbox("Resolution", ["4K Ultra HD Widescreen (3840x2160)", "Full HD Widescreen (1920x1080)"])
        target_duration_min = st.slider("Target Duration (Minutes)", 5, 20, 10)

    render_speed = st.selectbox("Encoding Speed", ["Ultra Fast (Recommended)", "Standard Quality"], index=0)

    st.markdown("---")
    with st.expander("🍪 YouTube Cookies (Optional - For Cloud Deploy)"):
        st.caption("Only needed if running on Streamlit Cloud and YouTube blocks the request. Export cookies from your browser using a browser extension like 'Get cookies.txt LOCALLY'.")
        cookie_text = st.text_area("Paste Netscape cookies.txt content", placeholder="# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\t...", height=100, key="cookie_input")

    if shutil.which("ffmpeg") or FFMPEG_BIN != "ffmpeg":
        st.success("✅ FFmpeg: Active")

# --- RESOLUTION MAP ---
res_map = {
    "4K Ultra HD Vertical (2160x3840)": "2160:3840",
    "Full HD Vertical (1080x1920)": "1080:1920",
    "4K Ultra HD Widescreen (3840x2160)": "3840:2160",
    "Full HD Widescreen (1920x1080)": "1920:1080"
}

# --- YT-DLP OPTIONS BUILDER ---
def get_ytdl_opts(extra=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'cachedir': False,
        'ffmpeg_location': FFMPEG_BIN,
        'extractor_args': {
            'youtube': {
                'player_client': ['android_vr', 'tv_embedded', 'ios'],
                'player_skip': ['webpage', 'configs']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    }

    # Only add cookies if user actually pasted valid content
    raw_cookies = st.session_state.get("cookie_input", "").strip()
    if raw_cookies and raw_cookies.startswith("#"):
        cookie_path = os.path.join(os.getcwd(), "yt_cookies.txt")
        with open(cookie_path, "w", encoding="utf-8") as f:
            f.write(raw_cookies)
        opts['cookiefile'] = cookie_path

    if extra:
        opts.update(extra)
    return opts

# --- CORE UTILS ---
def extract_video_id(url):
    for p in [r"(?:v=|\/)([0-9A-Za-z_-]{11})", r"youtu\.be\/([0-9A-Za-z_-]{11})", r"youtube\.com\/shorts\/([0-9A-Za-z_-]{11})"]:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def fetch_transcript(url, video_id):
    """Multi-method transcript extraction."""
    # Method 1: youtube-transcript-api
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        ytt_api = YouTubeTranscriptApi
        if hasattr(ytt_api, 'get_transcript'):
            items = ytt_api.get_transcript(video_id)
            if isinstance(items, list) and len(items) > 5:
                return items, "YouTube Captions API"
        if hasattr(ytt_api, 'list_transcripts'):
            for t in ytt_api.list_transcripts(video_id):
                items = t.fetch()
                if isinstance(items, list) and len(items) > 5:
                    return items, "YouTube Captions API (list)"
    except Exception:
        pass

    # Method 2: yt-dlp subtitle extraction
    try:
        ydl_opts = get_ytdl_opts({
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'en-US', 'en-orig', 'en-GB']
        })
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            all_subs = {}
            all_subs.update(info.get('subtitles', {}) or {})
            all_subs.update(info.get('automatic_captions', {}) or {})

            for lang in ['en', 'en-US', 'en-orig', 'en-GB']:
                if lang in all_subs:
                    formats = all_subs[lang]
                    json_fmt = next((f for f in formats if isinstance(f, dict) and f.get('ext') == 'json3'), None)
                    if json_fmt and 'url' in json_fmt:
                        req = urllib.request.Request(json_fmt['url'], headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=15) as res:
                            data = json.loads(res.read().decode('utf-8'))
                            items = []
                            for ev in data.get('events', []):
                                if isinstance(ev, dict) and 'segs' in ev:
                                    txt = "".join([s.get('utf8', '') for s in ev['segs'] if isinstance(s, dict)]).strip()
                                    if txt and txt != '\n':
                                        items.append({
                                            'start': float(ev.get('tStartMs', 0)) / 1000.0,
                                            'duration': float(ev.get('dDurationMs', 2000)) / 1000.0,
                                            'text': txt
                                        })
                            if len(items) > 5:
                                return items, "yt-dlp Subtitles"

            # Use video info to create approximate transcript
            dur = float(info.get('duration', 600))
            title = info.get('title', 'Video')
            desc = info.get('description', '') or ''
            sentences = [s.strip() for s in re.split(r'[.\n]', desc) if len(s.strip()) > 15][:30]

            items = []
            if sentences:
                interval = dur / len(sentences)
                for i, s in enumerate(sentences):
                    items.append({'start': round(i * interval, 1), 'duration': round(interval, 1), 'text': s})
                return items, "Video Description Fallback"
            else:
                for sec in range(0, int(dur), 15):
                    items.append({'start': float(sec), 'duration': 15.0, 'text': f"{title} segment at {sec}s"})
                return items, "Duration-Based Fallback"

    except Exception as e:
        return [{'start': float(i * 30), 'duration': 30.0, 'text': f'Segment {i+1}'} for i in range(20)], f"Emergency Fallback ({str(e)[:50]})"

def extract_json_safely(raw):
    text = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except Exception:
        for start_char, end_char in [('[', ']'), ('{', '}')]:
            s = text.find(start_char)
            e = text.rfind(end_char)
            if s != -1 and e > s:
                try:
                    return json.loads(text[s:e+1])
                except Exception:
                    continue
    return None

def download_source(url, output_path):
    """Downloads video with multi-client fallback."""
    errors = []
    # Attempt 1: android_vr + tv_embedded
    try:
        opts = get_ytdl_opts({
            'format': 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best[ext=mp4]/best',
            'outtmpl': output_path,
            'overwrites': True
        })
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        errors.append(str(e))

    # Attempt 2: ios only, simpler format
    try:
        opts2 = get_ytdl_opts({
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_path,
            'overwrites': True,
            'extractor_args': {'youtube': {'player_client': ['ios', 'android']}}
        })
        with yt_dlp.YoutubeDL(opts2) as ydl:
            ydl.download([url])
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        errors.append(str(e))

    # Attempt 3: No extractor_args at all
    try:
        opts3 = get_ytdl_opts({
            'format': 'best',
            'outtmpl': output_path,
            'overwrites': True
        })
        del opts3['extractor_args']
        with yt_dlp.YoutubeDL(opts3) as ydl:
            ydl.download([url])
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        errors.append(str(e))

    raise Exception(f"All download methods failed: {'; '.join(errors)}")

# --- ALGORITHMIC ENGINES ---
def smart_5_shorts(items):
    hooks = {
        "Controversial Truth": ["never", "wrong", "lie", "actually", "truth", "nobody", "stop", "myth"],
        "Breakthrough Insight": ["secret", "realize", "discovered", "understand", "future", "key", "mindset"],
        "The Big Mistake": ["mistake", "fail", "ruining", "danger", "problem", "worst", "lose"],
        "Secret Hack": ["how to", "fastest", "technique", "method", "strategy", "hack", "easy"],
        "Powerful Story": ["when i", "years ago", "changed", "remember", "suddenly", "happened", "lesson"]
    }
    total = len(items)
    step = max(1, total // 6)
    clips = []

    for idx, (name, kws) in enumerate(hooks.items()):
        si = min(idx * step, total - 1)
        ei = min((idx + 1) * step + 20, total)
        best_start = float(items[si].get('start', idx * 45))
        best_score = -1
        best_text = ""

        for i in range(si, ei):
            ts = float(items[i].get('start', 0))
            txt = ""
            sc = 0
            for j in range(i, min(i + 30, total)):
                nxt = items[j]
                txt += " " + str(nxt.get('text', ''))
                d = (float(nxt.get('start', 0)) + float(nxt.get('duration', 2))) - ts
                if 30 <= d <= 55:
                    low = txt.lower()
                    for kw in kws:
                        if kw in low:
                            sc += 3
                    if "?" in txt or "!" in txt:
                        sc += 2
                    if sc > best_score:
                        best_score = sc
                        best_start = ts
                        best_text = txt.strip()
                    break

        clip_end = min(best_start + 45.0, float(items[-1].get('start', best_start + 45)) + 4.0)
        summary = best_text[:120] if best_text else "Key insights in this clip."

        clips.append({
            "start": round(best_start, 1),
            "end": round(clip_end, 1),
            "title": f"The {name.split()[0]} You Can't Ignore 🤯",
            "description": f"{summary}... Watch until the end! Subscribe for more.",
            "tags": ["#shorts", "#viral", "#insight", "#mindset", "#trending"],
            "hook_type": name,
            "reasoning": f"Hook score {best_score} for {name}."
        })
    return clips

def algo_longform_chapters(items, target_mins=10):
    total = len(items)
    num = 8
    seg_sec = (target_mins * 60) // num
    step = max(1, total // num)
    names = ["The Hook & Master Premise", "The Core Problem Unveiled", "The Most Common Trap",
             "The Paradigm Shift", "The Step-by-Step Strategy", "The Surprising Case Study",
             "Mastering the Nuances", "The Final Verdict & Action Plan"]
    chapters = []
    for i in range(num):
        si = min(i * step, total - 1)
        ts = float(items[si].get('start', i * 60))
        chapters.append({"chapter_title": names[i], "start": round(ts, 1), "end": round(ts + seg_sec, 1)})
    return {
        "title": f"The Complete Masterclass (In {target_mins} Minutes) 🧠",
        "summary": f"Distilled {target_mins}-minute breakdown of the full discussion.",
        "tags": ["masterclass", "summary", "key takeaways", "deep dive", "productivity", "best advice"],
        "chapters": chapters
    }

# --- OLLAMA ---
def query_ollama(prompt, model="llama3.2"):
    url = "http://localhost:11434/api/generate"
    data = {"model": model, "prompt": prompt, "stream": False, "format": "json"}
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as response:
        res = json.loads(response.read().decode("utf-8"))
        return extract_json_safely(res.get("response", "{}"))

# --- RENDER ENGINES ---
def render_short(src, start, end, res_key, speed, out):
    dur = end - start
    scale = res_map.get(res_key, "2160:3840")
    preset = "ultrafast" if "Ultra Fast" in speed else "fast"
    subprocess.run([FFMPEG_BIN, "-y", "-ss", str(start), "-i", src, "-t", str(dur),
                    "-vf", f"crop=ih*(9/16):ih,scale={scale}:flags=fast_bilinear",
                    "-c:v", "libx264", "-preset", preset, "-crf", "20",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out],
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def render_mastercut(src, chapters, res_key, speed, out):
    scale = res_map.get(res_key, "3840:2160")
    preset = "ultrafast" if "Ultra Fast" in speed else "fast"
    temps = []
    try:
        for i, ch in enumerate(chapters):
            seg = f"tmp_seg_{i}.mp4"
            dur = float(ch.get("end", 60)) - float(ch.get("start", 0))
            subprocess.run([FFMPEG_BIN, "-y", "-ss", str(ch["start"]), "-i", src, "-t", str(dur),
                            "-vf", f"scale={scale}:flags=fast_bilinear",
                            "-c:v", "libx264", "-preset", preset, "-crf", "20",
                            "-c:a", "aac", "-b:a", "192k", seg],
                           stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            if os.path.exists(seg):
                temps.append(seg)

        with open("concat.txt", "w") as f:
            for t in temps:
                f.write(f"file '{os.path.abspath(t)}'\n")
        subprocess.run([FFMPEG_BIN, "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt",
                        "-c", "copy", "-movflags", "+faststart", out],
                       stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    finally:
        for t in temps:
            if os.path.exists(t):
                os.remove(t)
        if os.path.exists("concat.txt"):
            os.remove("concat.txt")

# --- MAIN UI ---
url_input = st.text_input("🔗 Paste YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")

if "Shorts" in app_mode:
    btn_label = "🚀 Generate 5x 4K Viral Shorts (9:16)"
else:
    btn_label = f"🚀 Generate {target_duration_min}-Minute 4K Mastercut (16:9)"

if st.button(btn_label, type="primary", use_container_width=True):
    if not url_input.strip():
        st.warning("Please paste a valid YouTube URL.")
    else:
        vid_id = extract_video_id(url_input)
        if not vid_id:
            st.error("Invalid YouTube URL.")
        else:
            status = st.status("⚡ Processing...", expanded=True)
            try:
                # 1. Transcript
                status.write("📥 Step 1/4: Extracting transcript...")
                transcript_items, t_source = fetch_transcript(url_input, vid_id)
                status.write(f"✅ Transcript loaded ({len(transcript_items)} lines via {t_source}).")

                # 2. Download
                status.write("📥 Step 2/4: Downloading video stream...")
                src = f"source_{vid_id}.mp4"
                download_source(url_input, src)
                status.write("✅ Source video downloaded.")

                if "Long-Form" in app_mode:
                    # LONG-FORM MODE
                    status.write(f"🤖 Step 3/4: Structuring {target_duration_min}-min mastercut...")
                    lf_meta = None
                    if "Ollama" in ai_engine:
                        try:
                            condensed = "\n".join([f"[{int(t.get('start',0))}s] {t.get('text','')}" for t in transcript_items[::max(1,len(transcript_items)//40)]])[:3000]
                            lf_meta = query_ollama(f"Analyze transcript, return JSON with title, summary, tags, chapters (8 objects with chapter_title/start/end):\n{condensed}", ollama_model)
                        except Exception as e:
                            status.write(f"⚠️ Ollama: {e}. Using algorithm.")

                    if not lf_meta or not isinstance(lf_meta.get("chapters"), list):
                        lf_meta = algo_longform_chapters(transcript_items, target_duration_min)

                    chapters = lf_meta["chapters"]
                    status.write(f"✅ {len(chapters)} chapters created.")

                    cur = 0.0
                    ch_lines = []
                    for c in chapters:
                        m, s = int(cur // 60), int(cur % 60)
                        ch_lines.append(f"{m:02d}:{s:02d} - {c.get('chapter_title', 'Insight')}")
                        cur += float(c.get("end", 60)) - float(c.get("start", 0))

                    desc = f"""{lf_meta.get('summary', 'Ultimate mastercut.')}\n\n⏱️ CHAPTERS:\n{chr(10).join(ch_lines)}\n\n🔔 Subscribe for more!"""

                    status.write(f"✂️ Step 4/4: Rendering mastercut...")
                    out_name = f"mastercut_{vid_id}_{target_duration_min}min.mp4"
                    render_mastercut(src, chapters, render_resolution, render_speed, out_name)

                    if os.path.exists(src): os.remove(src)
                    status.update(label=f"🎉 {target_duration_min}-Min Mastercut Ready!", state="complete", expanded=False)
                    st.session_state["mode"] = "longform"
                    st.session_state["longform_output"] = {
                        "file": out_name,
                        "title": lf_meta.get("title", f"Masterclass ({target_duration_min} Min) 🧠"),
                        "description": desc,
                        "tags": lf_meta.get("tags", ["masterclass", "summary", "highlights"])
                    }
                else:
                    # SHORTS MODE
                    status.write("🤖 Step 3/4: Finding top 5 viral hooks...")
                    shorts_data = None
                    if "Ollama" in ai_engine:
                        try:
                            condensed = "\n".join([f"[{int(t.get('start',0))}s] {t.get('text','')}" for t in transcript_items[::max(1,len(transcript_items)//30)]])[:3000]
                            raw = query_ollama(f"Find 5 viral shorts (30-55s). Return JSON with 'shorts' array (start/end/title/description/tags/hook_type/reasoning):\n{condensed}", ollama_model)
                            if raw and isinstance(raw.get("shorts"), list):
                                shorts_data = raw["shorts"]
                        except Exception:
                            pass
                    if not shorts_data:
                        shorts_data = smart_5_shorts(transcript_items)

                    status.write(f"✂️ Step 4/4: Rendering 5 shorts...")
                    rendered = []
                    for i, s in enumerate(shorts_data[:5]):
                        out = f"short_{vid_id}_{i+1}.mp4"
                        status.write(f"🎬 Short #{i+1} ({s.get('hook_type','Viral')})...")
                        render_short(src, float(s.get('start', i*45)), float(s.get('end', i*45+40)), render_resolution, render_speed, out)
                        rendered.append((out, s))

                    if os.path.exists(src): os.remove(src)
                    status.update(label="🎉 5x Shorts Ready!", state="complete", expanded=False)
                    st.session_state["mode"] = "shorts"
                    st.session_state["shorts_output"] = rendered

            except Exception as e:
                status.update(label="❌ Error", state="error", expanded=True)
                st.error(f"Error Details: {str(e)}")

# --- DISPLAY ---
if st.session_state.get("mode") == "longform" and "longform_output" in st.session_state:
    st.markdown("---")
    st.header("🎬 Your 4K Long-Form Mastercut (16:9)")
    d = st.session_state["longform_output"]
    c1, c2 = st.columns([1.2, 1])
    with c1:
        if os.path.exists(d["file"]):
            st.video(d["file"])
            with open(d["file"], "rb") as f:
                st.download_button("⬇️ Download 4K Mastercut", f, file_name=d["file"], mime="video/mp4", use_container_width=True)
    with c2:
        st.text_input("🔥 Title", value=d["title"])
        st.text_area("📄 Description & Chapters", value=d["description"], height=220)
        st.text_input("🏷️ Tags", value=" ".join(d["tags"]) if isinstance(d["tags"], list) else d["tags"])

elif st.session_state.get("mode") == "shorts" and "shorts_output" in st.session_state:
    st.markdown("---")
    st.header("🎬 Your 5 4K Viral Shorts (9:16)")
    tabs = st.tabs([f"📱 #{i+1}: {d.get('hook_type','Viral')}" for i, (_, d) in enumerate(st.session_state["shorts_output"])])
    for i, tab in enumerate(tabs):
        with tab:
            fp, meta = st.session_state["shorts_output"][i]
            c1, c2 = st.columns([1, 1])
            with c1:
                if os.path.exists(fp):
                    st.video(fp)
                    with open(fp, "rb") as f:
                        st.download_button(f"⬇️ Download Short #{i+1}", f, file_name=fp, mime="video/mp4", use_container_width=True, key=f"dl_{i}")
            with c2:
                st.text_input(f"Title #{i+1}", value=meta.get("title", ""), key=f"t_{i}")
                st.text_area(f"Description #{i+1}", value=meta.get("description", ""), height=100, key=f"d_{i}")
                tags = " ".join(meta.get("tags", [])) if isinstance(meta.get("tags"), list) else meta.get("tags", "")
                st.text_input(f"Tags #{i+1}", value=tags, key=f"tg_{i}")
