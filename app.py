from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Optional, Dict
from io import BytesIO
from html import escape
import asyncio
import hashlib
import json
from datetime import datetime

from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
from config import CACHE_DIR, MAX_CACHE_FILES, ANNOUNCEMENTS_FILE, BULLETINS_FILE, ANALYTICS_FILE, DAILY_QUIZ_FILE, MOCK_INDEX_FILE, MOCK_PAPERS_DIR
from models import PDFGenerationRequest, QuestionPaper, Section, Announcement, Bulletin, AnalyticsMetric, QuizQuestion, DailyQuiz, QuizTopicsResponse, QuizTopic, MockTestSchema
from paper_repository import paper_repository
app = FastAPI(title="Question Paper PDF Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_paper(paper_id: str) -> Optional[Dict]:
    return paper_repository.load(paper_id)

def save_paper(paper_id: str, paper_data: Dict):
    paper_repository.save(paper_id, paper_data)

def delete_paper(paper_id: str):
    return paper_repository.delete(paper_id)

def get_all_papers_metadata():
    return paper_repository.list_metadata()

def load_data_file(file_path):
    """Load JSON data file"""
    if not file_path.exists():
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

def save_data_file(file_path, data):
    """Save JSON data file"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
        return False

def get_cache_key(paper_id: str, sections: List[Section]) -> str:
    """Generate cache key"""
    json_str = json.dumps({
        "paper_id": paper_id,
        "data": [s.dict() for s in sections]
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(json_str.encode()).hexdigest()

def get_cached_pdf(cache_key: str) -> Optional[bytes]:
    """Check cache"""
    cache_file = CACHE_DIR / f"{cache_key}.pdf"
    if cache_file.exists():
        file_age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if file_age < 7 * 24 * 3600:
            with open(cache_file, 'rb') as f:
                return f.read()
        else:
            cache_file.unlink()
    return None

def save_to_cache(cache_key: str, pdf_bytes: bytes):
    """Save to cache"""
    cache_file = CACHE_DIR / f"{cache_key}.pdf"
    with open(cache_file, 'wb') as f:
        f.write(pdf_bytes)
    
    # Cleanup old files
    cache_files = sorted(CACHE_DIR.glob("*.pdf"), key=lambda x: x.stat().st_mtime)
    while len(cache_files) > MAX_CACHE_FILES:
        oldest = cache_files.pop(0)
        oldest.unlink()

# ============ HTML GENERATION ============
def safe(value) -> str:
    return escape(str(value or ""))

def build_html(paper: Dict, sections: List[Section]) -> str:
    """Generate HTML"""
    total_questions = sum(len(topic.qas) for section in sections for topic in section.topics)
    total_topics = len([topic for section in sections for topic in section.topics])
    total_sections = len(sections)
    
    sections_html = []
    for s_idx, section in enumerate(sections):
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
    
    metadata = paper.get("metadata", {})
    
    return f"""
    <!doctype html>
    <html>
    <head><meta charset="utf-8">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        @page {{ size: A4; margin: 16mm 14mm 20mm 14mm;
                @bottom-center {{ content: "Page " counter(page) " / " counter(pages); font-size: 9px; color: #667085; }} }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; font-family: 'Noto Sans Devanagari', sans-serif; background: white; }}
        
        .cover-page {{ page-break-after: always; break-after: page; margin: -16mm -14mm 0 -14mm; height: 297mm; display: flex; align-items: center; justify-content: center; }}
        .cover {{ width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center; position: relative; background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%); color: white; padding: 60px 50px; }}
        .cover-strip {{ position: absolute; top: 0; left: 0; right: 0; height: 6px; background: linear-gradient(90deg, #FF9933 0%, #FF9933 33%, #FFFFFF 33%, #FFFFFF 66%, #138808 66%, #138808 100%); }}
        .logo-section {{ text-align: center; margin-bottom: 30px; }}
        .logo-icon {{ font-size: 72px; color: #38bdf8; }}
        .gov-badge {{ display: inline-block; background: rgba(255,255,255,0.15); padding: 8px 20px; border-radius: 40px; font-size: 12px; font-weight: 600; margin-bottom: 30px; }}
        .cover h1 {{ font-size: 32px; font-weight: 800; margin: 0 0 16px 0; text-align: center; color: white; }}
        .cover-subtitle {{ text-align: center; font-size: 14px; color: #cbd5e1; margin-bottom: 40px; }}
        
        .exam-details {{ background: rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; margin: 20px 0; }}
        .exam-detail-row {{ display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 12px; }}
        
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; padding: 20px 0; border-top: 1px solid rgba(255,255,255,0.1); border-bottom: 1px solid rgba(255,255,255,0.1); }}
        .stat-item {{ text-align: center; }}
        .stat-number {{ font-size: 28px; font-weight: 800; color: #38bdf8; display: block; }}
        .stat-label {{ font-size: 10px; color: #94a3b8; text-transform: uppercase; margin-top: 8px; }}
        
        .generated-info {{ background: rgba(255,255,255,0.08); border-radius: 16px; padding: 20px; margin-top: 30px; }}
        .info-row {{ display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 11px; }}
        .verification-seal {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px dashed rgba(255,255,255,0.2); }}
        
        .section {{ margin-bottom: 18px; }}
        .section h1 {{ font-size: 20px; margin: 0 0 12px 0; padding-bottom: 6px; border-bottom: 2px solid #1a3c5e; color: #1a3c5e; }}
        .topic {{ margin: 0 0 14px 0; page-break-inside: avoid; }}
        .topic h2 {{ font-size: 16px; margin: 0 0 8px 0; padding: 8px 12px; background: #eff6ff; border-left: 4px solid #1a3c5e; border-radius: 8px; color: #1e3a8a; }}
        .qa-card {{ border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px 14px; margin: 0 0 8px 0; background: #ffffff; page-break-inside: avoid; }}
        .label {{ font-weight: 700; color: #374151; }}
        .q {{ font-weight: 600; color: #1f2937; margin-bottom: 6px; }}
        .a {{ color: #047857; margin: 4px 0; }}
        .h {{ color: #b45309; margin: 4px 0; font-size: 11px; }}
        .page-break {{ page-break-before: always; }}
    </style>
    </head>
    <body>
        <div class="cover-page">
            <div class="cover">
                <div class="cover-strip"></div>
                <div class="logo-section">
                    <div class="logo-icon"><i class="fas fa-graduation-cap"></i></div>
                </div>
                <div class="gov-badge">
                    <i class="fas fa-flag-checkered"></i> NATIONAL DIGITAL EXAM HUB <i class="fas fa-certificate"></i>
                </div>
                <h1>{safe(paper.get('title', 'Question Bank'))}</h1>
                <div class="cover-subtitle">{safe(paper.get('display_name', 'Exam Preparation Material'))}</div>
                
                <div class="exam-details">
                    <div class="exam-detail-row"><span><i class="fas fa-building"></i> Exam Board:</span><span>{safe(paper.get('exam_board', 'N/A'))}</span></div>
                    <div class="exam-detail-row"><span><i class="fas fa-book"></i> Subject:</span><span>{safe(paper.get('subject', 'N/A'))}</span></div>
                    <div class="exam-detail-row"><span><i class="fas fa-chart-line"></i> Difficulty:</span><span>{safe(metadata.get('difficulty', 'Medium'))}</span></div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-item"><span class="stat-number">{total_questions}</span><span class="stat-label">QUESTIONS</span></div>
                    <div class="stat-item"><span class="stat-number">{total_topics}</span><span class="stat-label">TOPICS</span></div>
                    <div class="stat-item"><span class="stat-number">{total_sections}</span><span class="stat-label">SECTIONS</span></div>
                    <div class="stat-item"><span class="stat-number">{paper.get('version', '1.0')}</span><span class="stat-label">VERSION</span></div>
                </div>
                
                <div class="generated-info">
                    <div class="info-row"><span><i class="far fa-calendar-alt"></i> Generated:</span><span>{datetime.now().strftime('%d %B %Y at %I:%M %p')}</span></div>
                    <div class="info-row"><span><i class="fas fa-link"></i> Source:</span><span><strong>getreadyforexam.my-board.org</strong></span></div>
                    <div class="info-row"><span><i class="fas fa-tag"></i> Paper ID:</span><span>{safe(paper.get('id', 'N/A'))}</span></div>
                </div>
                
                <div class="verification-seal"><i class="fas fa-shield-alt"></i> DIGITALLY VERIFIED DOCUMENT <i class="fas fa-shield-alt"></i></div>
            </div>
        </div>
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

# ============ API ENDPOINTS ============

@app.get("/")
async def home():
    papers = get_all_papers_metadata()
    return {
        "status": "running",
        "total_papers": len(papers),
        "papers": papers,
        "endpoints": {
            "list": "GET /papers",
            "get": "GET /paper/{paper_id}",
            "pdf": "GET /paper/{paper_id}/pdf",
            "generate_pdf": "POST /generate-pdf"
        }
    }

@app.head("/")
async def health_check():
    return JSONResponse(content=None)

@app.get("/papers")
async def list_papers():
    metadata = get_all_papers_metadata()

    sectors = sorted(
        list(
            {
                paper.get("sector")
                for paper in metadata
                if isinstance(paper, dict) and paper.get("sector")
            }
        )
    )

    return {
        "papers": metadata,
        "sectors": sectors
    }

@app.get("/paper/{paper_id}")
async def get_paper(paper_id: str):
    """Get complete paper data"""
    paper_data = load_paper(paper_id)
    if not paper_data:
        raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found")
    return paper_data

@app.post("/generate-pdf")
async def generate_pdf_from_payload(request: PDFGenerationRequest):
    """Generate a PDF from the frontend's existing payload contract."""
    try:
        paper_data = {
            "id": "generated-paper",
            "title": request.title,
            "display_name": request.title,
            "filename": request.filename,
        }
        html_str = build_html(paper_data, request.data)
        pdf_bytes = await html_to_pdf(html_str)

        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{request.filename}.pdf"'
                )
            },
        )
    except Exception as error:
        return JSONResponse(status_code=500, content={"error": str(error)})

@app.get("/paper/{paper_id}/pdf")
async def generate_pdf(paper_id: str):
    """Generate PDF for paper"""
    try:
        # Load paper
        paper_data = load_paper(paper_id)
        if not paper_data:
            raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found")
        
        # Convert sections
        sections = [Section(**section) for section in paper_data.get("sections", [])]
        
        # Check cache
        cache_key = get_cache_key(paper_id, sections)
        cached_pdf = get_cached_pdf(cache_key)
        
        if cached_pdf:
            filename = paper_data.get("filename", paper_id)
            return StreamingResponse(
                BytesIO(cached_pdf),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}.pdf"',
                    "X-Cache": "HIT"
                }
            )
        
        # Generate new PDF
        html_str = build_html(paper_data, sections)
        pdf_bytes = await html_to_pdf(html_str)
        
        # Save to cache
        save_to_cache(cache_key, pdf_bytes)
        
        filename = paper_data.get("filename", paper_id)
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.pdf"',
                "X-Cache": "MISS"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/paper/create")
async def create_paper(paper: QuestionPaper):
    """Create new paper"""
    try:
        paper_data = paper.dict()
        save_paper(paper.id, paper_data)
        return {"status": "success", "message": f"Paper '{paper.id}' created"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/paper/{paper_id}")
async def delete_paper_endpoint(paper_id: str):
    """Delete paper"""
    if not delete_paper(paper_id):
        raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found")
    return {"status": "success", "message": f"Paper '{paper_id}' deleted"}


@app.get("/announcements")
async def get_announcements():
    """Get ticker announcements"""
    data = load_data_file(ANNOUNCEMENTS_FILE)
    return data


@app.get("/bulletins")
async def get_bulletins():
    """Get official bulletins"""
    data = load_data_file(BULLETINS_FILE)
    return data


@app.get("/analytics")
async def get_analytics():
    """Get system analytics metrics"""
    data = load_data_file(ANALYTICS_FILE)
    return data


@app.post("/admin/announcements")
async def update_announcements(data: Dict):
    """Update announcements (admin endpoint)"""
    if save_data_file(ANNOUNCEMENTS_FILE, data):
        return {"status": "success", "message": "Announcements updated"}
    return JSONResponse(status_code=500, content={"error": "Failed to save announcements"})


@app.post("/admin/bulletins")
async def update_bulletins(data: Dict):
    """Update bulletins (admin endpoint)"""
    if save_data_file(BULLETINS_FILE, data):
        return {"status": "success", "message": "Bulletins updated"}
    return JSONResponse(status_code=500, content={"error": "Failed to save bulletins"})


@app.post("/admin/analytics")
async def update_analytics(data: Dict):
    """Update analytics (admin endpoint)"""
    if save_data_file(ANALYTICS_FILE, data):
        return {"status": "success", "message": "Analytics updated"}
    return JSONResponse(status_code=500, content={"error": "Failed to save analytics"})

@app.post("/feedback")
async def feedback(data: Dict):
    """Create new feedback"""
    try:
        print(f"New feedback received: {data}")
        return {"status": "success", "message": "Feedback received"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


def load_quiz_file() -> DailyQuiz:
    if not DAILY_QUIZ_FILE.exists():
        raise HTTPException(status_code=404, detail="daily_quizes.json not found")

    with open(DAILY_QUIZ_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    return DailyQuiz(**raw)

@app.get("/quiz-topics", response_model=QuizTopicsResponse)
def get_quiz_topics():
    data = load_quiz_file()
    return {"topics": data.daily_quizes}

@app.get("/quiz-topics/{topic_id}", response_model=QuizTopic)
def get_quiz_topic(topic_id: str):
    data = load_quiz_file()
    for topic in data.daily_quizes:
        if topic.id == topic_id:
            return topic
    raise HTTPException(status_code=404, detail="Quiz topic not found")


# ============ MOCK TEST ENGINE ENDPOINTS ============

@app.get("/mock-tests")
async def list_all_mock_tests():
    """
    1. Yeh endpoint saare available mock tests ki index list load karega 
    taaki frontend par saare cards (CGL, Bank, Police) render ho sakein.
    """
    if not MOCK_INDEX_FILE.exists():
        raise HTTPException(
            status_code=404, 
            detail="Mock tests index master file not found on server."
        )
    
    # Hamara purana generic load_data_file use kar rahe hain
    index_data = load_data_file(MOCK_INDEX_FILE)
    return index_data


@app.get("/mock-test/{paper_id}", response_model=MockTestSchema) # <-- Yeh response_model strict validation lagata hai!
async def get_individual_mock_test(paper_id: str):
    """
    Safely loads individual question files using configurations 
    from config.py to ensure zero path collisions.
    """
    # 1. Check if the master index exists to find the file mapping
    if not MOCK_INDEX_FILE.exists():
        raise HTTPException(
            status_code=404, 
            detail="Master index configuration file (mock_tests.json) not found."
        )
        
    index_data = load_data_file(MOCK_INDEX_FILE)
    
    # In case index_data is wrapped inside a dictionary like {"tests": [...]}
    tests_list = index_data if isinstance(index_data, list) else index_data.get("tests", [])
    
    # 2. Search for the target paper configuration in your master index list
    target_paper_meta = None
    for paper in tests_list:
        if paper.get("id") == paper_id:
            target_paper_meta = paper
            break
            
    # 3. Formulate the dynamic safe file resolution path
    if target_paper_meta and target_paper_meta.get("path"):
        # Extract just the filename (e.g., 'ssc_cgl.json') from the path string
        file_name = Path(target_paper_meta["path"]).name
        actual_file_path = MOCK_PAPERS_DIR / file_name
    else:
        # Fallback direct matching pattern if meta mapping isn't found
        actual_file_path = MOCK_PAPERS_DIR / f"{paper_id}.json"

    # 4. Strict assertion check to completely avoid 500 runtime execution breaks
    if not actual_file_path.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"Mock test questions file '{actual_file_path.name}' is missing in directory workspace."
        )

    try:
        paper_questions_data = load_data_file(actual_file_path)
        if not paper_questions_data:
            raise HTTPException(status_code=404, detail="File found but contains invalid or corrupted JSON data.")
            
        return paper_questions_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error parsing paper structure layout: {str(e)}"
        )

