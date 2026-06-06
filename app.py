from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List
from pathlib import Path
from io import BytesIO
from html import escape
import re

from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


# =========================
# App
# =========================

app = FastAPI(title="Array To PDF Converter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # production me apna domain daal dena
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
FONT_DIR = BASE_DIR / "fonts"


# =========================
# Models
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
# Helpers
# =========================

def safe(value) -> str:
    return escape(str(value or ""))


def clean_filename(name: str) -> str:
    name = re.sub(r"[^\w\-\.]+", "_", name.strip(), flags=re.UNICODE)
    return name or "QuestionBank"


def build_font_faces():
    """
    Automatically load every .ttf/.otf/.ttc/.woff/.woff2 present in /fonts.
    The order is file-system order; if you want priority, name files accordingly.
    """
    if not FONT_DIR.exists():
        return "", []

    allowed = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}
    faces = []
    families = []

    for font_file in sorted(FONT_DIR.iterdir()):
        if font_file.suffix.lower() not in allowed:
            continue

        family = font_file.stem.replace("_", " ")
        url = font_file.as_uri()

        if font_file.suffix.lower() in {".ttf", ".ttc"}:
            fmt = "truetype"
        elif font_file.suffix.lower() == ".otf":
            fmt = "opentype"
        elif font_file.suffix.lower() == ".woff":
            fmt = "woff"
        else:
            fmt = "woff2"

        faces.append(
            f"""
            @font-face {{
                font-family: "{family}";
                src: url("{url}") format("{fmt}");
                font-style: normal;
                font-weight: 400;
            }}
            """
        )
        families.append(f'"{family}"')

    return "\n".join(faces), families


def render_html(data: List[Section], title: str = "Question Bank") -> str:
    font_faces_css, families = build_font_faces()

    if families:
        font_stack = ", ".join(families) + ", sans-serif"
    else:
        font_stack = "sans-serif"

    sections_html = []
    for s_index, section in enumerate(data):
        topic_blocks = []
        for topic in section.topics:
            qa_blocks = []
            for idx, qa in enumerate(topic.qas, start=1):
                qa_blocks.append(
                    f"""
                    <div class="qa-card">
                        <div class="q"><span class="label">Q{idx}.</span> {safe(qa.q)}</div>
                        <div class="a"><span class="label">Answer:</span> {safe(qa.a)}</div>
                        <div class="h"><span class="label">Hack:</span> {safe(qa.hack)}</div>
                    </div>
                    """
                )

            topic_blocks.append(
                f"""
                <section class="topic">
                    <h2>{safe(topic.name)}</h2>
                    {''.join(qa_blocks)}
                </section>
                """
            )

        sections_html.append(
            f"""
            <section class="section {'page-break' if s_index > 0 else ''}">
                <h1>{safe(section.name)}</h1>
                {''.join(topic_blocks)}
            </section>
            """
        )

    return f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            {font_faces_css}

            @page {{
                size: A4;
                margin: 16mm 14mm 18mm 14mm;

                @bottom-center {{
                    content: "Page " counter(page) " / " counter(pages);
                    font-size: 9px;
                    color: #667085;
                }}
            }}

            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                font-family: {font_stack};
                color: #101828;
                font-size: 12px;
                line-height: 1.45;
                -webkit-font-smoothing: antialiased;
                text-rendering: geometricPrecision;
            }}

            .cover {{
                border: 1px solid #E4E7EC;
                border-radius: 14px;
                padding: 28px;
                margin-bottom: 18px;
                background: #F8FAFC;
            }}

            .cover h1 {{
                margin: 0 0 8px 0;
                font-size: 26px;
                line-height: 1.15;
            }}

            .cover p {{
                margin: 0;
                color: #475467;
            }}

            .section {{
                margin-bottom: 18px;
            }}

            .section h1 {{
                font-size: 22px;
                margin: 0 0 12px 0;
                padding-bottom: 6px;
                border-bottom: 2px solid #D0D5DD;
            }}

            .topic {{
                margin: 0 0 14px 0;
                page-break-inside: avoid;
                break-inside: avoid;
            }}

            .topic h2 {{
                font-size: 16px;
                margin: 0 0 8px 0;
                padding: 8px 10px;
                background: #EFF8FF;
                border-left: 4px solid #1570EF;
                border-radius: 8px;
            }}

            .qa-card {{
                border: 1px solid #EAECF0;
                border-radius: 10px;
                padding: 10px 12px;
                margin: 0 0 8px 0;
                background: #FFFFFF;
                page-break-inside: avoid;
                break-inside: avoid;
            }}

            .q, .a, .h {{
                margin: 4px 0;
            }}

            .label {{
                font-weight: 700;
                color: #344054;
            }}

            .q {{
                font-weight: 700;
            }}

            .a {{
                color: #067647;
            }}

            .h {{
                color: #B54708;
            }}

            .page-break {{
                page-break-before: always;
                break-before: page;
            }}
        </style>
    </head>
    <body>
        <div class="cover">
            <h1>{safe(title)}</h1>
            <p>Generated PDF with Unicode-safe HTML/CSS rendering and font fallback.</p>
        </div>

        {''.join(sections_html)}
    </body>
    </html>
    """


def html_to_pdf_bytes(html_str: str) -> bytes:
    font_config = FontConfiguration()
    html = HTML(string=html_str, base_url=str(BASE_DIR))
    css = CSS(string="", font_config=font_config)
    return html.write_pdf(stylesheets=[css], font_config=font_config)


# =========================
# Routes
# =========================

@app.get("/")
async def home():
    return {
        "status": "running",
        "message": "PDF API ready"
    }


@app.post("/generate-pdf")
async def generate_pdf(data: List[Section]):
    try:
        html_str = render_html(data, title="Question Bank")
        pdf_bytes = html_to_pdf_bytes(html_str)

        buffer = BytesIO(pdf_bytes)
        filename = clean_filename("QuestionBank") + ".pdf"

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )