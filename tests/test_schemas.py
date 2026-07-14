from __future__ import annotations

import pytest
from pydantic import ValidationError

from resume_cli.schemas import ResumeInfo, ScoreDraft, build_score_result, calculate_overall_score


def test_score_is_calculated_with_fixed_weights() -> None:
    draft = ScoreDraft(
        skill_score=88,
        experience_score=80,
        education_score=75,
        comment="Relevant strengths and gaps.",
        interview_questions=["Describe a relevant project."],
    )

    result = build_score_result(draft)

    assert calculate_overall_score(88, 80, 75) == 82
    assert result.overall_score == 82


def test_rejects_out_of_range_score() -> None:
    with pytest.raises(ValidationError):
        ScoreDraft(
            skill_score=101,
            experience_score=80,
            education_score=75,
            comment="Invalid score.",
            interview_questions=["Question?"],
        )


def test_question_count_constraints_are_exposed_in_json_schema() -> None:
    question_schema = ScoreDraft.model_json_schema()["properties"]["interview_questions"]

    assert question_schema["minItems"] == 1
    assert question_schema["maxItems"] == 5


def test_rejects_too_many_interview_questions() -> None:
    with pytest.raises(ValidationError):
        ScoreDraft(
            skill_score=80,
            experience_score=80,
            education_score=80,
            comment="Relevant strengths and gaps.",
            interview_questions=[f"Question {index}?" for index in range(6)],
        )


def test_rejects_invalid_resume_json() -> None:
    with pytest.raises(ValidationError):
        ResumeInfo.model_validate_json('{"name": "Alice"}')
