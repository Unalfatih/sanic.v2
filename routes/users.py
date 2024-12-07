import bcrypt
from sanic import Blueprint, response
from sqlalchemy.future import select
from utils.db import SessionLocal
from models.model import User
from redis.asyncio import from_url
from bcrypt import hashpw, gensalt, checkpw
import json

bp = Blueprint("users", url_prefix="/users")

redis = from_url("redis://localhost:6379")

@bp.get("/getall")
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


@bp.put("/deactivate/<user_id:int>")
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

@bp.put("/update/<user_id:int>")
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
    
    

@bp.post("/register")
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


@bp.post("/login")
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

#Id ile user getirm fonk.
@bp.get("/<user_id:int>")
async def get_user_by_id(request, user_id):
    """Kullanıcıyı id ile getirir."""
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if user:
            return response.json({"user": user.as_dict()}, status=200)
        else:
            return response.json({"message": f"User with id {user_id} not found."}, status=404)
