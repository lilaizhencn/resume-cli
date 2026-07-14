"""Validated public and provider-facing data contracts."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class StrictModel(BaseModel):
    """Forbid provider fields that are not part of the public contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Education(StrictModel):
    school: str | None
    major: str | None
    degree: str | None
    graduation_time: str | None

    @field_validator("school", "major", "degree", "graduation_time", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ResumeInfo(StrictModel):
    name: str | None
    phone: str | None
    email: str | None
    city: str | None
    education: list[Education]
    skills: list[str]

    @field_validator("name", "phone", "email", "city", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is not None and not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("email is not a valid email address")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digit_count = sum(character.isdigit() for character in value)
        if not 6 <= digit_count <= 20:
            raise ValueError("phone must contain between 6 and 20 digits")
        return value

    @field_validator("skills")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for value in values:
            skill = value.strip()
            if not skill:
                continue
            if skill not in seen:
                unique.append(skill)
                seen.add(skill)
        return unique


class ScoreDraft(StrictModel):
    """AI-provided component scores; overall score is never model-generated."""

    skill_score: int = Field(ge=0, le=100)
    experience_score: int = Field(ge=0, le=100)
    education_score: int = Field(ge=0, le=100)
    comment: str
    interview_questions: list[str] = Field(min_length=1, max_length=5)

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("comment must not be empty")
        return value

    @field_validator("interview_questions")
    @classmethod
    def validate_questions(cls, values: list[str]) -> list[str]:
        questions: list[str] = []
        seen: set[str] = set()
        for value in values:
            question = value.strip()
            if question and question not in seen:
                questions.append(question)
                seen.add(question)
        if not questions:
            raise ValueError("at least one interview question is required")
        if len(questions) > 5:
            raise ValueError("at most five interview questions are allowed")
        return questions


class ScoreResult(StrictModel):
    overall_score: int = Field(ge=0, le=100)
    skill_score: int = Field(ge=0, le=100)
    experience_score: int = Field(ge=0, le=100)
    education_score: int = Field(ge=0, le=100)
    comment: str
    interview_questions: list[str]

    @model_validator(mode="after")
    def overall_matches_components(self) -> ScoreResult:
        expected = calculate_overall_score(
            self.skill_score,
            self.experience_score,
            self.education_score,
        )
        if self.overall_score != expected:
            raise ValueError("overall_score does not match the documented component weights")
        return self


def calculate_overall_score(skill: int, experience: int, education: int) -> int:
    """Calculate a 40/40/20 weighted score with integer half-up rounding."""

    weighted_hundredths = skill * 40 + experience * 40 + education * 20
    return (weighted_hundredths + 50) // 100


def build_score_result(draft: ScoreDraft) -> ScoreResult:
    return ScoreResult(
        overall_score=calculate_overall_score(
            draft.skill_score,
            draft.experience_score,
            draft.education_score,
        ),
        **draft.model_dump(),
    )
