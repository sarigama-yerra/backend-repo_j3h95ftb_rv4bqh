"""
Database Schemas for SomDev Solutions

Each Pydantic model corresponds to a MongoDB collection where the
collection name is the lowercase of the class name.

Use these models for validation when creating new documents.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


class Service(BaseModel):
    """SomDev services offered to clients
    Collection name: "service"
    """
    title: str = Field(..., description="Service title")
    description: str = Field(..., description="Short description of the service")
    icon: Optional[str] = Field(None, description="Lucide icon name or URL to an image")
    price_from: Optional[float] = Field(None, ge=0, description="Starting price")
    category: Optional[str] = Field(None, description="Service category")
    cta_label: Optional[str] = Field("Order Now", description="Primary CTA label")


class Project(BaseModel):
    """Completed projects to showcase
    Collection name: "project"
    """
    title: str = Field(..., description="Project title")
    description: str = Field(..., description="Short summary")
    image: Optional[HttpUrl] = Field(None, description="Preview image URL")
    tags: List[str] = Field(default_factory=list, description="Tech or highlights")


class Interaction(BaseModel):
    """Tracks customer interactions like service views and orders
    Collection name: "interaction"
    """
    user_id: str = Field(..., description="Anonymous user id (from client)")
    service_id: Optional[str] = Field(None, description="Related service id if applicable")
    type: Literal["view", "order"] = Field(..., description="Interaction type")
    details: Optional[dict] = Field(default_factory=dict, description="Extra payload such as order form data")


class Message(BaseModel):
    """Chat messages for simple history keeping
    Collection name: "message"
    """
    user_id: str
    role: Literal["user", "assistant"]
    content: str
