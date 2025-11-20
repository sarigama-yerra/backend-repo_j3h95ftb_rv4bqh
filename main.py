import os
from typing import List, Optional, Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import db, create_document, get_documents
from schemas import Service, Project, Interaction, Message
from bson.objectid import ObjectId

app = FastAPI(title="SomDev Solutions API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Utility ----------

def oid_str(doc):
    if not doc:
        return doc
    if isinstance(doc, list):
        return [oid_str(d) for d in doc]
    d = {**doc}
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


def ensure_seed_data():
    """Seed default services and projects if collections are empty"""
    if db is None:
        return
    # Services
    if db["service"].count_documents({}) == 0:
        default_services = [
            {
                "title": "Custom Web Apps",
                "description": "High-performance, scalable web applications tailored to your business.",
                "icon": "Globe",
                "price_from": 4999.0,
                "category": "Development",
                "cta_label": "Start Your Project"
            },
            {
                "title": "AI Integrations",
                "description": "Integrate AI chat, search and automation into your products.",
                "icon": "Bot",
                "price_from": 2999.0,
                "category": "AI",
                "cta_label": "Discuss AI"
            },
            {
                "title": "Cloud & DevOps",
                "description": "Secure, automated, and cost-optimized cloud infrastructure.",
                "icon": "Cloud",
                "price_from": 1999.0,
                "category": "Cloud",
                "cta_label": "Optimize Stack"
            },
            {
                "title": "UI/UX Design",
                "description": "Premium, accessible, conversion-focused design systems.",
                "icon": "Palette",
                "price_from": 1499.0,
                "category": "Design",
                "cta_label": "Design My UI"
            },
        ]
        for s in default_services:
            db["service"].insert_one({**s})

    # Projects
    if db["project"].count_documents({}) == 0:
        default_projects = [
            {
                "title": "FinTech Analytics Suite",
                "description": "A real-time dashboard for risk analytics with ML-driven insights.",
                "image": "https://images.unsplash.com/photo-1551281044-8b59f0209686?w=1200&q=80&auto=format&fit=crop",
                "tags": ["React", "FastAPI", "Kafka", "Postgres"],
            },
            {
                "title": "E-commerce Headless Storefront",
                "description": "Lightning-fast storefront with personalized search and A/B testing.",
                "image": "https://images.unsplash.com/photo-1519337265831-281ec6cc8514?w=1200&q=80&auto=format&fit=crop",
                "tags": ["Next.js", "Stripe", "Algolia"],
            },
            {
                "title": "Healthcare Telemedicine Platform",
                "description": "HIPAA-ready video consultations with smart triage chatbot.",
                "image": "https://images.unsplash.com/photo-1494390248081-4e521a5940db?w=1200&q=80&auto=format&fit=crop",
                "tags": ["WebRTC", "AI", "MongoDB"],
            },
        ]
        for p in default_projects:
            db["project"].insert_one({**p})


@app.on_event("startup")
async def on_startup():
    try:
        ensure_seed_data()
    except Exception:
        pass


# ---------- Public Endpoints ----------

@app.get("/")
def root():
    return {"brand": "SomDev Solutions", "status": "ok"}


@app.get("/api/services")
def list_services() -> List[dict]:
    ensure_seed_data()
    docs = list(db["service"].find().sort("title"))
    return oid_str(docs)


@app.get("/api/projects")
def list_projects() -> List[dict]:
    ensure_seed_data()
    docs = list(db["project"].find().sort("title"))
    return oid_str(docs)


class TrackPayload(Interaction):
    pass


@app.post("/api/track")
def track_interaction(payload: TrackPayload):
    ensure_seed_data()
    interaction_id = create_document("interaction", payload)
    return {"ok": True, "id": interaction_id}


@app.get("/api/analytics")
def analytics(
    type: Optional[Literal["view", "order"]] = Query(None),
    service_id: Optional[str] = Query(None),
):
    ensure_seed_data()
    pipeline = []
    match = {}
    if type:
        match["type"] = type
    if service_id:
        try:
            match["service_id"] = service_id
        except Exception:
            pass
    if match:
        pipeline.append({"$match": match})
    pipeline.extend([
        {"$group": {"_id": {"service_id": "$service_id", "type": "$type"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ])
    data = list(db["interaction"].aggregate(pipeline))
    # Join with services
    services_map = {str(s["_id"]): s["title"] for s in db["service"].find({}, {"title": 1})}
    result = []
    for row in data:
        sid = row["_id"].get("service_id") or "unknown"
        result.append({
            "service_id": sid,
            "service_title": services_map.get(sid, "(General)" if sid == "unknown" else "Unknown"),
            "type": row["_id"].get("type"),
            "count": row["count"],
        })
    return {"ok": True, "data": result}


# ---------- Simple Chatbot ----------

class ChatPayload(BaseModel):
    user_id: str
    message: str


@app.post("/api/chat")
def chat_bot(payload: ChatPayload):
    ensure_seed_data()
    user_msg = payload.message.strip().lower()
    # Persist messages (optional for simple history)
    create_document("message", Message(user_id=payload.user_id, role="user", content=payload.message))

    answer = ""
    if any(k in user_msg for k in ["service", "offer", "do you do", "capability"]):
        services = list(db["service"].find())
        bullet = "\n".join([f"• {s['title']}: {s['description']}" for s in services])
        answer = (
            "We deliver end-to-end technology solutions. Here are our core services:\n" + bullet +
            "\nWould you like recommendations based on your goals and timeline?"
        )
    elif any(k in user_msg for k in ["project", "case study", "portfolio", "examples"]):
        projects = list(db["project"].find())
        bullet = "\n".join([f"• {p['title']} — {', '.join(p.get('tags', []))}" for p in projects])
        answer = (
            "Here are a few recent projects we loved building:\n" + bullet +
            "\nCurious about the approach or stack behind any of these?"
        )
    elif any(k in user_msg for k in ["price", "cost", "budget", "rates"]):
        answer = (
            "Pricing depends on scope and timelines. Typical starting points: Web Apps from $4,999, "
            "AI Integrations from $2,999, Cloud & DevOps from $1,999, and Design from $1,499. "
            "Share your goals and we'll outline a fixed-scope proposal."
        )
    else:
        answer = (
            "I'm SomDev's assistant. I can help with services, projects, timelines, and next steps. "
            "Ask about our services, pricing, or share your goals for a tailored plan."
        )

    create_document("message", Message(user_id=payload.user_id, role="assistant", content=answer))
    return {"ok": True, "answer": answer}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            collections = db.list_collection_names()
            response["collections"] = collections
            response["database"] = "✅ Connected & Working"
            response["connection_status"] = "Connected"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:100]}"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
