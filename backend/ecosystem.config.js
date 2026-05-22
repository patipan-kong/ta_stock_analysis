module.exports = {
  apps: [{
    name: "portfolio-backend",
    script: "venv/bin/uvicorn",
    // 💡 ยิงตรงหา uvicorn เพียวๆ คลีนๆ ไม่ผ่าน gunicorn
    args: "main:app --host 127.0.0.1 --port 8000",
    cwd: "/var/www/vhost/dev-ta.dvrdns.org/backend",
    // 💡 เปิดร่างแยกเงาพันร่างด้วย PM2 คุมให้เอง
    instances: 4,          
    exec_mode: "cluster",  
    env: {
      YF_NO_PRICING_CACHE: "1"
    }
  }]
}