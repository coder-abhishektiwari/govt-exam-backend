import hashlib
import json
import re
import asyncio
from io import BytesIO
from html import escape
from pathlib import Path
from typing import List
from functools import lru_cache

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

# PDF engines
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False

try:
    import weasyprint
    WEASY_AVAILABLE = True
except ImportError:
    WEASY_AVAILABLE = False


app = FastAPI(title="Ultra Fast PDF Converter")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

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
# HTML Template (fixed)
# =========================
HTML_TEMPLATE = """
<!doctype html>
<html>
<head><meta charset="utf-8">
<style>
    @page { size: A4; margin: 16mm 14mm 18mm 14mm;
            @bottom-center { content: "Page " counter(page) " / " counter(pages); font-size: 9px; color: #667085; } }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: sans-serif; color: #101828; font-size: 12px; line-height: 1.45; }
    .cover { border: 1px solid #E4E7EC; border-radius: 14px; padding: 28px; margin-bottom: 18px; background: #F8FAFC; }
    .cover h1 { margin: 0 0 8px 0; font-size: 26px; }
    .section { margin-bottom: 18px; }
    .section h1 { font-size: 22px; margin: 0 0 12px 0; padding-bottom: 6px; border-bottom: 2px solid #D0D5DD; }
    .topic { margin: 0 0 14px 0; page-break-inside: avoid; break-inside: avoid; }
    .topic h2 { font-size: 16px; margin: 0 0 8px 0; padding: 8px 10px; background: #EFF8FF; border-left: 4px solid #1570EF; border-radius: 8px; }
    .qa-card { border: 1px solid #EAECF0; border-radius: 10px; padding: 10px 12px; margin: 0 0 8px 0; background: #FFF; page-break-inside: avoid; break-inside: avoid; }
    .label { font-weight: 700; color: #344054; }
    .q { font-weight: 700; }
    .a { color: #067647; }
    .h { color: #B54708; }
    .page-break { page-break-before: always; break-before: page; }
</style>
</head>
<body>
    <div class="cover"><h1>{title}</h1><p>Fast PDF with caching</p></div>
    {sections_html}
</body>
</html>
"""

def safe(value) -> str:
    return escape(str(value or ""))

def clean_filename(name: str) -> str:
    return re.sub(r"[^\w\-\.]+", "_", name.strip(), flags=re.UNICODE) or "QuestionBank"

def build_html(data: List[Section], title: str = "Question Bank") -> str:
    sections = []
    for s_idx, sec in enumerate(data):
        topics_html = []
        for topic in sec.topics:
            qas_html = []
            for q_idx, qa in enumerate(topic.qas, 1):
                qas_html.append(f"""
                <div class="qa-card">
                    <div class="q"><span class="label">Q{q_idx}.</span> {safe(qa.q)}</div>
                    <div class="a"><span class="label">Answer:</span> {safe(qa.a)}</div>
                    <div class="h"><span class="label">Hack:</span> {safe(qa.hack)}</div>
                </div>""")
            topics_html.append(f"""
            <section class="topic"><h2>{safe(topic.name)}</h2>{''.join(qas_html)}</section>""")
        sections.append(f"""
        <section class="section {'page-break' if s_idx else ''}">
            <h1>{safe(sec.name)}</h1>{''.join(topics_html)}
        </section>""")
    return HTML_TEMPLATE.format(title=safe(title), sections_html=''.join(sections))

# =========================
# PDF Generation (async threads)
# =========================
async def render_pdf_pdfkit(html: str) -> bytes:
    def _render():
        options = {
            'page-size': 'A4',
            'margin-top': '16mm',
            'margin-right': '14mm',
            'margin-bottom': '18mm',
            'margin-left': '14mm',
            'encoding': 'UTF-8',
            'quiet': ''
        }
        # wkhtmltopdf path on Render (installed via build script)
        config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
        return pdfkit.from_string(html, False, options=options, configuration=config)
    return await asyncio.to_thread(_render)

async def render_pdf_weasy(html: str) -> bytes:
    def _render():
        return weasyprint.HTML(string=html).write_pdf()
    return await asyncio.to_thread(_render)

# =========================
# Caching (in-memory LRU)
# =========================
class SimpleCache:
    def __init__(self, maxsize=64):
        self.cache = {}
        self.order = []
        self.maxsize = maxsize
    def get(self, key):
        if key in self.cache:
            self.order.remove(key)
            self.order.append(key)
            return self.cache[key]
        return None
    def put(self, key, value):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.maxsize:
            oldest = self.order.pop(0)
            del self.cache[oldest]
        self.cache[key] = value
        self.order.append(key)

pdf_cache = SimpleCache(maxsize=64)

def content_hash(data: List[Section]) -> str:
    json_str = json.dumps([s.dict() for s in data], sort_keys=True, ensure_ascii=False)
    return hashlib.md5(json_str.encode()).hexdigest()

# =========================
# API
# =========================
@app.get("/")
def home():
    return {"status": "ready", "pdfkit": PDFKIT_AVAILABLE, "weasyprint": WEASY_AVAILABLE}

@app.post("/generate-pdf")
async def generate_pdf(data: List[Section]):
    try:
        h = content_hash(data)
        cached = pdf_cache.get(h)
        if cached:
            return StreamingResponse(BytesIO(cached), media_type="application/pdf",
                                     headers={"Content-Disposition": f'attachment; filename="{clean_filename("QuestionBank")}.pdf"',
                                              "X-Cache": "HIT"})

        html = build_html(data)
        if PDFKIT_AVAILABLE:
            pdf_bytes = await render_pdf_pdfkit(html)
        elif WEASY_AVAILABLE:
            pdf_bytes = await render_pdf_weasy(html)
        else:
            raise RuntimeError("No PDF engine available (install pdfkit or weasyprint)")

        pdf_cache.put(h, pdf_bytes)
        return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf",
                                 headers={"Content-Disposition": f'attachment; filename="{clean_filename("QuestionBank")}.pdf"',
                                          "X-Cache": "MISS"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})