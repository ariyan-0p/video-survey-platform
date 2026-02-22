from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List
import urllib.request
import json
import shutil
import os
import zipfile
import io

from database import engine, Base, get_db
import models
import schemas

# Create tables in the database
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Video Survey Platform API")

# Tell FastAPI to allow requests from our frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure the media directory exists on the server
MEDIA_DIR = "/app/media"
os.makedirs(MEDIA_DIR, exist_ok=True)

@app.get("/")
def read_root():
    return {"status": "Backend is running, Database is connected!"}

# ==========================================
# ADMIN FLOW: SURVEY MANAGEMENT APIs
# ==========================================

@app.post("/api/surveys", response_model=schemas.SurveyResponse)
def create_survey(survey: schemas.SurveyCreate, db: Session = Depends(get_db)):
    db_survey = models.Survey(title=survey.title)
    db.add(db_survey)
    db.commit()
    db.refresh(db_survey)
    return db_survey

@app.post("/api/surveys/{id}/questions", response_model=schemas.QuestionResponse)
def add_question(id: str, question: schemas.QuestionCreate, db: Session = Depends(get_db)):
    survey = db.query(models.Survey).filter(models.Survey.id == id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    existing_questions = db.query(models.SurveyQuestion).filter(models.SurveyQuestion.survey_id == id).count()
    if existing_questions >= 5:
        raise HTTPException(status_code=400, detail="A survey can only have a maximum of 5 questions")

    db_question = models.SurveyQuestion(
        survey_id=id,
        question_text=question.question_text,
        order=question.order
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question

@app.get("/api/surveys/{id}", response_model=schemas.SurveyResponse)
def get_survey(id: str, db: Session = Depends(get_db)):
    survey = db.query(models.Survey).filter(models.Survey.id == id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey

@app.post("/api/surveys/{id}/publish")
def publish_survey(id: str, db: Session = Depends(get_db)):
    survey = db.query(models.Survey).filter(models.Survey.id == id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    question_count = db.query(models.SurveyQuestion).filter(models.SurveyQuestion.survey_id == id).count()
    if question_count != 5:
        raise HTTPException(status_code=400, detail=f"Survey must have exactly 5 questions to be published. Currently has {question_count}.")
    
    survey.is_active = True
    db.commit()
    db.refresh(survey)
    return {"message": "Survey published successfully", "survey_id": survey.id, "public_url": f"/survey/{survey.id}"}

# ==========================================
# USER FLOW: SUBMISSION APIs
# ==========================================

def get_location_from_ip(ip: str):
    if ip == "127.0.0.1" or ip == "localhost":
        return "Localhost"
    try:
        with urllib.request.urlopen(f"http://ip-api.com/json/{ip}", timeout=3) as url:
            data = json.loads(url.read().decode())
            if data.get("status") == "success":
                return f"{data.get('city')}, {data.get('country')}"
    except Exception:
        pass
    return "Unknown"

def parse_user_agent(ua_string: str):
    ua_lower = ua_string.lower()
    device = "Mobile" if "mobi" in ua_lower else "Desktop"
    
    os_name = "Unknown"
    if "windows" in ua_lower: os_name = "Windows"
    elif "mac os" in ua_lower: os_name = "MacOS"
    elif "linux" in ua_lower: os_name = "Linux"
    elif "android" in ua_lower: os_name = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower: os_name = "iOS"
        
    browser = "Unknown"
    if "chrome" in ua_lower and "edg" not in ua_lower: browser = "Chrome"
    elif "firefox" in ua_lower: browser = "Firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower: browser = "Safari"
    elif "edg" in ua_lower: browser = "Edge"
        
    return device, os_name, browser

@app.post("/api/surveys/{id}/start", response_model=schemas.SubmissionResponse)
def start_submission(id: str, request: Request, db: Session = Depends(get_db)):
    survey = db.query(models.Survey).filter(models.Survey.id == id).first()
    if not survey or not survey.is_active:
        raise HTTPException(status_code=400, detail="Survey not found or not published yet")
    
    user_agent = request.headers.get('user-agent', '')
    client_ip = request.client.host if request.client else "Unknown"
    device, os_name, browser = parse_user_agent(user_agent)
    location = get_location_from_ip(client_ip)

    db_submission = models.SurveySubmission(
        survey_id=id,
        ip_address=client_ip,
        device=device,
        browser=browser,
        os=os_name,
        location=location
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission

@app.post("/api/submissions/{submission_id}/answers")
def save_answer(submission_id: str, answer: schemas.AnswerCreate, db: Session = Depends(get_db)):
    submission = db.query(models.SurveySubmission).filter(models.SurveySubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    db_answer = models.SurveyAnswer(
        submission_id=submission_id,
        question_id=answer.question_id,
        answer=answer.answer,
        face_detected=answer.face_detected,
        face_score=answer.face_score
    )
    db.add(db_answer)
    db.commit()
    return {"message": "Answer saved successfully", "answer_id": db_answer.id}

@app.post("/api/submissions/{id}/media")
def upload_media(id: str, type: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Uploads video or face image. 'type' should be 'video' or 'image'"""
    submission = db.query(models.SurveySubmission).filter(models.SurveySubmission.id == id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    safe_filename = file.filename.replace(" ", "_")
    file_path = os.path.join(MEDIA_DIR, f"{id}_{type}_{safe_filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    db_media = models.MediaFile(
        submission_id=id,
        type=type,
        path=file_path
    )
    db.add(db_media)
    db.commit()
    return {"message": f"{type} uploaded successfully", "path": file_path}

@app.post("/api/submissions/{id}/complete")
def complete_submission(id: str, db: Session = Depends(get_db)):
    submission = db.query(models.SurveySubmission).filter(models.SurveySubmission.id == id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
        
    answers = db.query(models.SurveyAnswer).filter(models.SurveyAnswer.submission_id == id).all()
    
    valid_scores = [a.face_score for a in answers if a.face_score is not None]
    overall_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
    
    submission.completed_at = func.now()
    submission.overall_score = overall_score
    db.commit()
    
    return {"message": "Survey completed", "overall_score": overall_score}

# ==========================================
# EXPORT API (Mandatory)
# ==========================================

@app.get("/api/submissions/{submission_id}/export")
def export_submission(submission_id: str, db: Session = Depends(get_db)):
    submission = db.query(models.SurveySubmission).filter(models.SurveySubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
        
    answers = db.query(models.SurveyAnswer).filter(models.SurveyAnswer.submission_id == submission_id).all()
    media_files = db.query(models.MediaFile).filter(models.MediaFile.submission_id == submission_id).all()
    
    # Construct metadata.json
    metadata = {
        "submission_id": submission.id,
        "survey_id": submission.survey_id,
        "started_at": submission.started_at.isoformat() if submission.started_at else None,
        "completed_at": submission.completed_at.isoformat() if submission.completed_at else None,
        "ip_address": submission.ip_address,
        "device": submission.device,
        "browser": submission.browser,
        "os": submission.os,
        "location": submission.location,
        "responses": [],
        "overall_score": submission.overall_score
    }
    
    for ans in answers:
        question = db.query(models.SurveyQuestion).filter(models.SurveyQuestion.id == ans.question_id).first()
        metadata["responses"].append({
            "question": question.question_text if question else "Unknown",
            "answer": ans.answer,
            "face_detected": ans.face_detected,
            "score": ans.face_score,
            "face_image": f"/images/{ans.id}.png"
        })

    # Create the ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        
        # Add metadata.json
        zip_file.writestr("metadata.json", json.dumps(metadata, indent=4))
        
        # Add media files
        for i, media in enumerate(media_files):
            if os.path.exists(media.path):
                if media.type == "video":
                    zip_file.write(media.path, "videos/full_session.mp4")
                elif media.type == "image":
                    zip_file.write(media.path, f"images/q{i}_face.png")

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer, 
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f"attachment; filename=submission_{submission_id}.zip"}
    )