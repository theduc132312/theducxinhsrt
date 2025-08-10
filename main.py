#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
theducxinhsrt - desktop SRT translator (uses Gemini via google-generativeai)
- GUI: PySimpleGUI
- Features: load .srt, fix timestamp overlaps (start_next = end_prev), choose language & mode,
  call Gemini to translate in chunks, preview and export .srt translated.
Author: prepared for you
"""

import re
import time
import threading
import json
import os
from pathlib import Path

try:
    import PySimpleGUI as sg
except Exception:
    raise RuntimeError("Please install PySimpleGUI (pip install PySimpleGUI) to run this app")

# try to import Gemini client
try:
    import google.generativeai as genai
    HAS_GENAI = True
except Exception:
    HAS_GENAI = False

# --------- SRT parsing/format/util ----------
SRT_BLOCK_RE = re.compile(r"(\d+)\s+((?:\d{2}:){2}\d{2},\d{3})\s+-->\s+((?:\d{2}:){2}\d{2},\d{3})\s+(.*?)(?=\n\n|\Z)", re.S)

def time_to_ms(t):
    # t = "HH:MM:SS,mmm"
    try:
        h, m, s_ms = t.split(":", 2)
        s, ms = s_ms.split(",", 1)
        return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)
    except Exception:
        return 0

def ms_to_time(ms):
    h = ms // 3600000
    ms = ms % 3600000
    m = ms // 60000
    ms = ms % 60000
    s = ms // 1000
    ms = ms % 1000
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def parse_srt(text):
    blocks = []
    for m in SRT_BLOCK_RE.finditer(text):
        idx = int(m.group(1))
        start = m.group(2)
        end = m.group(3)
        content = m.group(4).strip().replace('\r','')
        blocks.append({"index": idx, "start": start, "end": end, "text": content})
    return blocks

def srt_to_text(blocks):
    parts = []
    for b in blocks:
        parts.append(f"{b['index']}\n{b['start']} --> {b['end']}\n{b['text']}\n")
    return "\n".join(parts).strip()

def fix_timestamps_nocross(blocks, min_display_ms=800):
    """
    Ensure each block is valid and start of next >= end previous.
    If end <= start, extend end = start + min_display_ms
    If start_next < end_prev -> set start_next = end_prev
    """
    fixed = []
    for i, b in enumerate(blocks):
        start = b["start"]
        end = b["end"]
        # validate format, fallback to 00:00:00,000
        if not re.match(r"^(?:\d{2}:){2}\d{2},\d{3}$", start):
            start = "00:00:00,000"
        if not re.match(r"^(?:\d{2}:){2}\d{2},\d{3}$", end):
            end = ms_to_time(time_to_ms(start) + min_display_ms)

        # if end <= start -> extend end
        if time_to_ms(end) <= time_to_ms(start):
            end = ms_to_time(time_to_ms(start) + min_display_ms)

        # if overlaps with previous: set start = prev_end
        if i > 0:
            prev_end = fixed[-1]["end"]
            if time_to_ms(start) < time_to_ms(prev_end):
                start = prev_end
                # ensure end > start
                if time_to_ms(end) <= time_to_ms(start):
                    end = ms_to_time(time_to_ms(start) + min_display_ms)
        fixed.append({"index": b["index"], "start": start, "end": end, "text": b["text"]})
    return fixed

def chunk_blocks(blocks, max_blocks=30):
    chunks = []
    cur = []
    for b in blocks:
        cur.append(b)
        if len(cur) >= max_blocks:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks

# --------- Gemini prompt builder ----------
PROMPT_BASE = """
Bạn hãy dịch các đoạn phụ đề sau theo các yêu cầu:
- Giữ nguyên thứ tự và timecode (start/end).
- Không thay đổi số dòng hoặc thêm câu mới.
- Không để câu dịch chồng ý với dòng trước; đảm bảo mạch văn nối tiếp.
- Nếu chế độ 'Mượt-hài' thì dịch tự nhiên, mượt, có chút hài hước nhẹ (không lố).
- Nếu chế độ 'Nhanh' thì dịch gọn, sát nghĩa, ít xử lý.
- Giữ nguyên tên nhân vật/thuật ngữ.
Trả về định dạng .srt (index \\n start --> end \\n translated_text).
"""

def build_prompt_for_chunk(chunk_blocks, target_lang, mode):
    header = f"Target language: {target_lang}\nMode: {mode}\n"
    body = []
    for b in chunk_blocks:
        body.append(f"{b['index']}\n{b['start']} --> {b['end']}\n{b['text']}\n")
    return header + PROMPT_BASE + "\n\n" + "\n".join(body)

# --------- Gemini translation call ----------
def translate_chunk_gemini(api_key, model, prompt_text, timeout=60):
    if not HAS_GENAI:
        return None, "google.generativeai not installed"
    try:
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(model)
        resp = model_obj.generate_content(prompt_text, timeout=timeout)
        return resp.text.strip(), None
    except Exception as e:
        return None, str(e)

def parse_translated_text_to_blocks(text):
    # parse .srt-style blocks from model output
    blocks = []
    for m in SRT_BLOCK_RE.finditer(text + "\n\n"):
        idx = int(m.group(1))
        start = m.group(2)
        end = m.group(3)
        content = m.group(4).strip()
        blocks.append({"index": idx, "start": start, "end": end, "text": content})
    return blocks

# --------- GUI & App logic ----------
sg.theme('DefaultNoMoreNagging')

LANG_MAP = {
    "Tiếng Việt": "vi",
    "English": "en",
    "Français": "fr",
    "Español": "es"
}

layout = [
    [sg.Text('theducxinhsrt - SRT Translator', font=('Helvetica', 16))],
    [sg.Text('API Key (Gemini)'), sg.Input(key='-APIKEY-', size=(60,1)), sg.Button('Save Key', key='-SAVEKEY-')],
    [sg.Text('Model:'), sg.Combo(['gemini-2.0-flash','gemini-1.5-flash','gemini-1.5-pro'], default_value='gemini-2.0-flash', key='-MODEL-')],
    [sg.Text('Chọn ngôn ngữ đích:'), sg.Combo(list(LANG_MAP.keys()), default_value='Tiếng Việt', key='-LANG-')],
    [sg.Text('Chế độ dịch:'), sg.Radio('Mượt + Hài (mặc định)', 'MODE', default=True, key='-MODE_SMOOTH-'), sg.Radio('Nhanh (ít tốn token)', 'MODE', key='-MODE_FAST-')],
    [sg.HorizontalSeparator()],
    [sg.Text('Chọn file .srt:'), sg.Input(key='-FILE-', enable_events=True, size=(60,1)), sg.FileBrowse(file_types=(("SRT Files","*.srt"),)), sg.Button('Load', key='-LOAD-')],
    [sg.Progress(1, orientation='h', size=(40, 20), key='-PROG-'), sg.Text('', key='-STATUS-')],
    [sg.Button('Check & Fix Timestamps', key='-FIX-'), sg.Button('Translate', key='-TRANSLATE-'), sg.Button('Export .srt', key='-EXPORT-'), sg.Button('Quit')],
    [sg.Text('Log:')],
    [sg.Multiline('', size=(120,10), key='-LOG-')]
]

window = sg.Window('theducxinhsrt', layout, finalize=True)

# App state
app_blocks = []
translated_blocks = []
current_input_path = None
config_path = Path.home() / ".theducxinhsrt_config.json"

def log(msg):
    t = time.strftime("%H:%M:%S")
    prev = window['-LOG-'].get()
    window['-LOG-'].update(prev + f"[{t}] {msg}\n")

def save_api_key_local(key):
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump({"api_key": key}, f)
        log("API key saved locally.")
    except Exception as e:
        log("Failed to save API key: " + str(e))

def load_api_key_local():
    try:
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding='utf-8'))
            return data.get("api_key","")
    except Exception:
        return ""
    return ""

def load_srt_file(path):
    global app_blocks, translated_blocks, current_input_path
    try:
        txt = open(path, 'r', encoding='utf-8').read()
    except Exception:
        txt = open(path, 'r', encoding='latin-1').read()
    app_blocks = parse_srt(txt)
    app_blocks = fix_timestamps_nocross(app_blocks)
    translated_blocks = [{'index': b['index'], 'start': b['start'], 'end': b['end'], 'text': ''} for b in app_blocks]
    current_input_path = path
    log(f"Loaded {len(app_blocks)} blocks from {path}")

def export_srt(path_out):
    out_blocks = []
    for i, b in enumerate(app_blocks):
        tb = translated_blocks[i] if i < len(translated_blocks) else {}
        text = tb.get('text') if tb.get('text') else b['text']
        out_blocks.append({'index': b['index'], 'start': b['start'], 'end': b['end'], 'text': text})
    s = srt_to_text(out_blocks)
    with open(path_out, 'w', encoding='utf-8') as f:
        f.write(s)
    log("Exported translated SRT: " + path_out)

# Threaded translation to avoid blocking GUI
def do_translate(api_key, model, target_lang, mode):
    global translated_blocks, app_blocks
    if not app_blocks:
        log("No SRT loaded.")
        return
    log("Start translation... (this may take a while for large files)")
    chunks = chunk_blocks(app_blocks, max_blocks=25)
    total_chunks = len(chunks)
    completed = 0
    new_translated = []
    for ch in chunks:
        prompt = build_prompt_for_chunk(ch, target_lang, mode)
        txt, err = translate_chunk_gemini(api_key, model, prompt) if HAS_GENAI else (None, "google.generativeai not installed")
        if err:
            log(f"API error (chunk): {err}. Falling back to copy original text for this chunk.")
            for b in ch:
                new_translated.append({'index': b['index'], 'start': b['start'], 'end': b['end'], 'text': b['text']})
        else:
            parsed = parse_translated_text_to_blocks(txt)
            if not parsed:
                log("Warning: parsed 0 blocks from API response; copying originals for chunk.")
                for b in ch:
                    new_translated.append({'index': b['index'], 'start': b['start'], 'end': b['end'], 'text': b['text']})
            else:
                new_translated.extend(parsed)
        completed += 1
        progress = int((completed/total_chunks)*100)
        try:
            window['-PROG-'].update_bar(progress)
            window['-STATUS-'].update(f"{progress}%")
        except Exception:
            pass
        time.sleep(0.1)
    # map back to translated_blocks aligned by index
    idx_map = {b['index']: i for i,b in enumerate(app_blocks)}
    translated_blocks = [{'index': b['index'], 'start': b['start'], 'end': b['end'], 'text': ''} for b in app_blocks]
    for t in new_translated:
        if t['index'] in idx_map:
            translated_blocks[idx_map[t['index']]]['text'] = t['text']
    # final pass: ensure no overlaps after any slight time shifts
    for i in range(1, len(app_blocks)):
        prev_end = translated_blocks[i-1]['end']
        this_start = translated_blocks[i]['start']
        if time_to_ms(this_start) < time_to_ms(prev_end):
            translated_blocks[i]['start'] = prev_end
            # ensure end > start (keep original duration if possible)
            orig_end = translated_blocks[i]['end']
            if time_to_ms(orig_end) <= time_to_ms(prev_end):
                translated_blocks[i]['end'] = ms_to_time(time_to_ms(prev_end) + 800)
    window['-PROG-'].update_bar(100)
    window['-STATUS-'].update("100%")
    log("Translation finished.")

# GUI loop
# pre-load any saved key
saved = load_api_key_local()
if saved:
    window['-APIKEY-'].update(saved)

while True:
    event, values = window.read(timeout=100)
    if event == sg.WIN_CLOSED or event == 'Quit':
        break
    if event == '-SAVEKEY-':
        k = values['-APIKEY-'].strip()
        if not k:
            sg.popup("Please enter a non-empty API key")
        else:
            save_api_key_local(k)
    if event == '-LOAD-':
        path = values['-FILE-']
        if path and os.path.exists(path):
            load_srt_file(path)
        else:
            sg.popup("Please select a valid .srt file")
    if event == '-FIX-':
        if app_blocks:
            app_blocks = fix_timestamps_nocross(app_blocks)
            # reset translated_blocks
            translated_blocks = [{'index': b['index'], 'start': b['start'], 'end': b['end'], 'text': ''} for b in app_blocks]
            log("Timestamps checked & fixed (no overlaps).")
        else:
            sg.popup("No file loaded")
    if event == '-TRANSLATE-':
        if not app_blocks:
            sg.popup("No SRT loaded")
            continue
        api_key = values['-APIKEY-'].strip()
        if not api_key:
            # try config
            api_key = load_api_key_local()
            if not api_key:
                sg.popup("Please enter or save your Gemini API key first")
                continue
        model = values['-MODEL-']
        lang_choice = values['-LANG-']
        target_lang = LANG_MAP.get(lang_choice, 'vi')
        mode = "Mượt-hài" if values['-MODE_SMOOTH-'] else "Nhanh"
        # start thread
        t = threading.Thread(target=do_translate, args=(api_key, model, target_lang, mode), daemon=True)
        t.start()
    if event == '-EXPORT-':
        if not app_blocks:
            sg.popup("No file loaded")
            continue
        # choose filename
        default_name = "translated.srt"
        if current_input_path:
            stem = Path(current_input_path).stem
            default_name = f"{stem}_translated.srt"
        out = sg.popup_get_file('Save translated SRT as', save_as=True, no_window=True, default_extension='.srt', file_types=(("SRT Files","*.srt"),), default_path=default_name)
        if out:
            export_srt(out)
            sg.popup("Saved to " + out)
    # small sleep handled by read timeout

window.close()
