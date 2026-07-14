# **Web-PrinterPi 🖨️✨**
### Web-PrinterPi คือโซลูชัน Web Service ขนาดกะทัดรัดที่ถูกพัฒนาขึ้นเพื่อเปลี่ยน Raspberry Pi ให้กลายเป็น Print Server อัจฉริยะ ช่วยให้การสั่งพิมพ์งานกลายเป็นเรื่องง่าย สะดวก และไร้ขีดจำกัด รองรับการจัดการเครื่องพิมพ์ที่หลากหลายผ่านระบบมาตรฐาน CUPS (Common Unix Printing System) และรองรับการสั่งพิมพ์จากระยะไกลอย่างปลอดภัยผ่านเครือข่าย VPN

### ทำไมต้อง Web-PrinterPi?

ในยุคที่การทำงานแบบ Hybrid และการทำงานจากนอกสถานที่กลายเป็นเรื่องปกติ การสั่งพิมพ์เอกสารผ่านเครือข่ายเดิมๆ มักมีข้อจำกัดเรื่องความปลอดภัยและการเข้าถึงเครื่องพิมพ์ในเครือข่ายภายในบ้าน โปรเจกต์นี้จึงถูกสร้างขึ้นเพื่อตอบโจทย์ผู้ใช้งานที่ต้องการ:
- ความคล่องตัว (Mobility): สั่งพิมพ์เอกสารจากที่ไหนก็ได้บนโลกด้วยการเชื่อมต่อผ่าน Tailscale ทำให้เครื่องพิมพ์ส่วนตัวของคุณออนไลน์อยู่เสมอโดยไม่ต้องเปิด Port Forwarding ให้เสี่ยงต่อความปลอดภัย
- ความง่าย (Simplicity): ด้วยหน้าจอ Dashboard ที่ออกแบบด้วย Bootstrap 5 ผู้ใช้งานสามารถลากและวางไฟล์ (Drag & Drop) เพื่อพิมพ์เอกสารได้ทันทีผ่าน Browser ไม่ต้องติดตั้งไดรเวอร์หรือซอฟต์แวร์เพิ่มเติมในอุปกรณ์ปลายทาง
- ประสิทธิภาพ (Efficiency): จัดการทุกคำสั่งพิมพ์ผ่าน Flask Backend ที่สื่อสารกับ CUPS โดยตรง ช่วยให้คุณตรวจสอบสถานะเครื่องพิมพ์ ระดับหมึก และคิวงานพิมพ์ได้แบบ Real-time**

### **รายละเอียดทางเทคนิค (Technical Stack):**
- **Hardware & OS:** รันบน Raspberry Pi ควบคุมการทำงานผ่านระบบปฏิบัติการ Raspberry Pi OS
- **Networking & Security:** เชื่อมต่อและควบคุมความปลอดภัยผ่าน Tailscale VPN สำหรับการเข้าถึงและสั่งพิมพ์จากนอกบ้าน
- **Backend:** พัฒนาด้วย Flask (Python) ทำหน้าที่เป็น Middleware รับคำสั่งและสื่อสารกับระบบ CUPS ผ่าน lp command
- **Frontend:** ออกแบบด้วย Bootstrap 5 ให้รองรับการใช้งานผ่านหน้าจออุปกรณ์ที่หลากหลาย (Responsive Design) พร้อมฟังก์ชัน JavaScript สำหรับการจัดการไฟล์และการอัปเดตข้อมูลสถานะแบบ Asynchronous


