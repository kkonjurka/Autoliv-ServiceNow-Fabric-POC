from typing import List, Optional

from pydantic import BaseModel, Field


class UserSummary(BaseModel):
    id: str
    full_name: str
    email: str
    title: str
    location: str
    department: str


class AssignmentGroupSummary(BaseModel):
    id: str
    name: str
    description: str
    escalation_email: str


class CategorySummary(BaseModel):
    id: str
    name: str
    subcategory: str


class NoteSummary(BaseModel):
    id: str
    created_at: str
    author: UserSummary
    note_html: str
    note_text: str


class SlaSummary(BaseModel):
    id: str
    name: str
    stage: str
    target_hours: float
    elapsed_hours: float
    breached: bool


class ChangeRequestSummary(BaseModel):
    id: str
    number: str
    title: str
    state: str
    risk: str
    planned_start: str
    planned_end: str
    implemented_at: Optional[str] = None
    relationship_type: str


class ExternalReferenceSummary(BaseModel):
    id: str
    reference_type: str
    title: str
    url: str
    source_system: str


class AssetSummary(BaseModel):
    id: str
    incident_id: str
    incident_number: Optional[str] = None
    file_name: str
    content_type: str
    description: str
    mock_url: str
    uploaded_at: str
    file_size_kb: Optional[int] = None
    width_px: Optional[int] = None
    height_px: Optional[int] = None


class KnowledgeArticleSummary(BaseModel):
    id: str
    number: str
    title: str
    category: CategorySummary
    audience: str
    content_html: str
    content_text: str
    keywords: List[str] = Field(default_factory=list)
    published_at: str
    updated_at: str
    relevance_reason: Optional[str] = None


class IncidentListItem(BaseModel):
    id: str
    number: str
    short_description: str
    state: str
    priority: str
    impact: str
    urgency: str
    opened_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    follow_up_required: bool
    requester: UserSummary
    assignee: Optional[UserSummary] = None
    assignment_group: AssignmentGroupSummary
    category: CategorySummary


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class PaginatedIncidentsResponse(BaseModel):
    pagination: PaginationMeta
    items: List[IncidentListItem]


class PaginatedKnowledgeArticlesResponse(BaseModel):
    pagination: PaginationMeta
    items: List[KnowledgeArticleSummary]


class PaginatedAssetsResponse(BaseModel):
    pagination: PaginationMeta
    items: List[AssetSummary]


class IncidentDetail(IncidentListItem):
    description_html: str
    description_text: str
    follow_up_reason: Optional[str] = None
    resolution_summary_html: Optional[str] = None
    resolution_summary_text: Optional[str] = None
    related_kb_articles: List[KnowledgeArticleSummary] = Field(default_factory=list)
    work_notes: List[NoteSummary] = Field(default_factory=list)
    resolution_notes: List[NoteSummary] = Field(default_factory=list)
    change_requests: List[ChangeRequestSummary] = Field(default_factory=list)
    slas: List[SlaSummary] = Field(default_factory=list)
    attachments: List[AssetSummary] = Field(default_factory=list)
    images: List[AssetSummary] = Field(default_factory=list)
    documents: List[AssetSummary] = Field(default_factory=list)
    external_references: List[ExternalReferenceSummary] = Field(default_factory=list)
