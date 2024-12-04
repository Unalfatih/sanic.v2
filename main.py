from sanic import Sanic, response
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from models.model import Base, User, Event, Announcement
import bcrypt
from sanic_ext import Extend
from redis.asyncio import from_url
import json
from bcrypt import hashpw, gensalt, checkpw

app = Sanic("UserApp")

Extend(app)

# Redis bağlantısı
redis = from_url("redis://localhost:6379")

# Veritabanı bağlantı ayarları
DATABASE_URL = "mysql+aiomysql://root:159753@localhost:3306/school_club"
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

#CORS hatası çözümü
@app.middleware("response")
async def cors_headers(request, response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"

# Veritabanını başlat
@app.before_server_start
async def setup_db(app, loop):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/users/getall")
async def get_all_users(request):
    cache_key = "users:getall"
    cached_users = await redis.get(cache_key)

    if cached_users:
        # Cache'deki veriyi döndür
        return response.json({"users": json.loads(cached_users)})

    # Veritabanından kullanıcıları al
    async with SessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        users_list = [user.as_dict() for user in users]

        # Veriyi Redis'e kaydet (60 saniye süreyle geçerli)
        await redis.set(cache_key, json.dumps(users_list), ex=60)

        return response.json({"users": users_list})


@app.put("/users/deactivate/<user_id:int>")
async def deactivate_user(request, user_id):
    """
    Belirtilen kullanıcı ID'sine göre kullanıcıyı devre dışı bırakır (is_active = False).
    Kullanıcıyı dbden silmeyiz aktif durumunu pasif yaparız.
    """
    async with SessionLocal() as session:
        # Kullanıcıyı ID'ye göre getir
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            return response.json({"message": "User not found."}, status=404)

        # Kullanıcıyı devre dışı bırak
        user.is_active = False

        async with session.begin():
            session.add(user)

        return response.json({"message": f"User with ID {user_id} has been deactivated."}, status=200)

@app.put("/users/update/<user_id:int>")
async def update_user(request, user_id):
    """
    Kullanıcı bilgilerini ve opsiyonel olarak şifresini günceller.
    """
    async with SessionLocal() as session:
        # Kullanıcıyı getir
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            return response.json({"message": "User not found."}, status=404)

        data = request.json

        # Kullanıcı bilgilerini güncelle
        user.first_name = data.get("first_name", user.first_name)
        user.last_name = data.get("last_name", user.last_name)
        user.email = data.get("email", user.email)
        user.is_active = data.get("is_active", user.is_active)

        # Şifre güncellemesi
        new_password = data.get("new_password")
        current_password = data.get("current_password")
        if new_password:
            if not current_password:
                return response.json({"message": "Current password is required to update the password."}, status=400)
            
            # Mevcut şifre doğrulama
            if not checkpw(current_password.encode("utf-8"), user.password.encode("utf-8")):
                return response.json({"message": "Current password is incorrect."}, status=400)
            
            # Yeni şifreyi hashle ve kaydet
            user.password = hashpw(new_password.encode("utf-8"), gensalt()).decode("utf-8")

        async with session.begin():
            session.add(user)

        # Cache'i temizle
        await redis.delete("users:getall")
        return response.json({"message": "User updated successfully!"})
    
    

@app.post("/users/register")
async def register_user(request):
    """Yeni bir kullanıcı kaydeder."""
    data = request.json
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")  # Varsayılan olarak "user"
    is_active = data.get("is_active", True)  # Varsayılan olarak aktif

    if not first_name or not last_name or not email or not password:
        return response.json({"message": "All fields are required."}, status=400)

    # Şifreyi hashleme
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    new_user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=hashed_password,
        role=role,
        is_active=is_active,
    )

    async with SessionLocal() as session:
        # Aynı email kontrolü
        existing_user = await session.execute(select(User).where(User.email == email))
        if existing_user.scalars().first():
            return response.json({"message": "Email already exists."}, status=409)

        # Yeni kullanıcıyı kaydet
        session.add(new_user)
        await session.commit()  # İşlemi manuel olarak tamamla

        await redis.delete("users:getall")  # Cache'i temizle

    return response.json({"message": "User registered successfully!"}, status=201)


