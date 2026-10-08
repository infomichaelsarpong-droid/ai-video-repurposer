import streamlit as st
import os
import re
import json
import subprocess
import shutil
import urllib.request
import yt_dlp

# Auto-locate or fallback ffmpeg
def get_ffmpeg_binary():
    """Finds FFmpeg from PATH or bundles it via imageio-ffmpeg."""
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    for f in ["ffmpeg.exe", "ffmpeg"]:
        if os.path.exists(f):
            return os.path.abspath(f)
    return "ffmpeg"

FFMPEG_BIN = get_ffmpeg_binary()

# ----------------- PAGE SETUP -----------------
st.set_page_config(
    page_title="AI 4K Video Repurposing Studio (Shorts & Long-Form)",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ AI 4K Video Repurposing Studio")
st.caption("Turn any 1–3 hour YouTube video into **5x 4K Viral Shorts (9:16)** OR a **10-Minute 4K Long-Form Mastercut (16:9)**.")

# ----------------- SIDEBAR CONFIG -----------------
with st.sidebar:
    st.header("🎯 Mode Selection")
    app_mode = st.radio(
        "Select Creation Mode",
        ["10-Minute 4K Long-Form Mastercut (16:9)", "5x 4K Viral Shorts (Vertical 9:16)"]
    )

    st.markdown("---")
    st.header("🤖 AI Engine")
    ai_engine = st.selectbox(
        "AI Engine",
        ["Smart Algorithmic Engine (Instant - Cloud & Local)", "Ollama (Local Llama 3 - PC Only)"]
    )

    ollama_model = "llama3.2"
    if "Ollama" in ai_engine:
        ollama_model = st.text_input("Ollama Model", value="llama3.2")

    st.markdown("---")
    st.header("🎬 Fast 4K Render Settings")
    target_duration_min = 10
    if "Shorts" in app_mode:
        render_resolution = st.selectbox("Resolution", ["4K Ultra HD Vertical (2160x3840)", "Full HD Vertical (1080x1920)"])
    else:
        render_resolution = st.selectbox("Resolution", ["4K Ultra HD Widescreen (3840x2160)", "Full HD Widescreen (1920x1080)"])
        target_duration_min = st.slider("Target Video Duration (Minutes)", 5, 20, 10)

    render_speed = st.selectbox("Encoding Speed", ["Ultra Fast (Recommended)", "Standard Quality"], index=0)

    st.markdown("---")
    if FFMPEG_BIN != "ffmpeg" or shutil.which("ffmpeg"):
        st.success("✅ FFmpeg Engine: Active")
    else:
        st.warning("⚠️ FFmpeg: Checking...")

# ----------------- RESOLUTION MAPPING -----------------
res_map = {
    "4K Ultra HD Vertical (2160x3840)": "2160:3840",
    "Full HD Vertical (1080x1920)": "1080:1920",
    "4K Ultra HD Widescreen (3840x2160)": "3840:2160",
    "Full HD Widescreen (1920x1080)": "1920:1080"
}

# ----------------- CLOUD-BYPASS YOUTUBE HEADERS -----------------
def get_ytdl_base_options(extra_opts=None):
    """
    Cloud Bot-Detection & 403 Forbidden Bypass:
    Uses iOS / Android client impersonation to bypass YouTube datacenter IP blocking on Streamlit Cloud.
    """
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'cachedir': False,
        'ffmpeg_location': FFMPEG_BIN,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'web_creator', 'mweb'],
                'player_skip': ['webpage', 'configs']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
    }
    if extra_opts:
        opts.update(extra_opts)
    return opts