## **📦 สิ่งที่ต้องมี:**
  * **CUPS (Common Unix Printing System):** สำหรับเชื่อมต่อและจัดการไดรเวอร์เครื่องพิมพ์  
  👉 [ดูรายละเอียดเพิ่มเติมและวิธีติดตั้ง (OpenPrinting CUPS)](https://github.com/OpenPrinting/cups)
* **Tailscale:** สำหรับทำ Secure VPN ส่วนตัว ช่วยให้คุณสั่งพิมพ์เอกสารจากนอกเครือข่าย WiFi บ้านได้ปลอดภัยโดยไม่ต้องเปิด Port Forwarding  
  👉 [ดูรายละเอียดเพิ่มเติมและวิธีใช้งาน (Tailscale)](https://github.com/tailscale/tailscale)

## 🛠️ การติดตั้ง:
- อัปเดตระบบและติดตั้งแพ็กเกจที่จำเป็น (Flask, Gunicorn, และ CUPS)

  Bash:

      sudo apt update
      sudo apt install python3-flask python3-gunicorn cups cups-client python3-venv -y
- เพิ่มสิทธิ์ให้ User ที่ใช้งานอยู่ (สมมติว่าเป็นชื่อ pi) ให้สามารถจัดการเครื่องพิมพ์ผ่านระบบ CUPS ได้

   Bash:

      sudo usermod -a -G lp,lpadmin $USER
- นำไฟล์และโฟลเดอร์โปรเจกต์ web-printerPi มาไว้ที่ Home directory ด้วยวิธีที่สะดวก เช่น FileZilla, SCP, หรือสร้างไฟล์ผ่าน Nano
  >
- สร้างโฟลเดอร์ Uploads สำหรับเก็บไฟล์เอกสารชั่วคราว ภายในโฟลเดอร์ ~/web-printerPi

   Bash:

      mkdir -p ~/web-printerPi/uploads
- ให้ตรวจสอบว่าตอนนี้เราอยู่ในโฟลเดอร์โปรเจกต์หรือยัง
  
   Bash:

      ls -la
- สร้าง Virtual Environment ชื่อ venv ภายในโฟลเดอร์ ~/web-printerPi
  
   Bash:

      cd ~/web-printerPi
      python3 -m venv venv
- เปิดใช้งาน Virtual Environment (สังเกตว่าหน้าจอ Terminal จะมีชื่อ (venv)นำหน้า)

   Bash:

      source venv/bin/activate   
- ติดตั้ง Library ภายใน Virtual Environment อัปเดต pip และติดตั้งแพ็กเกจ Flask กับ Gunicorn
  
   Bash:

      pip install --upgrade pip
      pip install flask gunicorn
- ตรวจสอบให้แน่ใจว่าเรายังอยู่ใน ~/web-printerPi และเปิด Virtual Environment อยู่ จากนั้นทดสอบรันโปรแกรมด้วย Python
  
   Bash:

      python3 webPrinterPi.py
  >ถ้าหน้าจอแสดงผลว่าแอปเริ่มทำงานและรอรับการเชื่อมต่อ ให้ลองเปิด Browser เข้าไปทดสอบดู เมื่อเรียบร้อยแล้วให้กดปุ่ม Ctrl+C ที่คีย์บอร์ดเพื่อหยุดการทำงาน
- ทดสอบรันผ่าน Gunicorn

   Bash:

      ./venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 webPrinterPi:app
  >หากรันผ่านไม่มี Error ให้กด Ctrl+C เพื่อออกจากโหมดทดสอบ
- ตั้งค่าให้รันเป็น Systemd Service (เปิดอัตโนมัติหลังบูตเครื่อง) สร้างไฟล์เซอร์วิสใหม่ด้วยสิทธิ์ Admin
  
   Bash:

      sudo nano /etc/systemd/system/webprinterpi.service
  คัดลอกข้อความด้านล่างนี้ไปวางทั้งหมดในโปรแกรมแก้ไข Nano (อย่าลืมเปลี่ยน /home/pi/... หรือชื่อ User ให้ตรงกับเครื่องที่ใช้งานจริง):

      [Unit]
      Description=Gunicorn instance to serve Web-PrinterPi
      After=network.target cups.service

      [Service]
      User=pi
      Group=lp
      WorkingDirectory=/home/pi/web-printerPi
      ExecStart=/home/pi/web-printerPi/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:5000 webPrinterPi:app
      Restart=always

      [Install]
      WantedBy=multi-user.target
  >บันทึกค่า Config กด Ctrl+O แล้วกด Enter เพื่อบันทึก จากนั้นกด Ctrl+X เพื่อออก
- เปิดใช้งานและสตาร์ทเซอร์วิส
  
   Bash:

      sudo systemctl daemon-reload
      sudo systemctl start webprinterpi
      sudo systemctl enable webprinterpi
- ตรวจสอบสถานะการทำงานว่าเป็นสีเขียว active (running) เรียบร้อยดีไหม

   Bash:

      sudo systemctl status webprinterpi

## **📦 การใช้งานโปรแกรม:**
