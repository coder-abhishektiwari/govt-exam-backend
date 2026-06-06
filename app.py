from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List
from io import BytesIO
from html import escape
import re
import asyncio
import hashlib
import json

# WeasyPrint with specific font config
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration

app = FastAPI(title="PDF Converter")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
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

# Helpers
def safe(value) -> str:
    return escape(str(value or ""))

def clean_filename(name: str) -> str:
    return re.sub(r"[^\w\-\.]+", "_", name.strip(), flags=re.UNICODE) or "QuestionBank"

def build_html(data: List[Section], title: str = "Question Bank") -> str:
    sections_html = []
    for s_idx, section in enumerate(data):
        topic_blocks = []
        for topic in section.topics:
            qa_blocks = []
            for idx, qa in enumerate(topic.qas, start=1):
                qa_blocks.append(f"""
                <div class="qa-card">
                    <div class="q"><span class="label">Q{idx}.</span> {safe(qa.q)}</div>
                    <div class="a"><span class="label">Answer:</span> {safe(qa.a)}</div>
                    <div class="h"><span class="label">Hack:</span> {safe(qa.hack)}</div>
                </div>""")
            topic_blocks.append(f"""
            <section class="topic">
                <h2>{safe(topic.name)}</h2>
                {''.join(qa_blocks)}
            </section>""")
        sections_html.append(f"""
        <section class="section {'page-break' if s_idx > 0 else ''}">
            <h1>{safe(section.name)}</h1>
            {''.join(topic_blocks)}
        </section>""")
    
    return f"""
    <!doctype html>
    <html>
    <head><meta charset="utf-8">
    <style>
        @page {{ size: A4; margin: 16mm 14mm 18mm 14mm;
                @bottom-center {{ content: "Page " counter(page) " / " counter(pages); font-size: 9px; color: #667085; }} }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; font-family: sans-serif; color: #101828; font-size: 12px; line-height: 1.45; }}
        .cover {{ border: 1px solid #E4E7EC; border-radius: 14px; padding: 28px; margin-bottom: 18px; background: #F8FAFC; }}
        .cover h1 {{ margin: 0 0 8px 0; font-size: 26px; }}
        .section {{ margin-bottom: 18px; }}
        .section h1 {{ font-size: 22px; margin: 0 0 12px 0; padding-bottom: 6px; border-bottom: 2px solid #D0D5DD; }}
        .topic {{ margin: 0 0 14px 0; page-break-inside: avoid; break-inside: avoid; }}
        .topic h2 {{ font-size: 16px; margin: 0 0 8px 0; padding: 8px 10px; background: #EFF8FF; border-left: 4px solid #1570EF; border-radius: 8px; }}
        .qa-card {{ border: 1px solid #EAECF0; border-radius: 10px; padding: 10px 12px; margin: 0 0 8px 0; background: #FFF; page-break-inside: avoid; break-inside: avoid; }}
        .label {{ font-weight: 700; color: #344054; }}
        .q {{ font-weight: 700; }}
        .a {{ color: #067647; }}
        .h {{ color: #B54708; }}
        .page-break {{ page-break-before: always; break-before: page; }}
    </style>
    </head>
    <body>
        <div class="cover"><h1>{safe(title)}</h1><p>PDF Generator</p></div>
        {''.join(sections_html)}
    </body>
    </html>
    """

# Global font config
font_config = FontConfiguration()

async def html_to_pdf(html_str: str) -> bytes:
    def _render():
        html = HTML(string=html_str)
        return html.write_pdf(font_config=font_config)
    return await asyncio.to_thread(_render)

# Simple cache
pdf_cache = {}
cache_order = []
MAX_CACHE = 32

def get_cache_key(data: List[Section]) -> str:
    json_str = json.dumps([s.dict() for s in data], sort_keys=True, ensure_ascii=False)
    return hashlib.md5(json_str.encode()).hexdigest()

@app.get("/")
def home():
    return {"status": "running", "engine": "WeasyPrint", "caching": True}

@app.post("/generate-pdf")
async def generate_pdf(data: List[Section]):
    try:
        cache_key = get_cache_key(data)
        if cache_key in pdf_cache:
            return StreamingResponse(
                BytesIO(pdf_cache[cache_key]),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{clean_filename("QuestionBank")}.pdf"'}
            )
        
        html_str = build_html(data)
        pdf_bytes = await html_to_pdf(html_str)
        
        # Cache management
        if len(pdf_cache) >= MAX_CACHE:
            oldest = cache_order.pop(0)
            del pdf_cache[oldest]
        pdf_cache[cache_key] = pdf_bytes
        cache_order.append(cache_key)
        
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{clean_filename("QuestionBank")}.pdf"'}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})