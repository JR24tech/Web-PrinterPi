# Web-PrinterPi 🖨️✨
โปรเจกต์ทำเว็บเซอร์วิสสั่งพิมพ์งานผ่าน Raspberry Pi ควบคุมง่ายๆ ด้วย Flask และจัดการเครื่องพิมพ์ผ่าน OpenCUPS Printing
## 📦 สิ่งที่ต้องมี:
  - OpenCUPS Printing - สำหรับเชื่อมต่อและจัดการเครื่องพิมพ์ https://github.com/OpenPrinting/cups
  - Tailscale - สำหรับใช้งาน VPN สั่งพิมพ์นอกเครือข่ายภายในบ้าน https://github.com/tailscale/tailscale

## 🛠️ การติดตั้ง:
- อัปเดตระบบและติดตั้งแพ็กเกจที่จำเป็น (Flask, Gunicorn, และ CUPS):

       sudo apt update
       sudo apt install python3-flask python3-gunicorn cups cups-client python3-venv -y
- สร้างโฟลเดอร์หลักสำหรับเก็บโปรแกรมไว้ที่ Home Directory

      mkdir -p ~/web-printerPi
- นำไฟล์และโฟลเดอร์โปรเจกต์ web-printerPi ทั้งหมดไปไว้ที่ Home Directory (~/web-printerPi)
- สร้างโฟลเดอร์ Uploads สำหรับเก็บไฟล์เอกสารชั่วคราว

      mkdir -p ~/web-printerPi/uploads
- สร้าง Virtual Environment:

       cd ~/web-printerPi
       python3 -m venv venv
- เปิดใช้งาน Virtual Environment:

       source venv/bin/activate   
- ติดตั้ง Library ที่จำเป็น:
 
       cd ~/web-printerPi
       pip install flask gunicorn
- ทดสอบ Run โปรแกรม:

       cd ~/web-printerPi
       python3 webPrinterPi.py
  * หากเปิดโปรแกรมสำเร็จให้ทำการกด Ctrl+C เพื่อออกจากโปรแกรม

## 🛠️ การตั้งค่าสำหรับการรันโปรแกรมอัตโนมัติหลังจากบูตระบบ Raspberry Pi:
- ทดสอบเปิดโปรแกรมด้วย Gunicorn:

      cd ~/web-printerPi
      ./venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 webPrinterPi:app
  * หากเปิดโปรแกรมสำเร็จให้ทำการกด Ctrl+C เพื่อออกจากโปรแกรม
- สร้างเซอร์วิส systemctl สำหรับการเปิดโปรแกรมอัตโนมัติเมืื่อ Raspberry Pi บูตระบบเสร็จ:

      sudo nano /etc/systemd/system/webprinterpi.service
- เพิ่มค่า Config นี้ลงไป (แก้ User, WorkingDirectory และ ExecStart ให้ตรงกับ path ในเครื่อง):

      [Unit]
      Description=Gunicorn instance to serve Web-PrinterPi
      After=network.target

      [Service]
      User=pi
      Group=www-data
      WorkingDirectory=/home/pi/Web-PrinterPi
      ExecStart=/home/pi/web-printerPi/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:5000 webPrinterPi:app

      [Install]
      WantedBy=multi-user.target
- ทำการรีเฟรชค่าความจำของเซอร์วิส systemctl:

      sudo systemctl daemon-reload

- ทำการรีสตาร์ทเซอร์วิส Web-PrinterPi:

      sudo systemctl restart webprinterpi
- สร้างการทำงานอัตโนมัติทันทีเมื่อ Rasppberry Pi บูตระบบเสร็จ:

      sudo systemctl enable webprinterpi
  
