from typing import Any, Dict, List

from pydantic import BaseModel, Field


class QA(BaseModel):
    q: str
    a: str
    hack: str


class Topic(BaseModel):
    name: str
    qas: List[QA]


class Section(BaseModel):
    name: str
    topics: List[Topic]


class QuestionPaper(BaseModel):
    id: str
    title: str
    display_name: str
    filename: str
    subject: str
    exam_board: str
    total_questions: int
    sections: List[Section]
    metadata: Dict[str, Any] = Field(default_factory=dict)
