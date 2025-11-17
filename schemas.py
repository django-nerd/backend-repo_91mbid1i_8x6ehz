"""
Database Schemas for the IT Ticketing System

Each Pydantic model maps to a MongoDB collection. The collection name is the
lowercased class name.

- Ticket -> "ticket"
- Comment -> "comment"
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime

Priority = Literal["low", "medium", "high", "urgent"]
Status = Literal["open", "in_progress", "resolved", "closed"]


class Ticket(BaseModel):
    """Schema for support tickets (collection: ticket)"""
    title: str = Field(..., min_length=3, max_length=200, description="Short summary of the issue")
    description: str = Field(..., min_length=5, description="Detailed description of the problem")
    requester_email: EmailStr = Field(..., description="Email of the person reporting the issue")
    category: str = Field(..., description="Category like Hardware, Software, Access, Network, Other")
    priority: Priority = Field("medium", description="Ticket priority")
    status: Status = Field("open", description="Current ticket status")
    assignee: Optional[str] = Field(None, description="Assigned IT agent's name or email")


class TicketUpdate(BaseModel):
    """Partial updates for tickets"""
    title: Optional[str] = None
    description: Optional[str] = None
    requester_email: Optional[EmailStr] = None
    category: Optional[str] = None
    priority: Optional[Priority] = None
    status: Optional[Status] = None
    assignee: Optional[str] = None


class Comment(BaseModel):
    """Schema for comments on tickets (collection: comment)"""
    ticket_id: str = Field(..., description="ID of the ticket this comment belongs to")
    author: str = Field(..., description="Name or email of the commenter")
    body: str = Field(..., min_length=1, description="Comment text")


class TicketWithComments(BaseModel):
    """Response model for a ticket including comments"""
    id: str
    title: str
    description: str
    requester_email: EmailStr
    category: str
    priority: Priority
    status: Status
    assignee: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    comments: List[dict] = []
