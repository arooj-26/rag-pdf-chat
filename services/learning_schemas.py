"""Validated study content, with evidence quotes tied to retrieved source numbers."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_number: int = Field(ge=1)
    quote: str = Field(min_length=8, max_length=600)


class QuizQuestion(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=5, max_length=1500)
    evidence: Evidence

    @model_validator(mode="after")
    def unique_options(self):
        if len(set(s.strip().lower() for s in self.options)) != 4 or any(not s.strip() for s in self.options):
            raise ValueError("Questions must have four distinct nonempty options")
        return self


class Quiz(BaseModel):
    title: str
    questions: list[QuizQuestion] = Field(min_length=1, max_length=20)


class Flashcard(BaseModel):
    front: str = Field(min_length=1, max_length=1000)
    back: str = Field(min_length=1, max_length=2000)
    evidence: Evidence


class Flashcards(BaseModel):
    title: str
    cards: list[Flashcard] = Field(min_length=1, max_length=20)


class Note(BaseModel):
    concept: str
    definition: str
    explanation: str
    takeaway: str
    evidence: Evidence


class StudyNotes(BaseModel):
    title: str
    notes: list[Note] = Field(min_length=1, max_length=20)


class LearningRequest(BaseModel):
    document_ids: list[str] = Field(min_length=1, max_length=10)
    topic: str = Field(default="main concepts and definitions", min_length=1, max_length=1000)
    count: int = Field(default=5, ge=1, le=20)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    style: Literal["question-answer", "term-definition", "concept-revision"] = "question-answer"


class QuizSubmission(BaseModel):
    answers: list[int] = Field(min_length=1, max_length=20)