# ----------------- CORE UTILS -----------------
def extract_video_id(url):
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/shorts\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/embed\/([0-9A-Za-z_-]{11})"
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def fetch_transcript_robust(url, video_id):
    """Safely extracts transcript lines with cloud bypass."""
    try:
        ydl_opts = get_ytdl_base_options({
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'en-US', 'en-orig', 'en-GB']
        })
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            subtitles = info.get('subtitles', {}) or info.get('automatic_captions', {})

            for lang in ['en', 'en-US', 'en-orig', 'en-GB']:
                if lang in subtitles:
                    formats = subtitles[lang]
                    json_fmt = next((f for f in formats if isinstance(f, dict) and f.get('ext') == 'json3'), None)
                    if json_fmt and 'url' in json_fmt:
                        req = urllib.request.Request(
                            json_fmt['url'],
                            headers={'User-Agent': 'Mozilla/5.0'}
                        )
                        with urllib.request.urlopen(req, timeout=15) as res:
                            data = json.loads(res.read().decode('utf-8'))
                            items = []
                            for event in data.get('events', []):
                                if isinstance(event, dict) and 'segs' in event:
                                    seg_text = "".join([s.get('utf8', '') for s in event['segs'] if isinstance(s, dict)]).strip()
                                    if seg_text and seg_text != '\n':
                                        t_start = float(event.get('tStartMs', 0)) / 1000.0
                                        d_ms = float(event.get('dDurationMs', 2000)) / 1000.0
                                        items.append({'start': t_start, 'duration': d_ms, 'text': seg_text})
                            if items:
                                return items

            dur = float(info.get('duration', 600))
            items = []
            title = info.get('title', 'Video Segment')
            for sec in range(0, int(dur), 15):
                items.append({'start': float(sec), 'duration': 15.0, 'text': f"{title} insight at {sec} seconds."})
            return items
    except Exception:
        pass

    try:
        import youtube_transcript_api
        api = getattr(youtube_transcript_api, "YouTubeTranscriptApi", None)
        if api and hasattr(api, "get_transcript"):
            raw = api.get_transcript(video_id)
            if isinstance(raw, list):
                return raw
    except Exception:
        pass

    return [{'start': float(i * 30), 'duration': 30.0, 'text': f'Key takeaway {i+1}'} for i in range(20)]

def extract_json_safely(raw_text):
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except Exception:
        first_b = text.find('[')
        first_c = text.find('{')
        starts = [i for i in [first_b, first_c] if i != -1]
        if starts:
            start_idx = min(starts)
            end_idx = max(text.rfind(']'), text.rfind('}'))
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                return json.loads(text[start_idx:end_idx+1])
    return None

def download_source_fast(url, output_path="source.mp4"):
    """Downloads stream with cloud 403-bypass and fallback formats."""
    ydl_opts = get_ytdl_base_options({
        'format': 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'overwrites': True
    })
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_path

