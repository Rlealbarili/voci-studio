from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    credits = Column(Numeric, default=100.0) # Cost/Credit balance (e.g. used seconds)
    
    projects = relationship("Project", back_populates="owner")
    histories = relationship("InferenceHistory", back_populates="user")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="projects")
    histories = relationship("InferenceHistory", back_populates="project")

class InferenceHistory(Base):
    __tablename__ = "inference_history"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, index=True, nullable=False, unique=True)
    task_type = Column(String, nullable=False) # e.g. "convert", "mix"
    status = Column(String, default="PENDING")
    
    # Execution Tracking
    output_url = Column(String, nullable=True)
    error_text = Column(String, nullable=True)
    gpu_id = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    # GPU cost tracking
    duration_seconds = Column(Numeric, default=0.0)
    cost_deducted = Column(Numeric, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    
    user = relationship("User", back_populates="histories")
    project = relationship("Project", back_populates="histories")
