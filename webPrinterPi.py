import os
import re
import json
import uuid
import shutil
import subprocess
from datetime import datetime
from flask import Flask, render_template, request, redirect, flash, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey_for_sun_v2"

BASE_DIR = os.path.expanduser('~/web-printerPi')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
HISTORY_FOLDER = os.path.join(BASE_DIR, 'history')
HISTORY_FILE = os.path.join(HISTORY_FOLDER, 'history.json')
MAX_HISTORY_ITEMS = 10

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(HISTORY_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'txt', 'doc', 'docx'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_history(items):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_to_history(processed_filepath, display_name, settings):
    if not os.path.exists(processed_filepath):
        return
    history = load_history()
    item_id = uuid.uuid4().hex[:10]
    ext = os.path.splitext(processed_filepath)[1]
    stored_filename = f"{item_id}{ext}"
    stored_path = os.path.join(HISTORY_FOLDER, stored_filename)

    try:
        shutil.copy2(processed_filepath, stored_path)
    except Exception:
        return

    entry = {
        "id": item_id,
        "filename": display_name,
        "stored_filename": stored_filename,
        "timestamp": datetime.now().strftime("%d/%m %H:%M"),
        "settings": settings,
    }
    history.insert(0, entry)

    # ลบรายการที่เกิน MAX_HISTORY_ITEMS พร้อมไฟล์เก่า
    for old_item in history[MAX_HISTORY_ITEMS:]:
        old_file = os.path.join(HISTORY_FOLDER, old_item.get("stored_filename", ""))
        if os.path.exists(old_file):
            try:
                os.remove(old_file)
            except Exception:
                pass

    save_history(history[:MAX_HISTORY_ITEMS])


def convert_to_pdf_if_needed(filepath):
    ext = filepath.rsplit('.', 1)[1].lower()
    if ext in ['doc', 'docx']:
        pdf_dir = os.path.dirname(filepath)
        try:
            subprocess.run(
                ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", pdf_dir, filepath],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            pdf_path = os.path.join(pdf_dir, f"{base_name}.pdf")
            if os.path.exists(filepath):
                os.remove(filepath)
            return pdf_path
        except subprocess.CalledProcessError:
            return filepath
    return filepath


def is_valid_pdf(filepath):
    try:
        with open(filepath, 'rb') as f:
            header = f.read(1024).lstrip()
            if not header.startswith(b'%PDF'):
                return False
            f.seek(0, os.SEEK_END)
            size = f.tell()
            tail_size = min(1024, size)
            f.seek(-tail_size, os.SEEK_END)
            return b'%%EOF' in f.read(tail_size)
    except Exception:
        return False


def normalize_pdf(filepath):
    try:
        pdf_dir = os.path.dirname(filepath)
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        normalized_path = os.path.join(pdf_dir, f"{base_name}.normalized.pdf")
        subprocess.run(
            [
                "gs", "-q", "-dNOPAUSE", "-dBATCH",
                "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
                "-dPDFSETTINGS=/printer", "-dAutoRotatePages=/PageByPage",
                f"-sOutputFile={normalized_path}", filepath,
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if os.path.exists(normalized_path):
            if os.path.exists(filepath) and filepath != normalized_path:
                os.remove(filepath)
            return normalized_path
    except Exception:
        pass
    return filepath


def sanitize_page_ranges(raw_ranges):
    if not raw_ranges:
        return ""
    cleaned = re.sub(r'\s+', '', raw_ranges)
    if re.match(r'^\d+(-\d+)?(,\d+(-\d+)?)*$', cleaned):
        return cleaned
    return ""


def build_print_command(
    printer_name,
    filepath,
    print_mode="bw",
    copies=1,
    paper_size="A4",
    print_quality="normal",
    orientation="portrait",
    page_ranges="",
    duplex="one-sided",
    scaling="fit",
):
    command = ["lp", "-d", printer_name]
    command.extend(["-o", "ColorModel=RGB" if print_mode == "color" else "ColorModel=Gray"])

    if paper_size:
        command.extend(["-o", f"media={paper_size}"])
    if print_quality:
        command.extend(["-o", f"print-quality={print_quality}"])
    if orientation in ["portrait", "landscape"]:
        value = "3" if orientation == "portrait" else "4"
        command.extend(["-o", f"orientation-requested={value}", "-o", orientation])

    # 1. ช่วงหน้า (Page Range)
    valid_ranges = sanitize_page_ranges(page_ranges)
    if valid_ranges:
        command.extend(["-o", f"page-ranges={valid_ranges}"])

    # 2. พิมพ์ 2 หน้า (Duplex)
    valid_sides = {"one-sided", "two-sided-long-edge", "two-sided-short-edge"}
    if duplex in valid_sides:
        command.extend(["-o", f"sides={duplex}"])

    # 3. การปรับขนาด (Fit to page vs 100%)
    if scaling == "fit":
        command.extend(["-o", "fit-to-page"])
    else:
        command.extend(["-o", "scaling=100"])

    if copies and copies > 1:
        command.extend(["-n", str(copies)])

    command.append(filepath)
    return command


def parse_job_status(detail_output, queue_output=""):
    combined = "\n".join([p for p in [detail_output, queue_output] if p]).lower()
    if not combined:
        return None, None
    if any(k in combined for k in ["completed", "finished", "done"]):
        return "completed", "เสร็จสิ้น"
    if any(k in combined for k in ["active", "job-printing", "printing", "processing", "busy"]):
        return "printing", "กำลังพิมพ์"
    if any(k in combined for k in ["pending", "queued", "waiting", "held"]):
        return "queued", "รอคิว"
    return None, None


def parse_job_progress(detail_output, queue_output=""):
    combined = "\n".join([p for p in [detail_output, queue_output] if p])
    for line in combined.splitlines():
        lower_line = line.lower()
        if not any(k in lower_line for k in ["percent", "progress", "completed", "processed", "printed", "remaining", "job", "print"]):
            continue
        if any(k in lower_line for k in ["color", "colour", "black", "toner", "ink", "cyan", "magenta", "yellow"]):
            continue
        match = re.search(r"(\d{1,3})%", line)
        if match and 0 <= int(match.group(1)) <= 100:
            return int(match.group(1))
    return None


def parse_printer_jobs(printer_name, queue_output=""):
    """ดึงรายการคิวงานพิมพ์ทั้งหมดของเครื่องพิมพ์นี้"""
    active_job_ids = set()
    for line in queue_output.splitlines():
        if "active" in line.lower():
            m = re.search(r'\b(\d+)\b', line)
            if m:
                active_job_ids.add(m.group(1))

    jobs = []
    try:
        lpstat_output = subprocess.check_output(["lpstat", "-o", printer_name]).decode("utf-8", "ignore")
        for idx, line in enumerate(lpstat_output.splitlines()):
            line = line.strip()
            if not line:
                continue
            parts = re.split(r'\s+', line, maxsplit=3)
            if len(parts) >= 2:
                job_id = parts[0]
                user = parts[1] if len(parts) >= 2 else ""
                rest = parts[3].strip() if len(parts) >= 4 else ""
                # ตัดชื่อไฟล์ออกจาก size/date ท้ายบรรทัดของ lpstat -o ถ้ามี
                filename = re.sub(r'\s+\d+\s+[A-Za-z]{3}\s+.*$', '', rest).strip() or job_id
                numeric_id = job_id.rsplit('-', 1)[-1] if '-' in job_id else job_id
                is_active = (numeric_id in active_job_ids) or (idx == 0 and not active_job_ids)

                jobs.append({
                    "job_id": job_id,
                    "user": user,
                    "filename": filename,
                    "state": "printing" if is_active else "queued",
                    "state_label": "กำลังพิมพ์" if is_active else "รอคิว"
                })
    except Exception:
        pass
    return jobs


def parse_printer_status(line, detail_output, queue_output="", jobs=None):
    jobs = jobs or []
    lower_line = line.lower()
    lower_detail = detail_output.lower()
    lower_queue = queue_output.lower()

    job_state, job_state_label = parse_job_status(detail_output, queue_output)
    if any(j["state"] == "printing" for j in jobs) or job_state == "printing":
        status = "กำลังพิมพ์"
    elif len(jobs) > 0 or job_state == "queued":
        status = "รอคิว"
    elif job_state == "completed":
        status = "เสร็จสิ้น"
    elif any(k in lower_line for k in ["is idle", "accepting jobs", "idle", "อยู่นิ่ง"]):
        status = "พร้อมใช้งาน"
    elif any(k in lower_line for k in ["printing", "busy", "processing"]) or any(k in lower_queue for k in ["active", "กำลังพิมพ์"]):
        status = "กำลังพิมพ์"
    else:
        status = "ไม่ทราบ"

    color_percent = None
    bw_percent = None

    if "color" in lower_detail or "colour" in lower_detail:
        for pattern in [r"color[^\n]{0,20}(\d{1,3})%", r"colour[^\n]{0,20}(\d{1,3})%", r"(\d{1,3})%[^\n]{0,20}color", r"(\d{1,3})%[^\n]{0,20}colour"]:
            match = re.search(pattern, detail_output, re.IGNORECASE)
            if match:
                color_percent = int(match.group(1))
                break

    if any(k in lower_detail for k in ["black", "toner", "ink"]):
        for pattern in [r"black[^\n]{0,20}(\d{1,3})%", r"(\d{1,3})%[^\n]{0,20}black", r"toner[^\n]{0,20}(\d{1,3})%", r"ink[^\n]{0,20}(\d{1,3})%", r"(\d{1,3})%[^\n]{0,20}toner", r"(\d{1,3})%[^\n]{0,20}ink"]:
            match = re.search(pattern, detail_output, re.IGNORECASE)
            if match:
                bw_percent = int(match.group(1))
                break

    if color_percent is None and bw_percent is None:
        ink_level = "ไม่ทราบ"
    else:
        color_text = f"สี {color_percent}%" if color_percent is not None else "สี -"
        bw_text = f"ดำ {bw_percent}%" if bw_percent is not None else "ดำ -"
        ink_level = f"{color_text} | {bw_text}"

    job_progress = parse_job_progress(detail_output, queue_output)
    return status, ink_level, job_progress, job_state_label


def get_printers():
    try:
        output = subprocess.check_output(["lpstat", "-p"]).decode("utf-8")
        printers = []
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            match = re.search(r"(?:printer|เครื่องพิมพ์)\s+(\S+)", line, re.IGNORECASE)
            if not match:
                continue

            printer_name = match.group(1).strip()
            try:
                detail_output = subprocess.check_output(["lpstat", "-l", "-p", printer_name]).decode("utf-8", "ignore")
            except Exception:
                detail_output = ""
            try:
                queue_output = subprocess.check_output(["lpq", "-P", printer_name], stderr=subprocess.STDOUT).decode("utf-8", "ignore")
            except Exception:
                queue_output = ""

            jobs = parse_printer_jobs(printer_name, queue_output)
            status, ink_level, job_progress, job_state_label = parse_printer_status(line, detail_output, queue_output, jobs)
            first_job = jobs[0] if jobs else {}

            printers.append({
                "name": printer_name,
                "status": status,
                "ink_level": ink_level,
                "job_progress": job_progress,
                "job_state_label": job_state_label,
                "job_id": first_job.get("job_id"),
                "job_filename": first_job.get("filename"),
                "jobs": jobs,
            })
        return printers
    except Exception:
        return []


@app.route('/api/printers')
def api_printers():
    return jsonify(get_printers())


@app.route('/api/history')
def api_history():
    items = load_history()
    valid_items = [
        item for item in items
        if os.path.exists(os.path.join(HISTORY_FOLDER, item.get("stored_filename", "")))
    ]
    if len(valid_items) != len(items):
        save_history(valid_items)
    return jsonify(valid_items)


@app.route('/api/reprint/<item_id>', methods=['POST'])
def reprint_job(item_id):
    if not re.match(r'^[a-f0-9]+$', item_id):
        return jsonify({"success": False, "message": "Invalid History ID"}), 400

    history = load_history()
    target = next((item for item in history if item.get("id") == item_id), None)
    if not target:
        return jsonify({"success": False, "message": "ไม่พบประวัติงานพิมพ์นี้"}), 404

    stored_path = os.path.join(HISTORY_FOLDER, target.get("stored_filename", ""))
    if not os.path.exists(stored_path):
        return jsonify({"success": False, "message": "ไฟล์ต้นฉบับถูกลบออกจากระบบแล้ว"}), 404

    data = request.get_json(silent=True) or {}
    settings = target.get("settings", {})
    printer_name = data.get("printer") or settings.get("printer")
    if not printer_name:
        return jsonify({"success": False, "message": "กรุณาเลือกเครื่องพิมพ์"}), 400

    try:
        command = build_print_command(
            printer_name=printer_name,
            filepath=stored_path,
            print_mode=settings.get("print_mode", "bw"),
            copies=int(settings.get("copies", 1)),
            paper_size=settings.get("paper_size", "A4"),
            print_quality=settings.get("print_quality", "normal"),
            orientation=settings.get("orientation", "portrait"),
            page_ranges=settings.get("page_ranges", ""),
            duplex=settings.get("duplex", "one-sided"),
            scaling=settings.get("scaling", "fit"),
        )
        subprocess.run(command, check=True)
        return jsonify({
            "success": True,
            "message": f'สั่งพิมพ์ซ้ำ "{target["filename"]}" ไปที่ {printer_name} เรียบร้อยแล้ว'
        })
    except subprocess.CalledProcessError:
        return jsonify({"success": False, "message": "ไม่สามารถส่งงานไปยังระบบ CUPS ได้"}), 500


@app.route('/api/cancel/<job_id>', methods=['POST'])
def cancel_job(job_id):
    if not re.match(r'^[a-zA-Z0-9_-]+$', job_id):
        return jsonify({"success": False, "message": "Invalid Job ID"}), 400
    try:
        subprocess.run(["cancel", job_id], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify({"success": True, "message": f"ยกเลิกงานพิมพ์ {job_id} เรียบร้อยแล้ว"})
    except subprocess.CalledProcessError:
        return jsonify({"success": False, "message": "ไม่สามารถยกเลิกงานพิมพ์ได้ (อาจพิมพ์เสร็จไปแล้ว)"}), 500


@app.route('/', methods=['GET', 'POST'])
def index():
    printers = get_printers()
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('ไม่พบไฟล์ในคำขอ', 'danger')
            return redirect(request.url)

        file = request.files['file']
        selected_printer = request.form.get('printer')
        print_mode = request.form.get('print_mode', 'bw')
        copies_value = request.form.get('copies', '1')
        paper_size = request.form.get('paper_size', 'A4')
        print_quality = request.form.get('print_quality', 'normal')
        orientation = request.form.get('orientation', 'portrait')

        # ค่าใหม่ที่เพิ่มเข้ามา
        page_range_mode = request.form.get('page_range_mode', 'all')
        page_ranges_input = request.form.get('page_ranges', '').strip()
        page_ranges = sanitize_page_ranges(page_ranges_input) if page_range_mode == 'custom' else ''
        duplex = request.form.get('duplex', 'one-sided')
        scaling = request.form.get('scaling', 'fit')

        if file.filename == '':
            flash('กรุณาเลือกไฟล์ก่อนกดสั่งพิมพ์', 'warning')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('นามสกุลไฟล์ไม่อนุญาตให้อัปโหลด', 'danger')
            return redirect(request.url)

        if page_range_mode == 'custom' and not page_ranges:
            flash('รูปแบบช่วงหน้าไม่ถูกต้อง (ตัวอย่างที่ถูกต้อง: 1-3, 5)', 'warning')
            return redirect(request.url)

        try:
            copies = max(1, min(100, int(copies_value)))
        except ValueError:
            copies = 1

        if file and selected_printer:
            raw_filename = file.filename
            original_name = secure_filename(raw_filename) or f"document.{raw_filename.rsplit('.', 1)[-1].lower()}"
            unique_prefix = uuid.uuid4().hex[:6]
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_prefix}_{original_name}")
            file.save(filepath)

            ext = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else ''
            if ext == 'pdf':
                if not is_valid_pdf(filepath):
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    flash('ไฟล์ PDF ไม่ถูกต้องหรือเสียหาย กรุณาตรวจสอบไฟล์อีกครั้ง', 'danger')
                    return redirect(request.url)
                filepath = normalize_pdf(filepath)
            elif ext in ['doc', 'docx']:
                filepath = convert_to_pdf_if_needed(filepath)

            try:
                command = build_print_command(
                    printer_name=selected_printer,
                    filepath=filepath,
                    print_mode=print_mode,
                    copies=copies,
                    paper_size=paper_size,
                    print_quality=print_quality,
                    orientation=orientation,
                    page_ranges=page_ranges,
                    duplex=duplex,
                    scaling=scaling,
                )
                subprocess.run(command, check=True)

                # บันทึกลงประวัติการพิมพ์ล่าสุด (เก็บไฟล์ที่แปลงเรียบร้อยแล้ว)
                add_to_history(
                    processed_filepath=filepath,
                    display_name=raw_filename,
                    settings={
                        "printer": selected_printer,
                        "print_mode": print_mode,
                        "copies": copies,
                        "paper_size": paper_size,
                        "print_quality": print_quality,
                        "orientation": orientation,
                        "page_ranges": page_ranges,
                        "duplex": duplex,
                        "scaling": scaling,
                    }
                )

                flash(f'ส่งไฟล์ "{raw_filename}" ({copies} ชุด) ไปยังเครื่องพิมพ์ {selected_printer} เรียบร้อยแล้ว!', 'success')
            except subprocess.CalledProcessError:
                flash('เกิดข้อผิดพลาด: ไม่สามารถส่งงานไปยังระบบ CUPS ได้', 'danger')
            finally:
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass

            return redirect(request.url)

    return render_template('index.html', printers=printers)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
