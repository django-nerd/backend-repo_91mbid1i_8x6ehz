import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Ticket, TicketUpdate, Comment

app = FastAPI(title="IT Ticketing System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "IT Ticketing System API is running"}


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
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response


# Helper to convert ObjectId to string
class TicketOut(BaseModel):
    id: str
    title: str
    description: str
    requester_email: str
    category: str
    priority: str
    status: str
    assignee: Optional[str] = None
    created_at: str
    updated_at: str


@app.post("/api/tickets", response_model=dict)
def create_ticket(payload: Ticket):
    try:
        ticket_id = create_document("ticket", payload)
        return {"id": ticket_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tickets", response_model=List[dict])
def list_tickets(status: Optional[str] = None, priority: Optional[str] = None):
    try:
        filter_dict = {}
        if status:
            filter_dict["status"] = status
        if priority:
            filter_dict["priority"] = priority

        docs = get_documents("ticket", filter_dict=filter_dict)
        result = []
        for d in docs:
            d["id"] = str(d.pop("_id"))
            # Convert datetimes to isoformat strings for JSON
            if "created_at" in d and hasattr(d["created_at"], "isoformat"):
                d["created_at"] = d["created_at"].isoformat()
            if "updated_at" in d and hasattr(d["updated_at"], "isoformat"):
                d["updated_at"] = d["updated_at"].isoformat()
            result.append(d)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tickets/{ticket_id}", response_model=dict)
def get_ticket(ticket_id: str):
    from pymongo import ReturnDocument
    try:
        doc = db["ticket"].find_one({"_id": ObjectId(ticket_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Ticket not found")
        doc["id"] = str(doc.pop("_id"))
        if "created_at" in doc and hasattr(doc["created_at"], "isoformat"):
            doc["created_at"] = doc["created_at"].isoformat()
        if "updated_at" in doc and hasattr(doc["updated_at"], "isoformat"):
            doc["updated_at"] = doc["updated_at"].isoformat()
        # fetch comments
        comments = list(db["comment"].find({"ticket_id": ticket_id}).sort("created_at", 1))
        for c in comments:
            c["id"] = str(c.pop("_id"))
            if "created_at" in c and hasattr(c["created_at"], "isoformat"):
                c["created_at"] = c["created_at"].isoformat()
            if "updated_at" in c and hasattr(c["updated_at"], "isoformat"):
                c["updated_at"] = c["updated_at"].isoformat()
        doc["comments"] = comments
        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/tickets/{ticket_id}", response_model=dict)
def update_ticket(ticket_id: str, updates: TicketUpdate):
    from datetime import datetime, timezone
    try:
        to_set = {k: v for k, v in updates.model_dump(exclude_unset=True).items()}
        if not to_set:
            return {"id": ticket_id, "updated": False}
        to_set["updated_at"] = datetime.now(timezone.utc)
        result = db["ticket"].find_one_and_update(
            {"_id": ObjectId(ticket_id)},
            {"$set": to_set},
            return_document=True
        )
        if not result:
            raise HTTPException(status_code=404, detail="Ticket not found")
        result["id"] = str(result.pop("_id"))
        # convert dates
        for key in ("created_at", "updated_at"):
            if key in result and hasattr(result[key], "isoformat"):
                result[key] = result[key].isoformat()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tickets/{ticket_id}/comments", response_model=dict)
def add_comment(ticket_id: str, payload: Comment):
    try:
        # Ensure referenced ticket exists
        if not db["ticket"].find_one({"_id": ObjectId(ticket_id)}):
            raise HTTPException(status_code=404, detail="Ticket not found")
        comment_id = create_document("comment", {**payload.model_dump(), "ticket_id": ticket_id})
        return {"id": comment_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tickets/{ticket_id}/comments", response_model=List[dict])
def list_comments(ticket_id: str):
    try:
        comments = get_documents("comment", {"ticket_id": ticket_id})
        for c in comments:
            c["id"] = str(c.pop("_id"))
            if "created_at" in c and hasattr(c["created_at"], "isoformat"):
                c["created_at"] = c["created_at"].isoformat()
            if "updated_at" in c and hasattr(c["updated_at"], "isoformat"):
                c["updated_at"] = c["updated_at"].isoformat()
        return comments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
