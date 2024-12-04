from sanic import Sanic
from sanic_ext import Extend
from redis.asyncio import from_url
from utils.db import setup_db
from routes import users, events, announcements

app = Sanic("UserApp")

# Sanic Extend
Extend(app)

# Redis bağlantısı
redis = from_url("redis://localhost:6379")

# Middleware - CORS
@app.middleware("response")
async def cors_headers(request, response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"

# Veritabanını başlat
@app.before_server_start
async def before_start(app, loop):
    await setup_db()

# Blueprint'leri bağlama
app.blueprint(users.bp)
app.blueprint(events.bp)
app.blueprint(announcements.bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
