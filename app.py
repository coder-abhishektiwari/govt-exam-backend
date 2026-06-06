import hashlib
import json
from functools import lru_cache
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Tuple
from pathlib import Path
from io import BytesIO
from html import escape
import re
import asyncio
import pdfkit

# Try to import WeasyPrint as fallback
try:
    import weasyprint
    WEASY_AVAILABLE = True
except ImportError:
    WEASY_AVAILABLE = False

# =========================
# App & Config
# =========================

app = FastAPI(title="Ultra Fast PDF Converter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

# PDF engine selection (pdfkit is preferred)
USE_PDFKIT = True  # Set False to use WeasyPrint fallback

# Optional: wkhtmltopdf binary path (if not in PATH)
WKHTMLTOPDF_PATH = "/usr/local/bin/wkhtmltopdf"  # adjust for your OS

# Cache settings
MAX_CACHE_SIZE = 128  # number of PDFs to keep in memory


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
# HTML Template (constant)
# =========================

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @page {
            size: A4;
            margin: 16mm 14mm 18mm 14mm;
            @bottom-center {
                content: "Page " counter(page) " / " counter(pages);
                font-size: 9px;
                color: #667085;
            }
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: sans-serif;
            color: #101828;
            font-size: 12px;
            line-height: 1.45;
        }
        .cover {
            border: 1px solid #E4E7EC;
            border-radius: 14px;
            padding: 28px;
            margin-bottom: 18px;
            background: #F8FAFC;
        }
        .cover h1 {
            margin: 0 0 8px 0;
            font-size: 26px;
        }
        .section {
            margin-bottom: 18px;
        }
        .section h1 {
            font-size: 22px;
            margin: 0 0 12px 0;
            padding-bottom: 6px;
            border-bottom: 2px solid #D0D5DD;
        }
        .topic {
            margin: 0 0 14px 0;
            page-break-inside: avoid;
            break-inside: avoid;
        }
        .topic h2 {
            font-size: 16px;
            margin: 0 0 8px 0;
            padding: 8px 10px;
            background: #EFF8FF;
            border-left: 4px solid #1570EF;
            border-radius: 8px;
        }
        .qa-card {
            border: 1px solid #EAECF0;
            border-radius: 10px;
            padding: 10px 12px;
            margin: 0 0 8px 0;
            background: #FFFFFF;
            page-break-inside: avoid;
            break-inside: avoid;
        }
        .label { font-weight: 700; color: #344054; }
        .q { font-weight: 700; }
        .a { color: #067647; }
        .h { color: #B54708; }
        .page-break {
            page-break-before: always;
            break-before: page;
        }
    </style>
</head>
<body>
    <div class="cover">
        <h1>{title}</h1>
        <p>Generated PDF with ultra‑fast engine + caching.</p>
    </div>
    {sections_html}
</body>
</html>
"""


# =========================
# Helpers
# =========================

def safe(value) -> str:
    return escape(str(value or ""))

def clean_filename(name: str) -> str:
    return re.sub(r"[^\w\-\.]+", "_", name.strip(), flags=re.UNICODE) or "QuestionBank"

def compute_content_hash(data: List[Section]) -> str:
    """Generate MD5 hash from the input data (ignoring order? but order matters)."""
    # Convert to stable JSON representation
    json_str = json.dumps([s.dict() for s in data], sort_keys=True, ensure_ascii=False)
    return hashlib.md5(json_str.encode("utf-8")).hexdigest()

def build_html(data: List[Section], title: str = "Question Bank") -> str:
    """Render HTML using the constant template."""
    sections_html = []
    for s_idx, section in enumerate(data):
        topics_html = []
        for topic in section.topics:
            qas_html = []
            for q_idx, qa in enumerate(topic.qas, start=1):
                qas_html.append(f"""
                <div class="qa-card">
                    <div class="q"><span class="label">Q{q_idx}.</span> {safe(qa.q)}</div>
                    <div class="a"><span class="label">Answer:</span> {safe(qa.a)}</div>
                    <div class="h"><span class="label">Hack:</span> {safe(qa.hack)}</div>
                </div>
                """)
            topics_html.append(f"""
            <section class="topic">
                <h2>{safe(topic.name)}</h2>
                {''.join(qas_html)}
            </section>
            """)
        sections_html.append(f"""
        <section class="section {'page-break' if s_idx > 0 else ''}">
            <h1>{safe(section.name)}</h1>
            {''.join(topics_html)}
        </section>
        """)
    return HTML_TEMPLATE.format(title=safe(title), sections_html=''.join(sections_html))


# =========================
# PDF Generation Engines (thread‑safe)
# =========================

async def generate_pdf_with_pdfkit(html_str: str) -> bytes:
    """Use pdfkit (wkhtmltopdf) – very fast."""
    def _render():
        options = {
            'page-size': 'A4',
            'margin-top': '16mm',
            'margin-right': '14mm',
            'margin-bottom': '18mm',
            'margin-left': '14mm',
            'encoding': 'UTF-8',
            'quiet': '',  # reduce console output
            'enable-local-file-access': None,
        }
        if WKHTMLTOPDF_PATH:
            config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
            return pdfkit.from_string(html_str, False, options=options, configuration=config)
        else:
            return pdfkit.from_string(html_str, False, options=options)
    return await asyncio.to_thread(_render)


async def generate_pdf_with_weasyprint(html_str: str) -> bytes:
    """Fallback to WeasyPrint – slower but used if pdfkit is not available."""
    def _render():
        html = weasyprint.HTML(string=html_str, base_url=str(BASE_DIR))
        return html.write_pdf()
    return await asyncio.to_thread(_render)


# =========================
# Caching Decorator
# =========================

class PDFCache:
    """Simple in‑memory LRU cache for PDF bytes."""
    def __init__(self, maxsize=128):
        self.cache = {}
        self.maxsize = maxsize
        self.order = []  # list of keys in order of access

    def get(self, key):
        if key in self.cache:
            # move to end (most recent)
            self.order.remove(key)
            self.order.append(key)
            return self.cache[key]
        return None

    def put(self, key, value):
        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.maxsize:
            # evict oldest
            oldest = self.order.pop(0)
            del self.cache[oldest]
        self.cache[key] = value
        self.order.append(key)

pdf_cache = PDFCache(maxsize=MAX_CACHE_SIZE)


# =========================
# API Endpoint
# =========================

@app.get("/")
async def home():
    return {"status": "ready", "engine": "pdfkit" if USE_PDFKIT else "weasyprint", "caching": True}

@app.post("/generate-pdf")
async def generate_pdf(data: List[Section]):
    try:
        # Compute cache key based on input content
        content_hash = compute_content_hash(data)
        cached_pdf = pdf_cache.get(content_hash)
        if cached_pdf is not None:
            # Return cached PDF instantly
            buffer = BytesIO(cached_pdf)
            filename = clean_filename("QuestionBank") + ".pdf"
            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"',
                         "X-Cache": "HIT"}
            )

        # Generate HTML (this is fast)
        html_str = build_html(data, title="Question Bank")

        # Generate PDF using chosen engine
        if USE_PDFKIT:
            try:
                pdf_bytes = await generate_pdf_with_pdfkit(html_str)
            except Exception as e:
                # If pdfkit fails, fallback to WeasyPrint if available
                if WEASY_AVAILABLE:
                    pdf_bytes = await generate_pdf_with_weasyprint(html_str)
                else:
                    raise e
        else:
            pdf_bytes = await generate_pdf_with_weasyprint(html_str)

        # Store in cache
        pdf_cache.put(content_hash, pdf_bytes)

        buffer = BytesIO(pdf_bytes)
        filename = clean_filename("QuestionBank") + ".pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"',
                     "X-Cache": "MISS"}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})