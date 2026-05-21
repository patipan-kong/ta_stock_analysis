module.exports = {
  apps: [{
    name: "portfolio-backend",
    script: "venv/bin/uvicorn",
    // 💡 คลีนคำสั่ง args ให้เหลือแค่สั่งรันแอปกับผูกพอร์ตปกติ ไม่ต้องยุ่งกับกวนอิม
    args: "main:app --host 127.0.0.1 --port 8000",
    cwd: "/var/www/vhost/dev-ta.dvrdns.org/backend",
    // 💡 เปิดร่างแยกเงาพันร่างด้วย PM2 คุมให้เอง
    instances: 4,          // หรือใส่ "max" เพื่ออัดเต็มจำนวน core ของ VPS พี่ Ta
    exec_mode: "cluster",  // เปิดระบบคลัสเตอร์กระจายโหลดขนานกัน
    env: {
      YF_NO_PRICING_CACHE: "1"
    }
  }]
}