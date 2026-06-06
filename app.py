from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from io import BytesIO

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak
)

from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production me specific domain dena
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unicode Font
pdfmetrics.registerFont(
    TTFont(
        "Noto",
        "fonts/NotoSansDevanagari-Regular.ttf"
    )
)

# ------------------------
# Models
# ------------------------

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

# ------------------------
# PDF Generator
# ------------------------

def build_pdf(data):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        rightMargin=25,
        leftMargin=25,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontName="Noto",
        fontSize=22,
        leading=30
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Noto",
        fontSize=18
    )

    topic_style = ParagraphStyle(
        "Topic",
        parent=styles["Heading3"],
        fontName="Noto",
        fontSize=14
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Noto",
        fontSize=10,
        leading=16
    )

    story = []

    story.append(
        Paragraph("Question Bank", title_style)
    )

    story.append(
        Spacer(1, 20)
    )

    for section in data:

        story.append(
            Paragraph(section.name, section_style)
        )

        story.append(
            Spacer(1, 10)
        )

        for topic in section.topics:

            story.append(
                Paragraph(topic.name, topic_style)
            )

            story.append(
                Spacer(1, 5)
            )

            for idx, qa in enumerate(topic.qas, start=1):

                story.append(
                    Paragraph(
                        f"<b>Q{idx}:</b> {qa.q}",
                        body_style
                    )
                )

                story.append(
                    Paragraph(
                        f"<b>Answer:</b> {qa.a}",
                        body_style
                    )
                )

                story.append(
                    Paragraph(
                        f"<b>Hack:</b> {qa.hack}",
                        body_style
                    )
                )

                story.append(
                    Spacer(1, 8)
                )

        story.append(PageBreak())

    doc.build(story)

    buffer.seek(0)

    return buffer

# ------------------------
# API
# ------------------------

@app.post("/generate-pdf")
async def generate_pdf(data: List[Section]):

    pdf = build_pdf(data)

    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
            "attachment; filename=QuestionBank.pdf"
        }
    )

@app.get("/")
async def home():
    return {
        "status": "running"
    }