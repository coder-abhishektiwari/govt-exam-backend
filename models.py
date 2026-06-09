from typing import Any, Dict, List, Optional

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


class PDFGenerationRequest(BaseModel):
    data: List[Section]
    title: str = "Question Bank"
    filename: str = "QuestionBank"


class Announcement(BaseModel):
    id: str
    title: str
    description: str
    icon: str = "⚠️"
    link: Optional[str] = None


class Bulletin(BaseModel):
    id: str
    date: str
    title: str
    link: str = "#"
    is_new: bool = False


class AnalyticsMetric(BaseModel):
    label: str
    value: str
    description: str

class QuizQuestion(BaseModel):
    id: str
    q: str
    options: List[str]
    answer: int
    explanation: str

class QuizTopic(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    questions: List[QuizQuestion]

class DailyQuiz(BaseModel):
    daily_quizes: List[QuizTopic]

class QuizTopicsResponse(BaseModel):
    topics: List[QuizTopic]

class MockQuestionSchema(BaseModel):
    q: str
    options: List[str]
    answer: int
    explanation: Optional[str] = None

class MockTestSchema(BaseModel):
    id: str
    title: str
    description: str
    duration: int
    total_questions: int
    total_marks: float  
    negativeMarking: float
    passingMarks: float
    category: str
    questions: List[MockQuestionSchema]

# Main Response Model
class MockTestsResponse(BaseModel):
    mock_tests: List[MockTestSchema]