from sanic import Blueprint, response
from sqlalchemy.future import select
from utils.db import SessionLocal
from models.model import Event
from redis.asyncio import from_url
import json

bp = Blueprint("events", url_prefix="/events")

redis = from_url("redis://localhost:6379")

@bp.get("/getall")
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


@bp.post("/events/create")
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


@bp.delete("/events/delete/<event_id:int>")
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


