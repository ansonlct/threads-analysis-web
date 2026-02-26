import re
import requests
import html
import codecs
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# ==========================================
# 您的核心 Python 邏輯 (完全保留原本的抓取功能)
# ==========================================
def get_post_absolute_time(url):
    if not url or "threads.net" not in url and "threads.com" not in url:
        return ""
    post_id_match = re.search(r'/post/([^/?]+)', url)
    post_id = post_id_match.group(1) if post_id_match else ""
    url = url.replace("threads.com", "threads.net")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""
        page_html = response.text
        if post_id:
            specific_pattern = rf'"{post_id}".*?"taken_at"\s*:\s*(\d{{10}})'
            match = re.search(specific_pattern, page_html)
            if match:
                return format_timestamp(match.group(1))
        time_patterns = [
            r'"taken_at"\s*:\s*(\d{10})',
            r'"published_at"\s*:\s*(\d{10})',
            r'"created_at"\s*:\s*(\d{10})',
            r'datetime="([^"]+)"'
        ]
        for pattern in time_patterns:
            match = re.search(pattern, page_html)
            if match:
                time_data = match.group(1)
                if time_data.isdigit() and len(time_data) == 10:
                    return format_timestamp(time_data)
                elif "T" in time_data:
                     dt_str = time_data.split('+')[0].split('Z')[0]
                     dt_object = datetime.fromisoformat(dt_str)
                     return dt_object.strftime("%Y-%m-%d %H%M")
        return ""
    except Exception:
        return ""

def format_timestamp(timestamp_str):
    timestamp = int(timestamp_str)
    dt_object = datetime.fromtimestamp(timestamp)
    return dt_object.strftime("%Y-%m-%d %H%M")

def get_meta_user_info(username):
    if not username:
        return "", ""
    clean_username = username.strip().lstrip('@')
    url = f"https://www.threads.net/@{clean_username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive"
    }
    user_id = ""
    display_name = ""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return "", ""
        page_html = response.text
        id_patterns = [
            r'barcelona://user\?username=[^&]+&amp;id=(\d+)',
            r'barcelona://user\?username=[^&]+&id=(\d+)',
            r'instagram://user\?username=[^&]+&amp;id=(\d+)',
            r'instagram://user\?username=[^&]+&id=(\d+)',
            r'"profile_id":"(\d+)"',
            r'"user_id":"(\d+)"'
        ]
        for pattern in id_patterns:
            match = re.search(pattern, page_html)
            if match:
                user_id = match.group(1)
                break
        title_match = re.search(r'<title>(.*?) \(@', page_html)
        if title_match:
             display_name = html.unescape(title_match.group(1))
        if not display_name:
             name_patterns = [
                 rf'"username":"{clean_username}".*?"full_name":"([^"]+)"',
                 r'"full_name":"([^"]+)"'
             ]
             for pattern in name_patterns:
                 match = re.search(pattern, page_html)
                 if match:
                     name_raw = match.group(1)
                     try:
                         name_decoded = codecs.decode(name_raw.encode('ascii'), 'unicode_escape')
                         name = html.unescape(name_decoded)
                     except Exception:
                         name = html.unescape(name_raw)
                     if len(name) > 0 and not name.startswith("{"):
                         display_name = name
                         break
        if not display_name:
            display_name = clean_username
        return user_id, display_name
    except Exception:
        return "", ""

def sanitize_text(text):
    text = text.replace('\ufffc', '')
    text = text.replace('￼', '')
    return text

