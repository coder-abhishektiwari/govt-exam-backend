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


# 1. Individual Question Model (Matches frontend precisely)
class MockQuestionSchema(BaseModel):
    q: str
    options: List[str]
    answer: int
    explanation: Optional[str] = None
    sectionId: Optional[str] = None
    specialty: Optional[str] = None
    passage: Optional[str] = None
    examTag: Optional[str] = None

# 2. Config schemas for Layout engines (Banking/GATE style features)
class SectionConfigSchema(BaseModel):
    id: str
    label: str
    duration: int
    noNegative: Optional[bool] = False

class SessionSchema(BaseModel):
    id: str
    label: str
    sectionIds: List[str]
    noNegative: Optional[bool] = False

# 3. Upgraded Master Mock Test Schema (Every meta key made Optional for safety)
class MockTestSchema(BaseModel):
    id: str
    title: Optional[str] = "Mock Test"
    description: Optional[str] = ""
    duration: Optional[int] = 60
    total_questions: Optional[int] = 0
    total_marks: Optional[float] = 0.0
    negativeMarking: Optional[float] = 0.0
    passingMarks: Optional[float] = 0.0
    category: Optional[str] = "General"
    
    # Live questions array mapping
    questions: List[MockQuestionSchema] = Field(default_factory=list)
    
    # Layout engine fields (Made fully optional)
    layoutType: Optional[str] = "STANDARD"
    sections: Optional[List[SectionConfigSchema]] = None
    sessions: Optional[List[SessionSchema]] = None
    specialties: Optional[List[str]] = None
    path: Optional[str] = None # To handle the file index string cleanly

# 4. Fallback wrapping matching list response 
class MockTestsResponse(BaseModel):
    mock_tests: List[MockTestSchema]