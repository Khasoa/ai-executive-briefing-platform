from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Source


class DigestItemSchema(BaseModel):
    id: str
    title: str
    detail: str
    source: Source = "Gmail"
    emailIds: list[str] = Field(default_factory=list)
    # fact = grounded in synced rows; recommendation = AI planning suggestion
    kind: Literal["fact", "recommendation"] = "fact"


class NextWeekOutlookSchema(BaseModel):
    """Forward-looking section — facts and recommendations kept distinct."""

    upcomingMeetings: list[DigestItemSchema] = Field(default_factory=list)
    upcomingDeadlines: list[DigestItemSchema] = Field(default_factory=list)
    overdueWork: list[DigestItemSchema] = Field(default_factory=list)
    crmAttention: list[DigestItemSchema] = Field(default_factory=list)
    emailFollowUps: list[DigestItemSchema] = Field(default_factory=list)
    workItems: list[DigestItemSchema] = Field(default_factory=list)
    carryForward: list[DigestItemSchema] = Field(default_factory=list)
    recommendedPriorities: list[DigestItemSchema] = Field(default_factory=list)
    risksAndWatchouts: list[DigestItemSchema] = Field(default_factory=list)
    workloadSignals: list[DigestItemSchema] = Field(default_factory=list)


class DataCoverageSchema(BaseModel):
    """Honest signals about what synced data was available."""

    emailCount: int = 0
    emailSummariesAvailable: bool = False
    emailNote: str = ""
    meetingCount: int = 0
    opportunityCount: int = 0
    workItemCount: int = 0
    notionItemCount: int = 0
    sourcesWithData: list[str] = Field(default_factory=list)


class WeeklyDigestResponse(BaseModel):
    id: str
    weekStart: str
    weekEnd: str
    weekLabel: str
    headline: str
    summary: str
    # Alias retained for clients that prefer the new name
    weekSummary: str = ""
    importantConversations: list[DigestItemSchema]
    decisionsAndApprovals: list[DigestItemSchema]
    followUps: list[DigestItemSchema]
    unresolvedItems: list[DigestItemSchema]
    notableActivity: list[DigestItemSchema]
    carryIntoNextWeek: list[DigestItemSchema]
    nextWeekOutlook: NextWeekOutlookSchema = Field(default_factory=NextWeekOutlookSchema)
    planningNote: str
    confidence: Literal["high", "medium", "low"]
    generatedBy: Literal["openai", "curated"]
    sources: list[Source]
    emailCount: int
    dataCoverage: DataCoverageSchema = Field(default_factory=DataCoverageSchema)
    generatedAt: str
    generatedLabel: str
