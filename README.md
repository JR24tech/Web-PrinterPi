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
  * หากโปรแกรมรันสำเร็จให้ทำการกด Ctrl+C เพื่อออกจากโปรแกรม

## 🛠️ การตั้งค่าสำหรับการรันโปรแกรมอัตโนมัติหลังจากบูตระบบ Raspberry Pi:

