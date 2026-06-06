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
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;700&display=swap" rel="stylesheet">
    <style>
        @page {{ 
            size: A4; 
            margin: 16mm 14mm 20mm 14mm;
            @bottom-center {{ 
                content: "Page " counter(page) " / " counter(pages); 
                font-size: 9px; 
                color: #667085; 
            }}
        }}
        
        * {{ box-sizing: border-box; }}
        
        body {{ 
            margin: 0; 
            font-family: 'Noto Sans Devanagari', sans-serif; 
            color: #101828; 
            font-size: 12px; 
            line-height: 1.45;
            background: white;
        }}
        
        /* Cover Page */
        .cover {{
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 30px;
            border-bottom: 2px solid #e5e7eb;
        }}
        
        .logo {{
            font-size: 48px;
            margin-bottom: 20px;
        }}
        
        .cover h1 {{
            font-size: 28px;
            color: #1a3c5e;
            margin: 10px 0;
        }}
        
        .cover p {{
            color: #6b7280;
            margin: 5px 0;
        }}
        
        .generated-info {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px dashed #d1d5db;
            font-size: 10px;
            color: #9ca3af;
        }}
        
        /* Footer */
        .footer {{
            position: running(footer);
            text-align: center;
            font-size: 9px;
            color: #6b7280;
            padding: 10px 0;
            border-top: 1px solid #e5e7eb;
            margin-top: 30px;
        }}
        
        .footer-content {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        .footer-links a {{
            color: #3b82f6;
            text-decoration: none;
            margin: 0 8px;
        }}
        
        /* Question Bank Styles */
        .section {{
            margin-bottom: 18px;
        }}
        
        .section h1 {{
            font-size: 20px;
            margin: 0 0 12px 0;
            padding-bottom: 6px;
            border-bottom: 2px solid #1a3c5e;
            color: #1a3c5e;
        }}
        
        .topic {{
            margin: 0 0 14px 0;
            page-break-inside: avoid;
            break-inside: avoid;
        }}
        
        .topic h2 {{
            font-size: 16px;
            margin: 0 0 8px 0;
            padding: 8px 12px;
            background: #eff6ff;
            border-left: 4px solid #1a3c5e;
            border-radius: 8px;
            color: #1e3a8a;
        }}
        
        .qa-card {{
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 10px 14px;
            margin: 0 0 8px 0;
            background: #ffffff;
            page-break-inside: avoid;
            break-inside: avoid;
        }}
        
        .label {{
            font-weight: 700;
            color: #374151;
        }}
        
        .q {{
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 6px;
        }}
        
        .a {{
            color: #047857;
            margin: 4px 0;
        }}
        
        .h {{
            color: #b45309;
            margin: 4px 0;
            font-size: 11px;
        }}
        
        .page-break {{
            page-break-before: always;
            break-before: page;
        }}
        
        @page {{
            @bottom-center {{
                content: "Page " counter(page) " / " counter(pages);
            }}
        }}
    </style>
    </head>
    <body>
        <!-- COVER PAGE -->
        <div class="cover">
            <div class="logo">📚 📖 🎯</div>
            <h1>{safe(title)}</h1>
            <p>Comprehensive Question Bank for Exam Preparation</p>
            <div class="generated-info">
                <p>📅 Generated on: {__import__('datetime').datetime.now().strftime('%d %B %Y at %I:%M %p')}</p>
                <p>🔗 Source: <strong>national-digital-exam-prep-hub.onrender.com</strong></p>
                <p>📧 Support: support@examhub.com | 📞 Helpline: 1800-XXX-XXXX</p>
            </div>
        </div>
        
        <!-- QUESTION BANK CONTENT -->
        {''.join(sections_html)}
        
        <!-- FOOTER ON EVERY PAGE -->
        <div class="footer">
            <div class="footer-content">
                <span>© 2026 National Digital Exam Preparation Hub</span>
                <div class="footer-links">
                    <a href="#">Terms</a> | 
                    <a href="#">Privacy</a> | 
                    <a href="#">Contact</a>
                </div>
                <span>Version 2.0 | All Rights Reserved</span>
            </div>
            <div style="margin-top: 5px; font-size: 8px;">
                This document is digitally generated and verified. For any discrepancies, contact support@examhub.com
            </div>
        </div>
    </body>
    </html>
    """


    
font_config = FontConfiguration()

async def html_to_pdf(html_str: str) -> bytes:
    def _render():
        html = HTML(string=html_str)
        return html.write_pdf(font_config=font_config)
    return await asyncio.to_thread(_render)

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