@app.post("/users/login")
async def login_user(request):
    """Kullanıcı giriş yapar."""
    data = request.json
    email = data.get("email")
    password = data.get("password")

    # Gerekli alanların kontrolü
    if not email or not password:
        return response.json({"message": "Email and password are required."}, status=400)

    async with SessionLocal() as session:
        # Kullanıcıyı email'e göre bul
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalars().first()

        # Kullanıcı doğrulama
        if user and bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
            return response.json({"message": "Login successful!", "user": user.as_dict()})
        else:
            return response.json({"message": "Invalid email or password."}, status=401)


@app.get("/events/getall")
async def get_all_events(request):
    cache_key = "events:getall"
    cached_events = await redis.get(cache_key)

    if cached_events:
        return response.json({"events": json.loads(cached_events)})

    async with SessionLocal() as session:
        result = await session.execute(select(Event))
        events = result.scalars().all()
        events_list = [event.as_dict() for event in events]

        await redis.set(cache_key, json.dumps(events_list), ex=60)
        return response.json({"events": events_list})
    

@app.post("/events/create")
async def create_event(request):
    data = request.json
    title = data.get("title")
    description = data.get("description")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    created_by = data.get("created_by")

    if not title or not start_date or not end_date or not created_by:
        return response.json({"message": "Title, start_date, end_date, and created_by are required."},status=400)

    new_event = Event(
        title = title,
        description = description,
        start_date = start_date,
        end_date = end_date,
        created_by = created_by,
    )

    async with SessionLocal() as session:
        async with session.begin():
            session.add(new_event)

        await redis.delete("events:getall")  # Cache'i temizle
        return response.json({"message": "Event created successfully!"}, status=201)


@app.delete("/events/delete/<event_id:int>")
async def delete_event(request, event_id):
    """
    Belirtilen ID'ye sahip etkinliği siler.
    """
    async with SessionLocal() as session:
        # Etkinliği ID'ye göre bul
        result = await session.execute(select(Event).where(Event.id == event_id))
        event = result.scalars().first()

        if not event:
            return response.json({"message": "Event not found."}, status=404)

        async with session.begin():
            await session.delete(event)

        # Cache'i temizle
        await redis.delete("events:getall")
        return response.json({"message": "Event deleted successfully!"})



@app.get("/announcements/getall")
async def get_all_announcements(request):
    cache_key = "announcements:getall"
    cached_announcements = await redis.get(cache_key)

    if cached_announcements:
        return response.json({"announcements": json.loads(cached_announcements)})

    async with SessionLocal() as session:
        result = await session.execute(select(Announcement))
        announcements = result.scalars().all()
        announcements_list = [announcement.as_dict() for announcement in announcements]

        await redis.set(cache_key, json.dumps(announcements_list), ex=60)
        return response.json({"announcements": announcements_list})

@app.post("/announcements/create")
async def create_announcement(request):
    data = request.json
    title = data.get("title")
    content = data.get("content")
    created_by = data.get("created_by") 

    if not title or not content or not created_by:
        return response.json({"message": "Title, content, and created_by are required."}, status=400)

    new_announcement = Announcement(
        title=title,
        content=content,
        created_by=created_by,
    )

    async with SessionLocal() as session:
        async with session.begin():
            session.add(new_announcement)

        await redis.delete("announcements:getall")  # Cache'i temizle
        return response.json({"message": "Announcement created successfully!"}, status=201)


@app.delete("/announcements/delete/<announcement_id:int>")
async def delete_announcement(request, announcement_id):
    async with SessionLocal() as session:
        result = await session.execute(select(Announcement).where(Announcement.id == announcement_id))
        announcement = result.scalars().first()

        if not announcement:
            return response.json({"message": "Announcement not found."}, status=404)

        async with session.begin():
            await session.delete(announcement)

        await redis.delete("announcements:getall")  # Cache'i temizle
        return response.json({"message": "Announcement deleted successfully!"})


#Id ile user getirm fonk.
@app.get("/users/<user_id:int>")
async def get_user_by_id(request, user_id):
    """Kullanıcıyı id ile getirir."""
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if user:
            return response.json({"user": user.as_dict()}, status=200)
        else:
            return response.json({"message": f"User with id {user_id} not found."}, status=404)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
