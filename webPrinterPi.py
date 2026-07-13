import os
import re
import subprocess
from pathlib import Path
from flask import Flask, jsonify, render_template, request, redirect, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('WEB_PRINTERPI_SECRET_KEY', 'supersecretkey_for_sun')
UPLOAD_FOLDER = Path.home() / 'web-printerPi' / 'uploads'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # จำกัด 16MB
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'txt', 'doc', 'docx'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def unique_filename(directory: Path, filename: str) -> Path:
    target = directory / filename
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    counter = 1
    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def save_upload_file(file):
    filename = secure_filename(file.filename)
    if not filename:
        raise ValueError('ชื่อไฟล์ไม่ถูกต้อง')
    if not allowed_file(filename):
        raise ValueError('ไฟล์ประเภทนี้ไม่รองรับ')
    filepath = unique_filename(Path(app.config['UPLOAD_FOLDER']), filename)
    file.save(str(filepath))
    return filepath


def build_print_command(printer_name, filepath, print_mode, copies, paper_size, print_quality):
    command = ["lp", "-d", printer_name]

    if print_mode == "color":
        command.extend(["-o", "ColorModel=RGB"])
    else:
        command.extend(["-o", "ColorModel=Gray"])

    if paper_size:
        command.extend(["-o", f"media={paper_size}"])

    if print_quality:
        command.extend(["-o", f"print-quality={print_quality}"])

    if copies and copies > 1:
        command.extend(["-n", str(copies)])

    command.append(filepath)
    return command

def parse_job_status(detail_output, queue_output=""):
    combined_output = "\n".join([part for part in [detail_output, queue_output] if part])
    if not combined_output:
        return None, None

    lower_output = combined_output.lower()
    if any(keyword in lower_output for keyword in ["completed", "finished", "done"]):
        return "completed", "เสร็จสิ้น"
    if any(keyword in lower_output for keyword in ["active", "job-printing", "printing", "processing", "busy"]):
        return "printing", "กำลังพิมพ์"
    if any(keyword in lower_output for keyword in ["pending", "queued", "waiting", "held"]):
        return "queued", "รอคิว"
    return None, None


def parse_job_progress(detail_output, queue_output=""):
    combined_output = "\n".join([part for part in [detail_output, queue_output] if part])
    if not combined_output:
        return None

    for line in combined_output.splitlines():
        lower_line = line.lower()
        if not any(keyword in lower_line for keyword in ["percent", "progress", "completed", "processed", "printed", "remaining", "job", "print"]):
            continue

        if any(keyword in lower_line for keyword in ["color", "colour", "black", "toner", "ink", "cyan", "magenta", "yellow"]):
            continue

        if "%" not in line:
            continue

        match = re.search(r"(\d{1,3})%", line)
        if not match:
            continue

        value = int(match.group(1))
        if 0 <= value <= 100:
            return value

    return None


def parse_printer_problem(line, detail_output, queue_output=""):
    combined = "\n".join([part for part in [line, detail_output, queue_output] if part]).lower()
    problem_patterns = [
        ('กระดาษหมด', ['out of paper', 'paper out', 'no paper', 'paper empty', 'paper depleted']),
        ('กระดาษติด', ['paper jam', 'paper jammed', 'jammed', 'stuck paper']),
        ('หมึกหมด', ['no toner', 'toner empty', 'ink empty', 'out of ink']),
        ('หมึกต่ำ', ['toner low', 'ink low', 'low toner', 'low ink']),
        ('ฝาเปิด', ['door open', 'cover open']),
        ('เครื่องพิมพ์ออฟไลน์', ['offline', 'not connected', 'not responding']),
        ('เครื่องพิมพ์ถูกหยุดชั่วคราว', ['paused', 'disabled', 'not accepting jobs', 'stopped']),
        ('ต้องการบริการ', ['service requested', 'service required', 'maintenance required']),
    ]
    for message, keywords in problem_patterns:
        if any(keyword in combined for keyword in keywords):
            level = 'danger' if message not in ['หมึกต่ำ'] else 'warning'
            return message, level
    return None, None


