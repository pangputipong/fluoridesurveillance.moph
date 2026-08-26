# ใช้ Python 3.9 เป็นฐาน
FROM python:3.9-slim

# ตั้งค่า Timezone ของ Container ให้เป็นเวลาประเทศไทย
ENV TZ=Asia/Bangkok
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# ตั้งค่า Directory ทำงานภายใน Container
WORKDIR /app

# คัดลอกไฟล์ requirements.txt และติดตั้งไลบรารี
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกไฟล์ทั้งหมดในโปรเจกต์เข้าไปใน Container
COPY . .

# เปิดพอร์ต 5000
EXPOSE 5000

# คำสั่งสำหรับรันแอปพลิเคชันด้วย Gunicorn (Production WSGI)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "app:app"]