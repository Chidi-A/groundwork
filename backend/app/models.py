from typing import Any, Optional

import enum
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)

class ProcessingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class DocumentFormat(str, enum.Enum):
    pdf = "pdf"
    docx = "docx"
    txt = "txt"


class InsightType(str, enum.Enum):
    pain_point = "pain_point"
    opportunity = "opportunity"
    feature_request = "feature_request"
    quote = "quote"
    jtbd = "jtbd"


class Sentiment(str, enum.Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class ReviewStatus(str, enum.Enum):
    unreviewed = "unreviewed"
    confirmed = "confirmed"
    edited = "edited"
    rejected = "rejected"


class RejectionReason(str, enum.Enum):
    wrong_type = "wrong_type"
    wrong_quote = "wrong_quote"
    not_an_insight = "not_an_insight"


class ChatRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"



class ReportStatus(str, enum.Enum):
    generating = "generating"
    ready = "ready"
    failed = "failed"


class ProjectBase(SQLModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_archived: bool | None = None


class Project(ProjectBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    is_archived: bool = Field(default=False)
    owner: Optional["User"] = Relationship(back_populates="projects")
    documents: list["Document"] = Relationship(back_populates="project", cascade_delete=True)
    insights: list["Insight"] = Relationship(back_populates="project", cascade_delete=True)
    messages: list["ChatMessage"] = Relationship(back_populates="project", cascade_delete=True)
    reports: list["Report"] = Relationship(back_populates="project", cascade_delete=True)


class ProjectPublic(ProjectBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    is_archived: bool


class ProjectsPublic(SQLModel):
    data: list[ProjectPublic]
    count: int


class DocumentBase(SQLModel):
    filename: str = Field(max_length=500)
    format: DocumentFormat 
    processing_status: ProcessingStatus = ProcessingStatus.pending
    file_size: int | None = None


class Document(DocumentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="project.id", nullable=True, ondelete="CASCADE", 
        index=True,
    )
    uploaded_by_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    uploaded_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    search_vector: Any = Field(
        default=None,
        sa_column=sa.Column(
            TSVECTOR,
            sa.Computed("to_tsvector('english', coalesce(filename, ''))", persisted=True),
        )
    )
    project: Optional["Project"] = Relationship(back_populates="documents")
    uploaded_by: Optional["User"] = Relationship()
    participants: list["Participant"] = Relationship(back_populates="document", cascade_delete=True)
    insights: list["Insight"] = Relationship(back_populates="document", cascade_delete=True)
    storage_key: str | None = Field(default=None, max_length=1000)  # e.g. "uploads/uuid/filename.pdf"
    error_message: str | None = Field(default=None, sa_type=sa.Text())


class DocumentPublic(DocumentBase):
    id: uuid.UUID
    project_id: uuid.UUID | None
    uploaded_by_id: uuid.UUID
    uploaded_at: datetime
    error_message: str | None = None


class DocumentsPublic(SQLModel):
    data: list[DocumentPublic]
    count: int


class DocumentOrganize(SQLModel):
    project_id: uuid.UUID


class ParticipantBase(SQLModel):
    name: str = Field(max_length=255)
    reference_code: str = Field(default="", max_length=20)  # e.g. "P12"
    age_range: str | None = Field(default=None, max_length=50)  # e.g. "25-34"
    segment: str | None = Field(default=None, max_length=255)


class Participant(ParticipantBase, table=True):
    __table_args__ = (
        sa.UniqueConstraint(
            "reference_code", "document_id",
            name="uq_participant_refcode_document"
        ),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(foreign_key="document.id", nullable=False, ondelete="CASCADE", index=True    )
    document: Optional["Document"] = Relationship(back_populates="participants")
    insights: list["Insight"] = Relationship(back_populates="participant")


class InsightBase(SQLModel):
    type: InsightType
    text: str
    source_quote: str | None = None
    source_location: str | None = Field(default=None, max_length=500)
    sentiment: Sentiment = Sentiment.neutral
    theme: str | None = Field(default=None, max_length=255)
    needs_review: bool = False
    review_status: ReviewStatus = ReviewStatus.unreviewed


class Insight(InsightBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID | None = Field(default=None, foreign_key="project.id", nullable=True, ondelete="CASCADE", index=True)
    document_id: uuid.UUID | None = Field(
        default=None, foreign_key="document.id", nullable=True, ondelete="CASCADE", index=True
    )
    participant_id: uuid.UUID | None = Field(
        default=None, foreign_key="participant.id", nullable=True, ondelete="SET NULL"
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=sa.Column(
            DateTime(timezone=True),
            default=get_datetime_utc,
            onupdate=get_datetime_utc,
            nullable=False,
        ),
    )
    search_vector: Any = Field(
        default=None,
        sa_column=sa.Column(
            TSVECTOR,
            sa.Computed(
                "to_tsvector('english', "
                "coalesce(text, '') || ' ' || "
                "coalesce(source_quote, '') || ' ' || "
                "coalesce(theme, ''))",
                persisted=True,
            ),
        )
    )
    embedding: Any = Field(
    default=None,
    sa_column=sa.Column(Vector(1536), nullable=True),
    )
    project: Optional["Project"] = Relationship(back_populates="insights")
    document: Optional["Document"] = Relationship(back_populates="insights")
    participant: Optional["Participant"] = Relationship(back_populates="insights")
    rejection_reason: RejectionReason | None = Field(
    default=None,
    sa_column=sa.Column(
        sa.Enum(RejectionReason, name="rejectionreason"),
        nullable=True
    )
)

class InsightPublic(InsightBase):
    id: uuid.UUID
    project_id: uuid.UUID | None
    document_id: uuid.UUID | None
    participant_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    rejection_reason: RejectionReason | None = None


class InsightsPublic(SQLModel):
    data: list[InsightPublic]
    count: int


class PassagePublic(SQLModel):
    document_id: uuid.UUID
    filename: str
    snippet: str


class SearchResults(SQLModel):
    insights: list[InsightPublic]
    passages: list[PassagePublic]


class InsightReviewAction(str, enum.Enum):
    confirm = "confirm"
    reject = "reject"


class InsightReview(SQLModel):
    action: InsightReviewAction
    rejection_reason: RejectionReason | None = None


class InsightUpdate(SQLModel):
    type: InsightType | None = None
    text: str | None = None
    source_quote: str | None = None
    source_location: str | None = Field(default=None, max_length=500)
    sentiment: Sentiment | None = None
    theme: str | None = Field(default=None, max_length=255)
    participant_id: uuid.UUID | None = None


class ChatMessage(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID | None = Field(default=None, foreign_key="project.id", nullable=True, ondelete="CASCADE", index=True)
    role: ChatRole
    content: str
    cited_insight_ids: list[str] | None = Field(
        default=None, sa_column=sa.Column(sa.JSON, nullable=True)
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    project: Optional["Project"] = Relationship(back_populates="messages")


class ChatMessagePublic(SQLModel):
    id: uuid.UUID
    project_id: uuid.UUID | None
    role: ChatRole
    content: str
    cited_insight_ids: list[str] | None
    created_at: datetime


class ChatRequest(SQLModel):
    project_id: uuid.UUID
    message: str = Field(min_length=1)
    

class Report(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="project.id", nullable=False, ondelete="CASCADE", index=True)
    status: ReportStatus = ReportStatus.generating
    markdown_content: str | None = Field(default=None, sa_type=sa.Text())  # null while generating
    insight_count_at_generation: int | None = None
    reviewed_count_at_generation: int | None = None
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    project: Optional["Project"] = Relationship(back_populates="reports")

class ReportCreate(SQLModel):
    project_id: uuid.UUID


class ReportPublic(SQLModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: ReportStatus
    markdown_content: str | None
    insight_count_at_generation: int | None
    reviewed_count_at_generation: int | None
    created_at: datetime

# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str | None = Field(default=None)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    projects: list[Project] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int



# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
