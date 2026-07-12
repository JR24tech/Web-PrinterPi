# Web-PrinterPi 🖨️✨
โปรเจกต์ทำเว็บเซอร์วิสสั่งพิมพ์งานผ่าน Raspberry Pi ควบคุมง่ายๆ ด้วย Flask และจัดการเครื่องพิมพ์ผ่าน OpenCUPS Printing
## 📦 สิ่งที่ต้องมี:
  - OpenCUPS Printing >> สำหรับเชื่อมต่อและจัดการเครื่องพิมพ์ https://github.com/OpenPrinting/cups
  - Tailscale >> สำหรับใช้งาน VPN สั่งพิมพ์นอกเครือข่ายภายในบ้าน https://github.com/tailscale/tailscale

## 🛠️ การติดตั้ง:
1. อัปเดตระบบและติดตั้งแพ็กเกจที่จำเป็น (Flask, Gunicorn, และ CUPS):

       sudo apt update
       sudo apt install python3-flask python3-gunicorn cups cups-client python3-venv -y

2. นำโฟลเดอร์โปรเจกต์ web-printerPi ไปไว้ที่ Home Directory (~/web-printerPi)

3. สร้าง Virtual Environment:

       cd ~/web-printerPi
       python3 -m venv venv

4. เปิดใช้งาน Virtual Environment:

       source venv/bin/activate
   
5. ติดตั้ง Library ที่จำเป็น:
 
       cd ~/web-printerPi
       pip install flask gunicorn

6. ทดสอบ Run โปรแกรม:

       cd ~/web-printerPi
       python3 webPrinterPi.py
  