def parse_printer_status(line, detail_output, queue_output=""):
    lower_line = line.lower()
    lower_detail = detail_output.lower()
    lower_queue = queue_output.lower()

    job_state, job_state_label = parse_job_status(detail_output, queue_output)
    if job_state == "printing":
        status = "กำลังพิมพ์"
    elif job_state == "queued":
        status = "รอคิว"
    elif job_state == "completed":
        status = "เสร็จสิ้น"
    elif "is idle" in lower_line or "accepting jobs" in lower_line:
        status = "พร้อมใช้งาน"
    elif "printing" in lower_line or "busy" in lower_line or "processing" in lower_line or "active" in lower_queue:
        status = "กำลังพิมพ์"
    else:
        status = "ไม่ทราบ"

    color_percent = None
    bw_percent = None

    if "color" in lower_detail or "colour" in lower_detail:
        color_match = None
        for pattern in [r"color[^\n]{0,20}(\d{1,3})%", r"colour[^\n]{0,20}(\d{1,3})%", r"(\d{1,3})%[^\n]{0,20}color", r"(\d{1,3})%[^\n]{0,20}colour"]:
            match = re.search(pattern, detail_output, re.IGNORECASE)
            if match:
                color_match = int(match.group(1))
                break
        if color_match is not None:
            color_percent = color_match

    if "black" in lower_detail or "toner" in lower_detail or "ink" in lower_detail:
        bw_match = None
        for pattern in [r"black[^\n]{0,20}(\d{1,3})%", r"(\d{1,3})%[^\n]{0,20}black", r"toner[^\n]{0,20}(\d{1,3})%", r"ink[^\n]{0,20}(\d{1,3})%", r"(\d{1,3})%[^\n]{0,20}toner", r"(\d{1,3})%[^\n]{0,20}ink"]:
            match = re.search(pattern, detail_output, re.IGNORECASE)
            if match:
                bw_match = int(match.group(1))
                break
        if bw_match is not None:
            bw_percent = bw_match

    if color_percent is None and bw_percent is None:
        ink_level = "ไม่ทราบ"
    else:
        color_text = f"สี {color_percent}%" if color_percent is not None else "สี ไม่ทราบ"
        bw_text = f"ขาวดำ {bw_percent}%" if bw_percent is not None else "ขาวดำ ไม่ทราบ"
        ink_level = f"{color_text} | {bw_text}"

    job_progress = parse_job_progress(detail_output, queue_output)
    problem_message, status_level = parse_printer_problem(line, detail_output, queue_output)
    return status, ink_level, job_progress, job_state_label, problem_message, status_level


def get_printers():
    try:
        output = subprocess.check_output(["lpstat", "-p"]).decode("utf-8")
        printers = []
        for line in output.split("\n"):
            if "printer" in line:
                printer_name = line.split("printer ")[1].split(" ")[0].strip()
                try:
                    detail_output = subprocess.check_output(["lpstat", "-l", "-p", printer_name]).decode("utf-8", "ignore")
                except Exception:
                    detail_output = ""

                try:
                    queue_output = subprocess.check_output(["lpq", "-P", printer_name], stderr=subprocess.STDOUT).decode("utf-8", "ignore")
                except Exception:
                    queue_output = ""

                status, ink_level, job_progress, job_state_label, problem_message, status_level = parse_printer_status(line, detail_output, queue_output)
                printers.append({
                    "name": printer_name,
                    "status": status,
                    "ink_level": ink_level,
                    "job_progress": job_progress,
                    "job_state_label": job_state_label,
                    "problem_message": problem_message,
                    "status_level": status_level,
                })
        return printers
    except Exception:
        return []

@app.route('/api/printers')
def api_printers():
    return jsonify(get_printers())


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

        if file.filename == '':
            flash('กรุณาเลือกไฟล์ก่อนกดสั่งพิมพ์', 'warning')
            return redirect(request.url)

        try:
            copies = int(copies_value)
        except ValueError:
            copies = 1

        if copies < 1:
            copies = 1

        if not selected_printer:
            flash('กรุณาเลือกเครื่องพิมพ์', 'warning')
            return redirect(request.url)

        filename = file.filename
        filepath = None
        try:
            filepath = save_upload_file(file)
            command = build_print_command(selected_printer, str(filepath), print_mode, copies, paper_size, print_quality)
            subprocess.run(command, check=True)
            mode_label = 'สี' if print_mode == 'color' else 'ขาวดำ'
            flash(f'สำเร็จ! ส่งไฟล์ "{filename}" ไปยังเครื่องพิมพ์ [{selected_printer}] แบบ{mode_label} ขนาด {paper_size} คุณภาพ {print_quality} จำนวน {copies} ชุด แล้ว', 'success')
        except ValueError as err:
            flash(str(err), 'warning')
        except subprocess.CalledProcessError:
            flash('เกิดข้อผิดพลาด: ไม่สามารถส่งงานไปยัง CUPS ได้', 'danger')
        except OSError:
            flash('เกิดข้อผิดพลาด: ไม่สามารถบันทึกหรือส่งไฟล์ได้', 'danger')
        finally:
            if filepath is not None and os.path.exists(str(filepath)):
                try:
                    os.remove(str(filepath))
                except OSError:
                    pass

        return redirect(request.url)

    return render_template('index.html', printers=printers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)