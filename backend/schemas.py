from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Questions ---
class QuestionBase(BaseModel):
    question_text: str
    order: int

class QuestionCreate(QuestionBase):
    pass

class QuestionResponse(QuestionBase):
    id: str

    class Config:
        from_attributes = True

# --- Surveys ---
class SurveyBase(BaseModel):
    title: str

class SurveyCreate(SurveyBase):
    pass

class SurveyResponse(SurveyBase):
    id: str
    is_active: bool
    created_at: datetime
    questions: List[QuestionResponse] = []

    class Config:
        from_attributes = True

# --- Submissions & Answers ---
class AnswerCreate(BaseModel):
    question_id: str
    answer: str
    face_detected: bool
    face_score: Optional[float] = None

class SubmissionResponse(BaseModel):
    id: str
    survey_id: str
    started_at: datetime
    
    class Config:
        from_attributes = True