from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from typing import List
from io import BytesIO

from xml.sax.saxutils import escape

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


# =========================
# APP
# =========================

app = FastAPI(title="Array To PDF Converter")


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # production me domain lagana
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# FONT
# =========================

FONT_PATH = "fonts/NotoSansDevanagari-Regular.ttf"

pdfmetrics.registerFont(
    TTFont(
        "Noto",
        FONT_PATH
    )
)


# =========================
# HELPERS
# =========================

def safe(value):
    """
    ReportLab HTML parsing crash se bachata hai.
    """
    return escape(str(value or ""))


# =========================
# MODELS
# =========================

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


# =========================
# PDF BUILDER
# =========================

def build_pdf(data: List[Section]):

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
        leading=28
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Noto",
        fontSize=18,
        leading=24
    )

    topic_style = ParagraphStyle(
        "Topic",
        parent=styles["Heading3"],
        fontName="Noto",
        fontSize=14,
        leading=20
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Noto",
        fontSize=10,
        leading=16
    )

    story = []

    # Title
    story.append(
        Paragraph(
            "Question Bank",
            title_style
        )
    )

    story.append(
        Spacer(1, 20)
    )

    # Data
    for section in data:

        story.append(
            Paragraph(
                safe(section.name),
                section_style
            )
        )

        story.append(
            Spacer(1, 10)
        )

        for topic in section.topics:

            story.append(
                Paragraph(
                    safe(topic.name),
                    topic_style
                )
            )

            story.append(
                Spacer(1, 6)
            )

            for idx, qa in enumerate(topic.qas, start=1):

                # Question
                story.append(
                    Paragraph(
                        f"<b>Q{idx}:</b> {safe(qa.q)}",
                        body_style
                    )
                )

                # Answer
                story.append(
                    Paragraph(
                        f"<b>Answer:</b> {safe(qa.a)}",
                        body_style
                    )
                )

                # Hack
                story.append(
                    Paragraph(
                        f"<b>Hack:</b> {safe(qa.hack)}",
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


# =========================
# ROUTES
# =========================

@app.get("/")
async def home():
    return {
        "status": "running",
        "message": "PDF API Ready"
    }


@app.post("/generate-pdf")
async def generate_pdf(data: List[Section]):

    pdf_buffer = build_pdf(data)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
            "attachment; filename=QuestionBank.pdf"
        }
    )