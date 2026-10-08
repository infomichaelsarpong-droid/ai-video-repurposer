import streamlit as st
import os
import re
import json
import subprocess
import shutil
import urllib.request
import yt_dlp
import time

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

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="ClipForge AI — 4K Video Repurposing Studio",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Global Font & Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif !important;
    }

    /* Hero Banner */
    .hero-banner {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        border-radius: 16px;
        padding: 40px 36px;
        margin-bottom: 28px;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .hero-banner::before {
        content: "";
        position: absolute;
        top: -50%;
        right: -20%;
        width: 500px;
        height: 500px;
        background: radial-gradient(circle, rgba(99,102,241,0.25) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-banner::after {
        content: "";
        position: absolute;
        bottom: -40%;
        left: -10%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(244,63,94,0.2) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-title {
        font-size: 2.4rem;
        font-weight: 900;
        color: #ffffff;
        margin: 0;
        position: relative;
        z-index: 2;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: rgba(255,255,255,0.7);
        margin-top: 8px;
        position: relative;
        z-index: 2;
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16,185,129,0.15);
        border: 1px solid rgba(16,185,129,0.4);
        color: #34d399;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        margin-top: 14px;
        position: relative;
        z-index: 2;
    }

    /* Stats Row */
    .stats-row {
        display: flex;
        gap: 16px;
        margin-bottom: 24px;
    }
    .stat-card {
        flex: 1;
        background: linear-gradient(135deg, #1e1b4b, #312e81);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 14px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s ease;
    }
    .stat-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 24px rgba(99,102,241,0.2);
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 900;
        background: linear-gradient(135deg, #818cf8, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stat-label {
        font-size: 0.82rem;
        color: rgba(255,255,255,0.55);
        margin-top: 4px;
        font-weight: 500;
    }

    /* Mode Selector Cards */
    .mode-cards {
        display: flex;
        gap: 16px;
        margin-bottom: 24px;
    }
    .mode-card {
        flex: 1;
        background: rgba(30, 27, 75, 0.6);
        border: 2px solid rgba(99,102,241,0.2);
        border-radius: 16px;
        padding: 24px;
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: center;
    }
    .mode-card:hover {
        border-color: #6366f1;
        background: rgba(99,102,241,0.1);
        transform: translateY(-2px);
    }
    .mode-card.active {
        border-color: #6366f1;
        background: rgba(99,102,241,0.15);
        box-shadow: 0 0 20px rgba(99,102,241,0.15);
    }
    .mode-icon {
        font-size: 2.5rem;
        margin-bottom: 10px;
    }
    .mode-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #e2e8f0;
    }
    .mode-desc {
        font-size: 0.8rem;
        color: rgba(255,255,255,0.45);
        margin-top: 6px;
    }

    /* URL Input Styling */
    .url-container {
        background: rgba(30, 27, 75, 0.5);
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 24px;
    }

    /* Processing Animation */
    .processing-container {
        background: linear-gradient(135deg, #0f0c29, #1a1744);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 16px;
        padding: 32px;
        text-align: center;
    }
    @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 0 20px rgba(99,102,241,0.3); }
        50% { box-shadow: 0 0 40px rgba(99,102,241,0.6); }
    }
    .pulse-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        font-size: 2rem;
        animation: pulse-glow 2s infinite;
        margin-bottom: 16px;
    }

    /* Result Card */
    .result-card {
        background: linear-gradient(135deg, #0f172a, #1e1b4b);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
    }
    .result-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }
    .result-title {
        font-size: 1.2rem;
        font-weight: 800;
        color: #e2e8f0;
    }
    .quality-badge {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* Metadata Cards */
    .meta-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(99,102,241,0.15);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .meta-label {
        font-size: 0.75rem;
        font-weight: 700;
        color: #818cf8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }

    /* Tag Pills */
    .tag-container {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    .tag-pill {
        background: rgba(99,102,241,0.15);
        border: 1px solid rgba(99,102,241,0.3);
        color: #a5b4fc;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29, #1a1744) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e2e8f0 !important;
    }

    /* Feature Grid */
    .feature-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin: 16px 0;
    }
    .feature-item {
        background: rgba(99,102,241,0.08);
        border: 1px solid rgba(99,102,241,0.15);
        border-radius: 10px;
        padding: 14px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .feature-icon {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        flex-shrink: 0;
    }
    .feature-text {
        font-size: 0.82rem;
        color: #cbd5e1;
        font-weight: 500;
    }

    /* Progress Steps */
    .step-container {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: rgba(99,102,241,0.06);
        border-radius: 10px;
        margin-bottom: 8px;
        border-left: 3px solid #6366f1;
    }
    .step-done {
        border-left-color: #10b981;
        background: rgba(16,185,129,0.06);
    }
    .step-active {
        border-left-color: #f59e0b;
        background: rgba(245,158,11,0.06);
        animation: pulse-border 1.5s infinite;
    }
    @keyframes pulse-border {
        0%, 100% { border-left-color: #f59e0b; }
        50% { border-left-color: #fbbf24; }
    }

    /* Animated Gradient Button */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1, #8b5cf6, #a855f7) !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        padding: 14px 28px !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(99,102,241,0.4) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(99,102,241,0.5) !important;
    }

    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- HERO BANNER ---
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">🔥 ClipForge AI Studio</div>
    <div class="hero-subtitle">Turn any YouTube video into viral-ready content — 4K Shorts, Long-Form Mastercuts, and SEO-optimized metadata. 100% free, runs locally.</div>
    <div class="hero-badge">⚡ Powered by Local AI — Zero API Cost</div>
</div>
""", unsafe_allow_html=True)

# --- STATS ROW ---
total_processed = st.session_state.get("total_processed", 0)
st.markdown(f"""
<div class="stats-row">
    <div class="stat-card">
        <div class="stat-number">4K</div>
        <div class="stat-label">Ultra HD Rendering</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">5x</div>
        <div class="stat-label">Viral Shorts Per Video</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">9:16</div>
        <div class="stat-label">Vertical + 16:9 Widescreen</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{total_processed}</div>
        <div class="stat-label">Videos Processed</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🎯 Creation Mode")
    app_mode = st.radio("Mode", ["5x 4K Viral Shorts (9:16)", "Long-Form 4K Mastercut (16:9)"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### 🤖 AI Engine")
    ai_engine = st.selectbox("Engine", ["Smart Algorithm (Instant)", "Ollama (Local LLM - Free)"], label_visibility="collapsed")
    ollama_model = "llama3.2"
    if "Ollama" in ai_engine:
        ollama_model = st.text_input("Ollama Model", value="llama3.2")

    st.markdown("---")
    st.markdown("### 🎬 Render Quality")
    target_duration_min = 10
    if "Shorts" in app_mode:
        render_resolution = st.selectbox("Resolution", ["4K Ultra HD (2160x3840)", "Full HD (1080x1920)"], label_visibility="collapsed")
    else:
        render_resolution = st.selectbox("Resolution", ["4K Ultra HD (3840x2160)", "Full HD (1920x1080)"], label_visibility="collapsed")
        target_duration_min = st.slider("Target Duration (min)", 5, 20, 10)

    render_speed = st.selectbox("Speed", ["Ultra Fast", "Standard"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### 🛠️ System Status")
    if shutil.which("ffmpeg") or FFMPEG_BIN != "ffmpeg":
        st.markdown("✅ **FFmpeg** — Active")
    else:
        st.markdown("❌ **FFmpeg** — Missing")
    st.markdown(f"✅ **AI Engine** — {ai_engine.split('(')[0].strip()}")
    st.markdown(f"✅ **Resolution** — {render_resolution.split('(')[0].strip()}")

    st.markdown("---")
    st.markdown("### ✨ Features")
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-item"><div class="feature-icon">🎬</div><div class="feature-text">4K Vertical Crop</div></div>
        <div class="feature-item"><div class="feature-icon">🤖</div><div class="feature-text">AI Hook Finder</div></div>
        <div class="feature-item"><div class="feature-icon">📝</div><div class="feature-text">SEO Metadata</div></div>
        <div class="feature-item"><div class="feature-icon">⚡</div><div class="feature-text">Ultra Fast Render</div></div>
    </div>
    """, unsafe_allow_html=True)

# --- RESOLUTION MAP ---
res_map = {
    "4K Ultra HD (2160x3840)": "2160:3840",
    "Full HD (1080x1920)": "1080:1920",
    "4K Ultra HD (3840x2160)": "3840:2160",
    "Full HD (1920x1080)": "1920:1080"
}

# --- YT-DLP OPTIONS ---
def get_ytdl_opts(extra=None):
    opts = {
        'quiet': True, 'no_warnings': True, 'nocheckcertificate': True,
        'geo_bypass': True, 'cachedir': False, 'ffmpeg_location': FFMPEG_BIN,
        'extractor_args': {'youtube': {'player_client': ['android_vr', 'tv_embedded', 'ios'], 'player_skip': ['webpage', 'configs']}},
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'}
    }
    if extra: opts.update(extra)
    return opts

# --- CORE FUNCTIONS ---
def extract_video_id(url):
    for p in [r"(?:v=|\/)([0-9A-Za-z_-]{11})", r"youtu\.be\/([0-9A-Za-z_-]{11})", r"youtube\.com\/shorts\/([0-9A-Za-z_-]{11})"]:
        m = re.search(p, url)
        if m: return m.group(1)
    return None

def get_video_info(url):
    """Gets video title, duration, thumbnail etc."""
    try:
        opts = get_ytdl_opts({'skip_download': True})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'channel': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'description': info.get('description', '')
            }
    except Exception:
        return None

def fetch_transcript(url, video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        ytt = YouTubeTranscriptApi
        if hasattr(ytt, 'get_transcript'):
            items = ytt.get_transcript(video_id)
            if isinstance(items, list) and len(items) > 5: return items, "YouTube Captions"
        if hasattr(ytt, 'list_transcripts'):
            for t in ytt.list_transcripts(video_id):
                items = t.fetch()
                if isinstance(items, list) and len(items) > 5: return items, "YouTube Captions"
    except Exception: pass

    try:
        opts = get_ytdl_opts({'skip_download': True, 'writesubtitles': True, 'writeautomaticsub': True, 'subtitleslangs': ['en', 'en-US', 'en-orig']})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            subs = {}
            subs.update(info.get('subtitles', {}) or {})
            subs.update(info.get('automatic_captions', {}) or {})
            for lang in ['en', 'en-US', 'en-orig', 'en-GB']:
                if lang in subs:
                    jf = next((f for f in subs[lang] if isinstance(f, dict) and f.get('ext') == 'json3'), None)
                    if jf and 'url' in jf:
                        req = urllib.request.Request(jf['url'], headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=15) as res:
                            data = json.loads(res.read().decode('utf-8'))
                            items = []
                            for ev in data.get('events', []):
                                if isinstance(ev, dict) and 'segs' in ev:
                                    txt = "".join([s.get('utf8', '') for s in ev['segs'] if isinstance(s, dict)]).strip()
                                    if txt and txt != '\n':
                                        items.append({'start': float(ev.get('tStartMs', 0))/1000, 'duration': float(ev.get('dDurationMs', 2000))/1000, 'text': txt})
                            if len(items) > 5: return items, "yt-dlp Subtitles"
            desc = info.get('description', '') or ''
            sentences = [s.strip() for s in re.split(r'[.\n]', desc) if len(s.strip()) > 15][:30]
            dur = float(info.get('duration', 600))
            if sentences:
                interval = dur / len(sentences)
                return [{'start': round(i*interval,1), 'duration': round(interval,1), 'text': s} for i, s in enumerate(sentences)], "Description Fallback"
    except Exception: pass

    return [{'start': float(i*30), 'duration': 30.0, 'text': f'Segment {i+1}'} for i in range(20)], "Fallback"

def extract_json_safely(raw):
    text = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m: text = m.group(1).strip()
    try: return json.loads(text)
    except Exception:
        for sc, ec in [('[',']'),('{','}')]:
            s, e = text.find(sc), text.rfind(ec)
            if s != -1 and e > s:
                try: return json.loads(text[s:e+1])
                except: continue
    return None

def download_source(url, out):
    errors = []
    for fmt_str in [
        'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best',
        'best[ext=mp4]/best',
        'best'
    ]:
        try:
            opts = get_ytdl_opts({'format': fmt_str, 'outtmpl': out, 'overwrites': True})
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            if os.path.exists(out): return out
        except Exception as e:
            errors.append(str(e)[:80])
    raise Exception(f"Download failed: {'; '.join(errors)}")

# --- AI ENGINES ---
def query_ollama(prompt, model="llama3.2"):
    url = "http://localhost:11434/api/generate"
    data = {"model": model, "prompt": prompt, "stream": False, "format": "json"}
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as response:
        res = json.loads(response.read().decode("utf-8"))
        return extract_json_safely(res.get("response", "{}"))

def smart_5_shorts(items):
    hooks = {
        "Controversial Truth": ["never","wrong","lie","actually","truth","nobody","stop","myth"],
        "Breakthrough Insight": ["secret","realize","discovered","understand","future","key","mindset"],
        "The Big Mistake": ["mistake","fail","ruining","danger","problem","worst","lose"],
        "Secret Hack": ["how to","fastest","technique","method","strategy","hack","easy"],
        "Powerful Story": ["when i","years ago","changed","remember","suddenly","happened","lesson"]
    }
    total = len(items); step = max(1, total//6); clips = []
    for idx, (name, kws) in enumerate(hooks.items()):
        si = min(idx*step, total-1); ei = min((idx+1)*step+20, total)
        bs = float(items[si].get('start', idx*45)); bsc = -1; bt = ""
        for i in range(si, ei):
            ts = float(items[i].get('start',0)); txt = ""; sc = 0
            for j in range(i, min(i+30, total)):
                n = items[j]; txt += " " + str(n.get('text',''))
                d = (float(n.get('start',0)) + float(n.get('duration',2))) - ts
                if 30 <= d <= 55:
                    low = txt.lower()
                    for k in kws:
                        if k in low: sc += 3
                    if "?" in txt or "!" in txt: sc += 2
                    if sc > bsc: bsc = sc; bs = ts; bt = txt.strip()
                    break
        ce = min(bs+45, float(items[-1].get('start', bs+45))+4)
        sm = bt[:120] if bt else "Key insights in this clip."
        clips.append({"start": round(bs,1), "end": round(ce,1), "title": f"The {name.split()[0]} You Can't Ignore 🤯",
            "description": f"{sm}... Watch until the end! Subscribe for more.", "tags": ["#shorts","#viral","#insight","#mindset","#trending"],
            "hook_type": name, "reasoning": f"Hook score {bsc} for {name}.", "virality": min(99, 70 + bsc*3)})
    return clips

def algo_longform(items, mins=10):
    total = len(items); num = 8; seg = (mins*60)//num; step = max(1, total//num)
    names = ["The Hook & Master Premise","The Core Problem Unveiled","The Most Common Trap","The Paradigm Shift",
             "The Step-by-Step Strategy","The Surprising Case Study","Mastering the Nuances","The Final Verdict"]
    chs = []
    for i in range(num):
        si = min(i*step, total-1); ts = float(items[si].get('start', i*60))
        chs.append({"chapter_title": names[i], "start": round(ts,1), "end": round(ts+seg,1)})
    return {"title": f"The Complete Masterclass ({mins} Min) 🧠", "summary": f"A high-impact {mins}-minute breakdown.",
            "tags": ["masterclass","summary","key takeaways","deep dive","productivity","best advice"], "chapters": chs}

# --- RENDER ENGINES ---
def render_short(src, start, end, res_key, speed, out):
    d = end - start; scale = res_map.get(res_key, "2160:3840"); pr = "ultrafast" if "Ultra" in speed else "fast"
    subprocess.run([FFMPEG_BIN,"-y","-ss",str(start),"-i",src,"-t",str(d),"-vf",f"crop=ih*(9/16):ih,scale={scale}:flags=fast_bilinear",
        "-c:v","libx264","-preset",pr,"-crf","20","-c:a","aac","-b:a","192k","-movflags","+faststart",out],
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def render_mastercut(src, chapters, res_key, speed, out):
    scale = res_map.get(res_key, "3840:2160"); pr = "ultrafast" if "Ultra" in speed else "fast"; temps = []
    try:
        for i, ch in enumerate(chapters):
            seg = f"tmp_{i}.mp4"; d = float(ch.get("end",60)) - float(ch.get("start",0))
            subprocess.run([FFMPEG_BIN,"-y","-ss",str(ch["start"]),"-i",src,"-t",str(d),"-vf",f"scale={scale}:flags=fast_bilinear",
                "-c:v","libx264","-preset",pr,"-crf","20","-c:a","aac","-b:a","192k",seg],
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            if os.path.exists(seg): temps.append(seg)
        with open("concat.txt","w") as f:
            for t in temps: f.write(f"file '{os.path.abspath(t)}'\n")
        subprocess.run([FFMPEG_BIN,"-y","-f","concat","-safe","0","-i","concat.txt","-c","copy","-movflags","+faststart",out],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    finally:
        for t in temps:
            if os.path.exists(t): os.remove(t)
        if os.path.exists("concat.txt"): os.remove("concat.txt")

# --- FORMAT HELPERS ---
def format_duration(seconds):
    h = int(seconds // 3600); m = int((seconds % 3600) // 60); s = int(seconds % 60)
    if h > 0: return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"

def format_views(count):
    if count >= 1_000_000: return f"{count/1_000_000:.1f}M"
    if count >= 1_000: return f"{count/1_000:.1f}K"
    return str(count)

# --- MAIN INPUT ---
st.markdown('<div class="url-container">', unsafe_allow_html=True)
url_input = st.text_input("🔗 Paste YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...", label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# --- VIDEO PREVIEW ---
if url_input.strip():
    vid_id = extract_video_id(url_input)
    if vid_id:
        with st.spinner("🔍 Fetching video info..."):
            vinfo = get_video_info(url_input)
        if vinfo:
            col_thumb, col_info = st.columns([1, 2])
            with col_thumb:
                if vinfo['thumbnail']:
                    st.image(vinfo['thumbnail'], use_container_width=True)
            with col_info:
                st.markdown(f"### {vinfo['title']}")
                st.markdown(f"**{vinfo['channel']}** · {format_views(vinfo['view_count'])} views · {format_duration(vinfo['duration'])}")
                if "Shorts" in app_mode:
                    st.info(f"🎬 Will generate **5 vertical 4K shorts** from this {format_duration(vinfo['duration'])} video")
                else:
                    st.info(f"🎬 Will create a **{target_duration_min}-minute 4K mastercut** from this {format_duration(vinfo['duration'])} video")
            st.markdown("---")

# --- GENERATE BUTTON ---
if "Shorts" in app_mode:
    btn_label = "⚡ Generate 5x 4K Viral Shorts"
else:
    btn_label = f"⚡ Generate {target_duration_min}-Minute 4K Mastercut"

if st.button(btn_label, type="primary", use_container_width=True):
    if not url_input.strip():
        st.warning("Please paste a YouTube URL.")
    else:
        vid_id = extract_video_id(url_input)
        if not vid_id:
            st.error("Invalid YouTube URL.")
        else:
            # --- ANIMATED PROCESSING UI ---
            status = st.status("⚡ **ClipForge AI** is working...", expanded=True)
            progress = st.progress(0, text="Initializing...")
            start_time = time.time()

            try:
                # Step 1: Transcript
                progress.progress(10, text="📥 Extracting video transcript...")
                status.write("📥 **Step 1/4:** Extracting transcript & captions...")
                transcript_items, t_source = fetch_transcript(url_input, vid_id)
                status.write(f"✅ Transcript loaded — **{len(transcript_items)} lines** via *{t_source}*")
                progress.progress(25, text="✅ Transcript ready")

                # Step 2: Download
                progress.progress(30, text="📥 Downloading video stream...")
                status.write("📥 **Step 2/4:** Downloading video stream...")
                src = f"source_{vid_id}.mp4"
                download_source(url_input, src)
                file_size_mb = round(os.path.getsize(src) / (1024*1024), 1) if os.path.exists(src) else 0
                status.write(f"✅ Source downloaded — **{file_size_mb} MB**")
                progress.progress(50, text="✅ Video downloaded")

                if "Long-Form" in app_mode:
                    # LONG-FORM
                    progress.progress(55, text="🤖 AI analyzing narrative structure...")
                    status.write(f"🤖 **Step 3/4:** AI structuring {target_duration_min}-minute mastercut...")
                    lf = None
                    if "Ollama" in ai_engine:
                        try:
                            cond = "\n".join([f"[{int(t.get('start',0))}s] {t.get('text','')}" for t in transcript_items[::max(1,len(transcript_items)//40)]])[:3000]
                            lf = query_ollama(f"Analyze transcript, return JSON with title, summary, tags, chapters (8 objects with chapter_title/start/end):\n{cond}", ollama_model)
                        except: pass
                    if not lf or not isinstance(lf.get("chapters"), list):
                        lf = algo_longform(transcript_items, target_duration_min)
                    chapters = lf["chapters"]
                    status.write(f"✅ **{len(chapters)} chapters** identified")
                    progress.progress(65, text="✅ Chapters mapped")

                    cur = 0.0; ch_lines = []
                    for c in chapters:
                        m, s = int(cur//60), int(cur%60)
                        ch_lines.append(f"{m:02d}:{s:02d} - {c.get('chapter_title','Insight')}")
                        cur += float(c.get("end",60)) - float(c.get("start",0))
                    desc_text = f"""{lf.get('summary','Ultimate mastercut.')}\n\n⏱️ CHAPTERS:\n{chr(10).join(ch_lines)}\n\n🔔 Subscribe for more!"""

                    progress.progress(70, text="✂️ Rendering 4K mastercut...")
                    status.write(f"✂️ **Step 4/4:** Rendering {target_duration_min}-minute 4K mastercut...")
                    out_name = f"mastercut_{vid_id}_{target_duration_min}min.mp4"
                    render_mastercut(src, chapters, render_resolution, render_speed, out_name)

                    elapsed = round(time.time() - start_time, 1)
                    progress.progress(100, text=f"🎉 Done in {elapsed}s!")
                    if os.path.exists(src): os.remove(src)

                    status.update(label=f"🎉 **{target_duration_min}-Min Mastercut Ready!** ({elapsed}s)", state="complete", expanded=False)
                    st.session_state["mode"] = "longform"
                    st.session_state["longform_output"] = {"file": out_name, "title": lf.get("title", f"Masterclass ({target_duration_min} Min) 🧠"),
                        "description": desc_text, "tags": lf.get("tags", ["masterclass","summary","highlights"])}
                    st.session_state["total_processed"] = total_processed + 1
                    st.session_state["elapsed"] = elapsed

                else:
                    # SHORTS
                    progress.progress(55, text="🤖 AI scanning for viral hooks...")
                    status.write("🤖 **Step 3/4:** AI scanning for viral hooks...")
                    shorts_data = None
                    if "Ollama" in ai_engine:
                        try:
                            cond = "\n".join([f"[{int(t.get('start',0))}s] {t.get('text','')}" for t in transcript_items[::max(1,len(transcript_items)//30)]])[:3000]
                            raw = query_ollama(f"Find 5 viral shorts (30-55s). Return JSON with 'shorts' array:\n{cond}", ollama_model)
                            if raw and isinstance(raw.get("shorts"), list): shorts_data = raw["shorts"]
                        except: pass
                    if not shorts_data: shorts_data = smart_5_shorts(transcript_items)
                    status.write(f"✅ **{len(shorts_data[:5])} viral moments** locked in")
                    progress.progress(65, text="✅ Hooks identified")

                    progress.progress(70, text="✂️ Rendering 5 vertical 4K shorts...")
                    status.write("✂️ **Step 4/4:** Rendering 5 vertical 4K shorts...")
                    rendered = []
                    for i, s in enumerate(shorts_data[:5]):
                        out = f"short_{vid_id}_{i+1}.mp4"
                        pct = 70 + ((i+1) * 6)
                        progress.progress(pct, text=f"🎬 Rendering Short #{i+1}...")
                        status.write(f"🎬 Rendering Short #{i+1} — *{s.get('hook_type','Viral')}*")
                        render_short(src, float(s.get('start',i*45)), float(s.get('end',i*45+40)), render_resolution, render_speed, out)
                        rendered.append((out, s))

                    elapsed = round(time.time() - start_time, 1)
                    progress.progress(100, text=f"🎉 Done in {elapsed}s!")
                    if os.path.exists(src): os.remove(src)

                    status.update(label=f"🎉 **5x 4K Shorts Ready!** ({elapsed}s)", state="complete", expanded=False)
                    st.session_state["mode"] = "shorts"
                    st.session_state["shorts_output"] = rendered
                    st.session_state["total_processed"] = total_processed + 1
                    st.session_state["elapsed"] = elapsed

            except Exception as e:
                progress.progress(100, text="❌ Error")
                status.update(label="❌ Error", state="error", expanded=True)
                st.error(f"Error: {str(e)}")

# --- DISPLAY RESULTS ---
if st.session_state.get("mode") == "longform" and "longform_output" in st.session_state:
    st.markdown("---")
    elapsed = st.session_state.get("elapsed", 0)
    d = st.session_state["longform_output"]

    st.markdown(f"""
    <div class="result-card">
        <div class="result-header">
            <div class="result-title">🎬 Your 4K Long-Form Mastercut</div>
            <span class="quality-badge">4K ULTRA HD</span>
        </div>
        <div style="color: rgba(255,255,255,0.5); font-size: 0.85rem;">Processed in {elapsed}s · Ready to upload</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1.2, 1])
    with c1:
        if os.path.exists(d["file"]):
            st.video(d["file"])
            with open(d["file"], "rb") as f:
                st.download_button("⬇️ Download 4K Mastercut (MP4)", f, file_name=d["file"], mime="video/mp4", use_container_width=True)
    with c2:
        st.markdown('<div class="meta-card"><div class="meta-label">🔥 YouTube Title</div>', unsafe_allow_html=True)
        st.text_input("Title", value=d["title"], label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="meta-card"><div class="meta-label">📄 Description & Chapters</div>', unsafe_allow_html=True)
        st.text_area("Desc", value=d["description"], height=200, label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="meta-card"><div class="meta-label">🏷️ Search Tags</div>', unsafe_allow_html=True)
        tags = " ".join(d["tags"]) if isinstance(d["tags"], list) else d["tags"]
        st.text_input("Tags", value=tags, label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.get("mode") == "shorts" and "shorts_output" in st.session_state:
    st.markdown("---")
    elapsed = st.session_state.get("elapsed", 0)

    st.markdown(f"""
    <div class="result-card">
        <div class="result-header">
            <div class="result-title">🎬 Your 5 4K Viral Shorts</div>
            <span class="quality-badge">4K · 9:16 VERTICAL</span>
        </div>
        <div style="color: rgba(255,255,255,0.5); font-size: 0.85rem;">Processed in {elapsed}s · Ready to upload to YouTube Shorts / TikTok / Reels</div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs([f"📱 #{i+1}: {d.get('hook_type','Viral')}" for i, (_, d) in enumerate(st.session_state["shorts_output"])])
    for i, tab in enumerate(tabs):
        with tab:
            fp, meta = st.session_state["shorts_output"][i]
            virality = meta.get("virality", 85)
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown(f"""
                <div style="text-align:center; margin-bottom:10px;">
                    <span style="background:linear-gradient(135deg,#10b981,#059669); color:white; padding:4px 14px; border-radius:20px; font-size:0.8rem; font-weight:700;">
                        🔥 {virality}/100 Viral Score
                    </span>
                </div>
                """, unsafe_allow_html=True)
                if os.path.exists(fp):
                    st.video(fp)
                    with open(fp, "rb") as f:
                        st.download_button(f"⬇️ Download Short #{i+1}", f, file_name=fp, mime="video/mp4", use_container_width=True, key=f"dl_{i}")
            with c2:
                st.markdown('<div class="meta-card"><div class="meta-label">🔥 Shorts Title</div>', unsafe_allow_html=True)
                st.text_input(f"T{i}", value=meta.get("title",""), label_visibility="collapsed", key=f"t_{i}")
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('<div class="meta-card"><div class="meta-label">📄 Description</div>', unsafe_allow_html=True)
                st.text_area(f"D{i}", value=meta.get("description",""), height=80, label_visibility="collapsed", key=f"d_{i}")
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('<div class="meta-card"><div class="meta-label">🏷️ Hashtags</div>', unsafe_allow_html=True)
                tg = " ".join(meta.get("tags",[])) if isinstance(meta.get("tags"), list) else meta.get("tags","")
                st.text_input(f"TG{i}", value=tg, label_visibility="collapsed", key=f"tg_{i}")
                st.markdown('</div>', unsafe_allow_html=True)

                with st.expander("💡 Hook Analysis"):
                    st.write(f"**Hook:** {meta.get('hook_type')}")
                    st.write(f"**Window:** `{meta.get('start')}s` → `{meta.get('end')}s` ({round(float(meta.get('end',0))-float(meta.get('start',0)),1)}s)")
                    st.write(f"**Why:** {meta.get('reasoning')}")
