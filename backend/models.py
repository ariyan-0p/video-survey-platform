from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Survey(Base):
    __tablename__ = "surveys"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    questions = relationship("SurveyQuestion", back_populates="survey")
    submissions = relationship("SurveySubmission", back_populates="survey")

class SurveyQuestion(Base):
    __tablename__ = "survey_questions"

    id = Column(String, primary_key=True, default=generate_uuid)
    survey_id = Column(String, ForeignKey("surveys.id"), nullable=False)
    question_text = Column(String, nullable=False)
    order = Column(Integer, nullable=False) # 1 to 5

    survey = relationship("Survey", back_populates="questions")

class SurveySubmission(Base):
    __tablename__ = "survey_submissions"

    id = Column(String, primary_key=True, default=generate_uuid)
    survey_id = Column(String, ForeignKey("surveys.id"), nullable=False)
    ip_address = Column(String)
    device = Column(String)
    browser = Column(String)
    os = Column(String)
    location = Column(String)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    overall_score = Column(Float, nullable=True)

    survey = relationship("Survey", back_populates="submissions")
    answers = relationship("SurveyAnswer", back_populates="submission")
    media_files = relationship("MediaFile", back_populates="submission")

class SurveyAnswer(Base):
    __tablename__ = "survey_answers"

    id = Column(String, primary_key=True, default=generate_uuid)
    submission_id = Column(String, ForeignKey("survey_submissions.id"), nullable=False)
    question_id = Column(String, ForeignKey("survey_questions.id"), nullable=False)
    answer = Column(String) # "Yes" or "No"
    face_detected = Column(Boolean, default=False)
    face_score = Column(Float, nullable=True)
    face_image_path = Column(String, nullable=True)

    submission = relationship("SurveySubmission", back_populates="answers")

class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(String, primary_key=True, default=generate_uuid)
    submission_id = Column(String, ForeignKey("survey_submissions.id"), nullable=False)
    type = Column(String, nullable=False) # "video" or "image"
    path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    submission = relationship("SurveySubmission", back_populates="media_files")