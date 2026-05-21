module.exports = {
  apps: [{
    name: "portfolio-backend",
    script: "venv/bin/uvicorn",
    args: "-w 4 -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8000",
    cwd: "/var/www/vhost/dev-ta.dvrdns.org/backend",
    env: {
      YF_NO_PRICING_CACHE: "1"
    }
  }]
}