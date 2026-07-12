import os
import re
import subprocess
from flask import Flask, render_template, request, redirect, flash

app = Flask(__name__)
app.secret_key = "supersecretkey_for_sun"
UPLOAD_FOLDER = os.path.expanduser('~/web-printerPi/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # จำกัด 16MB


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

def parse_printer_status(line, detail_output):
    lower_line = line.lower()
    lower_detail = detail_output.lower()

    if "is idle" in lower_line or "accepting jobs" in lower_line:
        status = "พร้อมใช้งาน"
    elif "printing" in lower_line or "busy" in lower_line or "processing" in lower_line:
        status = "กำลังพิมพ์"
    else:
        status = "ไม่ทราบ"

    color_percent = None
    bw_percent = None

    for token in ["color", "colour", "cyan", "magenta", "yellow", "black", "toner", "ink"]:
        if token in lower_detail:
            pass

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

    return status, ink_level


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
                status, ink_level = parse_printer_status(line, detail_output)
                printers.append({"name": printer_name, "status": status, "ink_level": ink_level})
        return printers
    except Exception:
        return []

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

        if file and selected_printer:
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                command = build_print_command(selected_printer, filepath, print_mode, copies, paper_size, print_quality)
                subprocess.run(command, check=True)
                mode_label = 'สี' if print_mode == 'color' else 'ขาวดำ'
                flash(f'สำเร็จ! ส่งไฟล์ "{filename}" ไปยังเครื่องพิมพ์ [{selected_printer}] แบบ{mode_label} ขนาด {paper_size} คุณภาพ {print_quality} จำนวน {copies} ชุด แล้ว', 'success')
            except subprocess.CalledProcessError:
                flash('เกิดข้อผิดพลาด: ไม่สามารถส่งงานไปยัง CUPS ได้', 'danger')
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)

            return redirect(request.url)

    return render_template('index.html', printers=printers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)