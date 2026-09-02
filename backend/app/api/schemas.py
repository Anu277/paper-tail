from pydantic import BaseModel


class ResearchRequest(BaseModel):
    question: str


class ClaimResponse(BaseModel):
    text: str
    paper_id: str


class ResearchResponse(BaseModel):
    question: str
    final_report: str
    claims: list[ClaimResponse]
    claims_by_paper: dict[str, list[str]]
    search_history: list[str]
    iterations: int
    decision: str


class CorpusPaper(BaseModel):
    paper_id: str
    title: str
    published: str
    search_query: str | None


class CorpusResponse(BaseModel):
    papers: list[CorpusPaper]


class CorpusBuildRequest(BaseModel):
    topic: str
    count: int
