# Web-PrinterPi 🖨️✨
โปรเจกต์ทำเว็บเซอร์วิสสั่งพิมพ์งานผ่าน Raspberry Pi ควบคุมง่ายๆ ด้วย Flask และจัดการเครื่องพิมพ์ผ่าน OpenCUPS Printing
## 📦 สิ่งที่ต้องมี:
  - OpenCUPS Printing - สำหรับเชื่อมต่อและจัดการเครื่องพิมพ์ https://github.com/OpenPrinting/cups
  - Tailscale - สำหรับใช้งาน VPN สั่งพิมพ์นอกเครือข่ายภายในบ้าน https://github.com/tailscale/tailscale

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
