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
    # Calculate stats
    total_questions = sum(len(topic.qas) for section in data for topic in section.topics)
    total_topics = len([topic for section in data for topic in section.topics])
    total_sections = len(data)
    
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
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
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
            font-family: 'Noto Sans Devanagari', 'Segoe UI', sans-serif; 
            background: white;
        }}
        
        /* ========== IMPROVED COVER PAGE (No Emojis) ========== */
        .cover {{
            position: relative;
            background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
            color: white;
            padding: 60px 40px;
            border-radius: 24px;
            margin-bottom: 40px;
            page-break-after: avoid;
            break-inside: avoid;
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            overflow: hidden;
        }}
        
        /* Decorative background elements */
        .cover::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(2,132,199,0.2) 0%, transparent 70%);
            border-radius: 50%;
            pointer-events: none;
        }}
        
        .cover::after {{
            content: '';
            position: absolute;
            bottom: -30%;
            left: -10%;
            width: 250px;
            height: 250px;
            background: radial-gradient(circle, rgba(22,163,74,0.15) 0%, transparent 70%);
            border-radius: 50%;
            pointer-events: none;
        }}
        
        /* Indian Flag Tricolor Strip */
        .cover-strip {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 6px;
            background: linear-gradient(90deg, #FF9933 0%, #FF9933 33%, #FFFFFF 33%, #FFFFFF 66%, #138808 66%, #138808 100%);
        }}
        
        .logo-section {{
            text-align: center;
            margin-bottom: 30px;
            position: relative;
            z-index: 1;
        }}
        
        .logo-icon {{
            font-size: 56px;
            color: #38bdf8;
            filter: drop-shadow(0 4px 8px rgba(0,0,0,0.2));
        }}
        
        .gov-badge {{
            display: inline-block;
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(10px);
            padding: 6px 16px;
            border-radius: 40px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.3);
        }}
        
        .gov-badge i {{
            margin-right: 6px;
        }}
        
        .cover h1 {{
            font-size: 32px;
            font-weight: 800;
            margin: 0 0 12px 0;
            text-align: center;
            letter-spacing: -0.5px;
            color: white;
        }}
        
        .cover-subtitle {{
            text-align: center;
            font-size: 13px;
            color: #cbd5e1;
            margin-bottom: 30px;
            font-weight: 500;
            letter-spacing: 0.5px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin: 35px 0;
            padding: 20px 0;
            border-top: 1px solid rgba(255,255,255,0.1);
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .stat-item {{
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 28px;
            font-weight: 800;
            color: #38bdf8;
            display: block;
        }}
        
        .stat-label {{
            font-size: 10px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 6px;
        }}
        
        .generated-info {{
            background: rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 20px;
            margin-top: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .info-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            font-size: 11px;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        .info-row:last-child {{
            margin-bottom: 0;
        }}
        
        .info-label {{
            color: #94a3b8;
            font-weight: 500;
            letter-spacing: 0.5px;
        }}
        
        .info-label i {{
            width: 20px;
            margin-right: 6px;
        }}
        
        .info-value {{
            color: #e2e8f0;
            font-weight: 600;
        }}
        
        .info-value strong {{
            color: #38bdf8;
            font-weight: 700;
        }}
        
        .verification-seal {{
            text-align: center;
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px dashed rgba(255,255,255,0.2);
        }}
        
        .seal-text {{
            font-size: 9px;
            color: #64748b;
            letter-spacing: 1px;
        }}
        
        .seal-text i {{
            margin: 0 4px;
        }}
        
        /* Rest of your existing styles */
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
        
        i {{
            font-style: normal;
        }}
    </style>
    </head>
    <body>
        <!-- COVER PAGE WITH FONT AWESOME ICONS -->
        <div class="cover">
            <div class="cover-strip"></div>
            
            <div class="logo-section">
                <div class="logo-icon">
                    <i class="fas fa-graduation-cap"></i>
                </div>
            </div>
            
            <div class="gov-badge">
                <i class="fas fa-flag-checkered"></i> NATIONAL DIGITAL EXAM HUB <i class="fas fa-certificate"></i>
            </div>
            
            <h1>{safe(title)}</h1>
            <div class="cover-subtitle">Comprehensive Question Bank for Exam Preparation</div>
            
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-number">{total_questions}</span>
                    <span class="stat-label">TOTAL QUESTIONS</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{total_topics}</span>
                    <span class="stat-label">TOPICS COVERED</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{total_sections}</span>
                    <span class="stat-label">SECTIONS</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">100%</span>
                    <span class="stat-label">VERIFIED</span>
                </div>
            </div>
            
            <div class="generated-info">
                <div class="info-row">
                    <span class="info-label"><i class="far fa-calendar-alt"></i> GENERATED ON</span>
                    <span class="info-value">{__import__('datetime').datetime.now().strftime('%d %B %Y at %I:%M %p')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label"><i class="fas fa-link"></i> SOURCE</span>
                    <span class="info-value"><strong>national-digital-exam-prep-hub.onrender.com</strong></span>
                </div>
                <div class="info-row">
                    <span class="info-label"><i class="fas fa-envelope"></i> SUPPORT</span>
                    <span class="info-value">support@examhub.com</span>
                </div>
                <div class="info-row">
                    <span class="info-label"><i class="fas fa-phone-alt"></i> HELPLINE</span>
                    <span class="info-value">1800-XXX-XXXX (Toll Free)</span>
                </div>
            </div>
            
            <div class="verification-seal">
                <span class="seal-text">
                    <i class="fas fa-shield-alt"></i> DIGITALLY VERIFIED DOCUMENT <i class="fas fa-shield-alt"></i>
                </span>
            </div>
        </div>
        
        <!-- QUESTION BANK CONTENT -->
        {''.join(sections_html)}
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