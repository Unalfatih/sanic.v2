from sanic import Blueprint, response
from sqlalchemy.future import select
from utils.db import SessionLocal
from models.model import Announcement
from redis.asyncio import from_url
import json

bp = Blueprint("announcements", url_prefix="/announcements")

redis = from_url("redis://localhost:6379")

@bp.get("/getall")
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

@bp.post("/create")
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


@bp.delete("/delete/<announcement_id:int>")
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