# ==========================================
# Flask 路由與網頁介面 (HTML)
# ==========================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Threads Post Analysis Web</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f9; margin: 0; padding: 20px; display: flex; justify-content: center; }
        .container { background-color: white; width: 100%; max-width: 700px; padding: 25px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        h2 { margin-top: 0; font-size: 22px; color: #333; }
        label { font-weight: bold; font-size: 14px; display: block; margin-bottom: 5px; margin-top: 15px; color: #444; }
        input[type="text"], textarea { width: 100%; padding: 12px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-family: inherit; font-size: 14px; }
        textarea { resize: vertical; }
        .btn-group { display: flex; gap: 15px; margin-top: 10px; margin-bottom: 15px; }
        button { flex: 1; padding: 12px; font-size: 16px; font-weight: bold; border: none; border-radius: 4px; cursor: pointer; color: white; transition: opacity 0.2s; }
        button:hover { opacity: 0.9; }
        button:disabled { background-color: #ccc !important; cursor: not-allowed; }
        .btn-submit { background-color: #FF5722; }
        .btn-copy { background-color: #2196F3; }
    </style>
</head>
<body>

<div class="container">
    <h2>Threads Post Analysis Web 🚀</h2>
    
    <label>URL (用於抓取精確時間) (可選):</label>
    <input type="text" id="url_input" placeholder="貼上 Threads 連結...">

    <label>CONTENT (複製內容):</label>
    <textarea id="content_input" rows="8" placeholder="貼上 Threads 複製的內容..."></textarea>

    <div class="btn-group">
        <button id="convert_btn" class="btn-submit" onclick="submitData()">Submit</button>
        <button id="copy_btn" class="btn-copy" onclick="copyToClipboard()">Copy</button>
    </div>

    <label>轉換結果:</label>
    <textarea id="output_text" rows="14" readonly></textarea>
</div>

<script>
    async function submitData() {
        const urlInput = document.getElementById("url_input").value;
        const contentInput = document.getElementById("content_input").value;
        const btn = document.getElementById("convert_btn");
        const output = document.getElementById("output_text");
        
        btn.innerText = "⏳ 正在深度挖掘資料...";
        btn.disabled = true;
        
        try {
            const response = await fetch("/process", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: urlInput, content: contentInput })
            });
            const data = await response.json();
            output.value = data.result;
        } catch (error) {
            output.value = "發生錯誤：" + error.message;
        } finally {
            btn.innerText = "Submit";
            btn.disabled = false;
        }
    }

    function copyToClipboard() {
        const outputText = document.getElementById("output_text");
        outputText.select();
        document.execCommand("copy");
        alert("已成功複製到剪貼簿！");
    }
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/process", methods=["POST"])
def process_data():
    data = request.json
    raw_content = sanitize_text(data.get("content", "").strip())
    url = data.get("url", "").strip()

    if url.upper().startswith("URL:"):
        url = url[4:].strip()
    if raw_content.upper().startswith("CONTENT:"):
        raw_content = raw_content[8:].strip()
        
    url_user_match = re.search(r'(@[a-zA-Z0-9_.]+)', url)
    expected_user_from_url = url_user_match.group(1) if url_user_match else ""
    
    raw_lines = raw_content.splitlines()
    lines = [line.strip() for line in raw_lines]
    
    threads_page = ""
    reply_content = ""
    original_text = ""
    reply_idx = -1
    detected_user_from_content = ""

    for i in range(len(lines) - 1, -1, -1):
        if "正在回覆" in lines[i]:
            reply_idx = i
            page_match = re.search(r'正在回覆\s*(@[a-zA-Z0-9_.]+)', lines[i])
            if page_match:
                threads_page = page_match.group(1)
            for j in range(1, 6): 
                if i - j >= 0 and lines[i-j]: 
                    if not re.search(r'\d+(秒|分|分鐘|小時|日|天|週|星期)', lines[i-j]) and not re.search(r'\d{4}-\d{2}-\d{2}', lines[i-j]) and not lines[i-j].isdigit() and lines[i-j] != "/":
                        detected_user_from_content = "@" + lines[i-j] if not lines[i-j].startswith('@') else lines[i-j]
                        break
            break 

    is_reply = (reply_idx != -1)
    if not is_reply and len(lines) > 0:
        detected_user_from_content = "@" + lines[0] if not lines[0].startswith('@') else lines[0]

    if expected_user_from_url and detected_user_from_content:
        if expected_user_from_url.lower() != detected_user_from_content.lower():
            error_msg = f"==========================================\n"
            error_msg += f"⚠️ 警告：資料不一致，請檢查複製內容！ ⚠️\n"
            error_msg += f"==========================================\n\n"
            error_msg += f"👉 網址 (URL) 中的發文者是： {expected_user_from_url}\n"
            error_msg += f"👉 內容 (CONTENT) 的發文者是： {detected_user_from_content}\n\n"
            error_msg += f"因為兩者不符，程式已停止解析。\n"
            return jsonify({"result": error_msg})

    threads_user = detected_user_from_content if detected_user_from_content else expected_user_from_url

    if is_reply:
        reply_lines = lines[reply_idx+1:]
        while reply_lines and not reply_lines[0]:
            reply_lines.pop(0)
        reply_content = "\n".join(reply_lines).strip()
        
        original_end = -1
        original_start = -1
        for i in range(reply_idx - 1, -1, -1):
            if lines[i] == threads_user.lstrip('@') or lines[i] == threads_user:
                original_end = i
                break
        if original_end != -1:
            for i in range(original_end - 1, -1, -1):
                if re.search(r'^\d+(秒|分|分鐘|小時|日|天|週|星期)$', lines[i]) or re.search(r'^\d{4}-\d{2}-\d{2}$', lines[i]):
                    if i + 1 < len(lines) and "正在回覆" in lines[i+1]:
                        original_start = i + 2
                    else:
                        original_start = i + 1
                    break
        if original_start != -1 and original_end != -1 and original_start < original_end:
            raw_original_lines = lines[original_start:original_end]
            cleaned_original = []
            for line in raw_original_lines:
                if not re.search(r'^(\d+|/)$', line):
                    cleaned_original.append(line)
            while len(cleaned_original) > 0 and cleaned_original[0] == "":
                cleaned_original.pop(0)
            while len(cleaned_original) > 0 and cleaned_original[-1] == "":
                cleaned_original.pop()
            original_text = "\n".join(cleaned_original).strip()
            
        if not threads_page and len(lines) > 0:
            threads_page = "@" + lines[0] if not lines[0].startswith('@') else lines[0]
    else:
        time_idx = -1
        for i, line in enumerate(lines):
            if re.search(r'^\d+(秒|分|分鐘|小時|日|天|週|星期)$', line) or re.search(r'^\d{4}-\d{2}-\d{2}$', line):
                time_idx = i
                break
        if time_idx != -1:
            reply_content = "\n".join(lines[time_idx+1:]).strip()
        else:
            reply_content = "\n".join(lines).strip()

    threads_user_id, threads_user_name = get_meta_user_info(threads_user)
    
    threads_page_id, threads_page_name = "", ""
    if is_reply:
        threads_page_id, threads_page_name = get_meta_user_info(threads_page)
        
    absolute_time = get_post_absolute_time(url)
    user_display = f"{threads_user}"
    if threads_user_name:
        user_display = f"{threads_user_name} {threads_user}"
        
    if is_reply:
        page_display = f"{threads_page}"
        if threads_page_name:
            page_display = f"{threads_page_name} {threads_page}"
            
    output = f"URL: {url}\n"
    if is_reply:
        output += f"Threads Page: {page_display}\n"
        output += f"Threads Page ID: {threads_page_id}\n"
        
    output += f"Threads User: {user_display}\n"
    output += f"Threads User ID: {threads_user_id}\n"
    output += f"Date/Time: {absolute_time if absolute_time else ''}\n"
    
    if is_reply:
        if original_text:
            output += f"Content: [[回覆 {page_display} 串文: {original_text}]]\n"
        else:
            output += f"Content: [[回覆 {page_display} 串文]]\n"
        output += f"{reply_content}" 
    else:
        output += f"Content: {reply_content}"

    return jsonify({"result": output})

if __name__ == "__main__":
    # 雲端環境會自動分配 PORT，若沒有則預設使用 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