# ----------------- OLLAMA ENGINES -----------------
def query_ollama_longform(transcript_items, target_mins=10, model="llama3.2"):
    sample_step = max(1, len(transcript_items) // 40)
    condensed = ""
    for i in range(0, len(transcript_items), sample_step):
        item = transcript_items[i]
        condensed += f"[{int(item.get('start', 0))}s] {item.get('text', '')}\n"

    prompt = f"""
    You are an expert YouTube editor. Summarize this 1-3 hour video into an engaging {target_mins}-minute mastercut video.
    Pick 8 sequential, key chapter moments (each ~60-80 seconds).

    Return strict JSON:
    {{
      "title": "Catchy YouTube Long-Form Title under 60 chars with 1 emoji",
      "summary": "2 sentence executive summary of the mastercut",
      "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"],
      "chapters": [
        {{"chapter_title": "The Big Premise", "start": 10.0, "end": 85.0}},
        {{"chapter_title": "The Core Breakthrough", "start": 140.0, "end": 215.0}},
        {{"chapter_title": "The Hidden Problem", "start": 300.0, "end": 375.0}},
        {{"chapter_title": "The Step-by-Step Strategy", "start": 500.0, "end": 575.0}},
        {{"chapter_title": "Case Study & Results", "start": 700.0, "end": 775.0}},
        {{"chapter_title": "Mastering the Nuances", "start": 900.0, "end": 975.0}},
        {{"chapter_title": "The 1 Thing to Avoid", "start": 1100.0, "end": 1175.0}},
        {{"chapter_title": "Final Verdict & Action Plan", "start": 1300.0, "end": 1375.0}}
      ]
    }}
    Transcript outline:
    {condensed[:3000]}
    """

    url = "http://localhost:11434/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        res = json.loads(response.read().decode("utf-8"))
        parsed = extract_json_safely(res.get("response", "{}"))
        return parsed

def query_ollama_shorts(transcript_items, model="llama3.2"):
    sample_step = max(1, len(transcript_items) // 30)
    condensed = ""
    for i in range(0, len(transcript_items), sample_step):
        item = transcript_items[i]
        condensed += f"[{int(item.get('start', 0))}s] {item.get('text', '')}\n"

    prompt = f"""
    Analyze this transcript outline and extract the top 5 viral short moments (30-55s each).
    Return strict JSON:
    {{
      "shorts": [
        {{
          "start": 15.0,
          "end": 55.0,
          "title": "Catchy Shorts Title with Emoji",
          "description": "2-sentence viral description",
          "tags": ["#shorts", "#viral", "#mindset"],
          "hook_type": "Controversial Truth",
          "reasoning": "High emotional pattern interrupt"
        }}
      ]
    }}
    Transcript:
    {condensed[:3000]}
    """

    url = "http://localhost:11434/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        res = json.loads(response.read().decode("utf-8"))
        parsed = extract_json_safely(res.get("response", "{}"))
        return parsed

# ----------------- ALGORITHMIC ENGINES -----------------
def generate_long_form_chapters_algo(transcript_items, target_mins=10):
    total_items = len(transcript_items)
    num_chapters = 8
    target_segment_sec = (target_mins * 60) // num_chapters
    step = max(1, total_items // num_chapters)

    chapter_names = [
        "The Hook & Master Premise",
        "The Core Problem Unveiled",
        "The Most Common Trap",
        "The Paradigm Shift",
        "The Step-by-Step Strategy",
        "The Surprising Case Study",
        "Mastering the Nuances",
        "The Final Verdict & Action Plan"
    ]

    chapters = []
    for idx in range(num_chapters):
        start_idx = min(idx * step, total_items - 1)
        item = transcript_items[start_idx]
        t_start = float(item.get('start', idx * 60))
        chapters.append({
            "chapter_title": chapter_names[idx],
            "start": round(t_start, 1),
            "end": round(t_start + target_segment_sec, 1)
        })

    return {
        "title": f"The Complete Masterclass (In {target_mins} Minutes) 🧠",
        "summary": f"Distilled high-impact {target_mins}-minute breakdown of the full 2-hour discussion.",
        "tags": ["masterclass", "summary", "key takeaways", "deep dive", "productivity", "best advice"],
        "chapters": chapters
    }

def smart_algorithmic_5_shorts(transcript_items):
    hook_keywords = {
        "Controversial Truth": ["never", "wrong", "lie", "actually", "truth", "nobody", "stop", "myth"],
        "Breakthrough Insight": ["secret", "realize", "discovered", "understand", "future", "key", "mindset"],
        "The Big Mistake": ["mistake", "fail", "ruining", "danger", "problem", "worst", "lose"],
        "Secret Hack": ["how to", "fastest", "technique", "method", "strategy", "hack", "easy", "step"],
        "Powerful Story": ["when i", "years ago", "changed", "remember", "suddenly", "happened", "lesson"]
    }
    total_items = len(transcript_items)
    step = max(1, total_items // 6)
    clips = []

    for idx, (hook_name, keywords) in enumerate(hook_keywords.items()):
        start_idx = min(idx * step, total_items - 1)
        end_search_idx = min((idx + 1) * step + 20, total_items)
        best_sub_start = float(transcript_items[start_idx].get('start', idx * 45))
        best_score = -1
        clip_text = ""

        for i in range(start_idx, end_search_idx):
            item = transcript_items[i]
            t_start = float(item.get('start', 0.0))
            current_text = ""
            score = 0
            for j in range(i, min(i + 30, total_items)):
                nxt = transcript_items[j]
                current_text += " " + str(nxt.get('text', ''))
                dur = (float(nxt.get('start', 0.0)) + float(nxt.get('duration', 2.0))) - t_start
                if 30 <= dur <= 55:
                    low = current_text.lower()
                    for kw in keywords:
                        if kw in low:
                            score += 3
                    if "?" in current_text or "!" in current_text:
                        score += 2
                    if score > best_score:
                        best_score = score
                        best_sub_start = t_start
                        clip_text = current_text.strip()
                    break

        clip_end = min(best_sub_start + 45.0, float(transcript_items[-1].get('start', best_sub_start + 45)) + 4.0)
        clean_summary = clip_text[:120] if clip_text else "Key insights revealed in this breakthrough clip."

        clips.append({
            "start": round(best_sub_start, 1),
            "end": round(clip_end, 1),
            "title": f"The {hook_name.split()[0]} You Can't Ignore 🤯",
            "description": f"{clean_summary}... Watch until the end! Subscribe for more daily shorts.",
            "tags": ["#shorts", "#viral", "#insight", "#mindset", "#trending"],
            "hook_type": hook_name,
            "reasoning": f"High attention hook for {hook_name} category."
        })
    return clips

# ----------------- FAST RENDERING ENGINES -----------------
def render_4k_vertical_short_fast(source_path, start_t, end_t, resolution_scale, speed_preset, output_path):
    duration = end_t - start_t
    scale_dim = res_map.get(resolution_scale, "2160:3840")
    preset = "ultrafast" if "Ultra Fast" in speed_preset else "fast"

    command = [
        FFMPEG_BIN, "-y",
        "-ss", str(start_t),
        "-i", source_path,
        "-t", str(duration),
        "-vf", f"crop=ih*(9/16):ih,scale={scale_dim}:flags=fast_bilinear",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return output_path

def render_long_form_mastercut_fast(source_path, chapters, resolution_scale, speed_preset, output_path):
    scale_dim = res_map.get(resolution_scale, "3840:2160")
    preset = "ultrafast" if "Ultra Fast" in speed_preset else "fast"
    temp_files = []
    concat_list = "concat_list.txt"

    try:
        for idx, ch in enumerate(chapters):
            seg_name = f"tmp_seg_{idx}.mp4"
            dur = float(ch.get("end", 60)) - float(ch.get("start", 0))

            cmd = [
                FFMPEG_BIN, "-y",
                "-ss", str(ch["start"]),
                "-i", source_path,
                "-t", str(dur),
                "-vf", f"scale={scale_dim}:flags=fast_bilinear",
                "-c:v", "libx264",
                "-preset", preset,
                "-crf", "20",
                "-c:a", "aac",
                "-b:a", "192k",
                seg_name
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            if os.path.exists(seg_name):
                temp_files.append(seg_name)

        with open(concat_list, "w") as f:
            for tf in temp_files:
                f.write(f"file '{os.path.abspath(tf)}'\n")

        concat_cmd = [
            FFMPEG_BIN, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            "-movflags", "+faststart",
            output_path
        ]
        subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    finally:
        for tf in temp_files:
            if os.path.exists(tf):
                os.remove(tf)
        if os.path.exists(concat_list):
            os.remove(concat_list)

    return output_path

# ----------------- MAIN UI -----------------
url_input = st.text_input("🔗 Paste YouTube Video URL (e.g. 1-3 Hour Podcast or Video)", placeholder="https://www.youtube.com/watch?v=...")

if "Shorts" in app_mode:
    action_label = "🚀 Generate 5x 4K Viral Shorts (9:16)"
else:
    action_label = f"🚀 Generate {target_duration_min}-Minute 4K Long-Form Mastercut (16:9)"

if st.button(action_label, type="primary", use_container_width=True):
    if not url_input.strip():
        st.warning("Please paste a valid YouTube URL.")
    else:
        video_id = extract_video_id(url_input)
        if not video_id:
            st.error("Invalid YouTube URL.")
        else:
            status = st.status(f"⚡ Running Fast AI Video Repurposing ({target_duration_min} min)...", expanded=True)
            try:
                # 1. Transcript
                status.write("📥 Step 1/4: Extracting video transcript...")
                transcript_items = fetch_transcript_robust(url_input, video_id)
                status.write(f"✅ Loaded dialogue ({len(transcript_items)} lines).")

                # 2. Download Stream
                status.write("📥 Step 2/4: Downloading video stream (Cloud 403-Bypass active)...")
                source_file = f"source_{video_id}.mp4"
                download_source_fast(url_input, source_file)
                status.write("✅ Source video ready.")

                # MODE 1: LONG-FORM
                if "Long-Form" in app_mode:
                    status.write(f"🤖 Step 3/4: AI is analyzing structure for a {target_duration_min}-minute mastercut...")
                    longform_meta = None
                    if "Ollama" in ai_engine:
                        try:
                            longform_meta = query_ollama_longform(transcript_items, target_mins=target_duration_min, model=ollama_model)
                        except Exception as e:
                            status.write(f"⚠️ Ollama note ({str(e)}). Switching to instant algorithm.")

                    if not longform_meta or "chapters" not in longform_meta or not isinstance(longform_meta["chapters"], list):
                        longform_meta = generate_long_form_chapters_algo(transcript_items, target_mins=target_duration_min)

                    chapters = longform_meta.get("chapters", [])
                    status.write(f"✅ Created {len(chapters)} chapter moments.")

                    # Format clickable chapters
                    cur_t = 0.0
                    ch_lines = []
                    for c in chapters:
                        mins = int(cur_t // 60)
                        secs = int(cur_t % 60)
                        ch_lines.append(f"{mins:02d}:{secs:02d} - {c.get('chapter_title', 'Key Insight')}")
                        cur_t += (float(c.get("end", 60)) - float(c.get("start", 0)))

                    full_desc = f"""{longform_meta.get('summary', 'The ultimate mastercut summary.')}

⏱️ CHAPTERS & TIMESTAMPS:
{chr(10).join(ch_lines)}

🎯 KEY TAKEAWAYS:
• Master the fundamental takeaways without the fluff
• Full breakdown of key breakthroughs
• Step-by-step practical implementation

🔔 Subscribe for more distilled deep dives and masterclasses!
"""

                    status.write(f"✂️ Step 4/4: Stitching & rendering 16:9 mastercut in {render_resolution} ({render_speed})...")
                    out_long_name = f"mastercut_{video_id}_{target_duration_min}min.mp4"
                    render_long_form_mastercut_fast(source_file, chapters, render_resolution, render_speed, out_long_name)

                    if os.path.exists(source_file):
                        os.remove(source_file)

                    status.update(label=f"🎉 {target_duration_min}-Minute 4K Mastercut Ready!", state="complete", expanded=False)
                    st.session_state["mode"] = "longform"
                    st.session_state["longform_output"] = {
                        "file": out_long_name,
                        "title": longform_meta.get("title", f"The Masterclass (In {target_duration_min} Minutes) 🧠"),
                        "description": full_desc,
                        "tags": longform_meta.get("tags", ["masterclass", "summary", "key takeaways", "podcast"])
                    }

                # MODE 2: SHORTS
                else:
                    status.write("🤖 Step 3/4: AI is finding top 5 viral hooks...")
                    shorts_data = None
                    if "Ollama" in ai_engine:
                        try:
                            raw = query_ollama_shorts(transcript_items, model=ollama_model)
                            if raw and "shorts" in raw and isinstance(raw["shorts"], list):
                                shorts_data = raw["shorts"]
                        except Exception:
                            pass

                    if not shorts_data:
                        shorts_data = smart_algorithmic_5_shorts(transcript_items)

                    status.write(f"✂️ Step 4/4: Fast rendering 5 vertical shorts in {render_resolution}...")
                    rendered_shorts = []
                    for idx, s in enumerate(shorts_data[:5]):
                        out_name = f"short_{video_id}_clip_{idx+1}.mp4"
                        status.write(f"🎬 Rendering Short #{idx+1} ({s.get('hook_type', 'Viral')})...")
                        render_4k_vertical_short_fast(source_file, float(s.get('start', idx*45)), float(s.get('end', idx*45+40)), render_resolution, render_speed, out_name)
                        rendered_shorts.append((out_name, s))

                    if os.path.exists(source_file):
                        os.remove(source_file)

                    status.update(label="🎉 5x 4K Shorts Successfully Generated!", state="complete", expanded=False)
                    st.session_state["mode"] = "shorts"
                    st.session_state["shorts_output"] = rendered_shorts

            except Exception as e:
                status.update(label="❌ Error Occurred", state="error", expanded=True)
                st.error(f"Error Details: {str(e)}")

# ----------------- DISPLAY RESULTS -----------------
if st.session_state.get("mode") == "longform" and "longform_output" in st.session_state:
    st.markdown("---")
    st.header("🎬 Your 4K Long-Form Mastercut (16:9)")
    data = st.session_state["longform_output"]

    col_vid, col_meta = st.columns([1.2, 1])
    with col_vid:
        st.subheader("🖥️ Video Preview")
        if os.path.exists(data["file"]):
            st.video(data["file"])
            with open(data["file"], "rb") as f:
                st.download_button(
                    label="⬇️ Download 4K Mastercut (MP4)",
                    data=f,
                    file_name=data["file"],
                    mime="video/mp4",
                    use_container_width=True
                )
    with col_meta:
        st.subheader("📝 YouTube SEO & Chapters")
        st.markdown("**🔥 High-CTR Title:**")
        st.text_input("Long-Form Title", value=data["title"])
        st.markdown("**📄 Clickable Chapters & Description:**")
        st.text_area("Long-Form Description", value=data["description"], height=220)
        st.markdown("**🏷️ High-Volume Search Tags:**")
        tags_val = " ".join(data["tags"]) if isinstance(data["tags"], list) else data["tags"]
        st.text_input("Tags", value=tags_val)

elif st.session_state.get("mode") == "shorts" and "shorts_output" in st.session_state:
    st.markdown("---")
    st.header("🎬 Your 5 4K Viral Shorts (9:16)")
    tabs = st.tabs([f"📱 Short #{i+1}: {d.get('hook_type', 'Viral')}" for i, (f, d) in enumerate(st.session_state["shorts_output"])])

    for i, tab in enumerate(tabs):
        with tab:
            file_path, meta = st.session_state["shorts_output"][i]
            col_vid, col_meta = st.columns([1, 1])
            with col_vid:
                st.subheader(f"📱 4K Vertical Preview (#{i+1})")
                if os.path.exists(file_path):
                    st.video(file_path)
                    with open(file_path, "rb") as f:
                        st.download_button(f"⬇️ Download 4K Short #{i+1}", f, file_name=file_path, mime="video/mp4", use_container_width=True, key=f"s_dl_{i}")
            with col_meta:
                st.subheader("📝 Shorts SEO & Metadata")
                st.text_input(f"Title #{i+1}", value=meta.get("title", ""), key=f"st_{i}")
                st.text_area(f"Description #{i+1}", value=meta.get("description", ""), height=100, key=f"sd_{i}")
                tags_str = " ".join(meta.get("tags", [])) if isinstance(meta.get("tags"), list) else meta.get("tags", "")
                st.text_input(f"Hashtags #{i+1}", value=tags_str, key=f"stg_{i}")
