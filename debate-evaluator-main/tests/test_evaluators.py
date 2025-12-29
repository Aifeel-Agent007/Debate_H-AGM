"""평가자 테스트"""

import pytest

from debate_evaluator.models.base import EvaluationMode
from debate_evaluator.models.dqi import DQICategory, DQIResult
from debate_evaluator.evaluators.dqi import DQIEvaluator
from debate_evaluator.prompts.dqi import DQIPrompt


class TestDQIEvaluator:
    """DQI 평가자 테스트"""

    def test_parse_response_extracts_debate_summary(self, sample_dqi_response):
        """토론 요약 추출 테스트"""
        evaluator = DQIEvaluator(client=None, prompt=DQIPrompt())
        result = evaluator.parse_response(sample_dqi_response)

        assert isinstance(result, DQIResult)
        assert "AI 규제" in result.debate_summary

    def test_parse_response_extracts_category_scores(self, sample_dqi_response):
        """범주별 점수 추출 테스트"""
        evaluator = DQIEvaluator(client=None, prompt=DQIPrompt())
        result = evaluator.parse_response(sample_dqi_response)

        assert len(result.category_scores) == 7

        # 참여 평등 점수 확인
        participation_score = result.get_category_score(DQICategory.PARTICIPATION)
        assert participation_score is not None
        assert participation_score.code == 1

    def test_parse_response_extracts_recommendations(self, sample_dqi_response):
        """개선점 추출 테스트"""
        evaluator = DQIEvaluator(client=None, prompt=DQIPrompt())
        result = evaluator.parse_response(sample_dqi_response)

        assert len(result.recommendations) >= 1
        assert any("통계" in rec for rec in result.recommendations)

    def test_total_score_calculation(self, sample_dqi_response):
        """총점 계산 테스트"""
        evaluator = DQIEvaluator(client=None, prompt=DQIPrompt())
        result = evaluator.parse_response(sample_dqi_response)

        expected_total = sum(cs.code for cs in result.category_scores)
        assert result.total_score == expected_total


class TestEvaluationMode:
    """평가 모드 테스트"""

    def test_from_string_valid_modes(self):
        """유효한 모드 문자열 변환 테스트"""
        assert EvaluationMode.from_string("dqi") == EvaluationMode.DQI
        assert EvaluationMode.from_string("DQI") == EvaluationMode.DQI
        assert EvaluationMode.from_string("aaf") == EvaluationMode.AAF
        assert EvaluationMode.from_string("dqi-aaf") == EvaluationMode.HYBRID
        assert EvaluationMode.from_string("afra") == EvaluationMode.AFRA

    def test_from_string_invalid_mode(self):
        """유효하지 않은 모드 문자열 변환 테스트"""
        with pytest.raises(ValueError) as exc_info:
            EvaluationMode.from_string("invalid")

        assert "유효하지 않은 평가 모드" in str(exc_info.value)


class TestPromptRegistry:
    """프롬프트 레지스트리 테스트"""

    def test_all_modes_have_prompts(self, evaluation_modes):
        """모든 모드에 프롬프트가 등록되어 있는지 테스트"""
        from debate_evaluator.prompts.base import PromptRegistry
        # 프롬프트 모듈 import하여 등록
        from debate_evaluator.prompts import dqi, aaf, hybrid, afra  # noqa: F401

        for mode in evaluation_modes:
            prompt = PromptRegistry.get(mode)
            assert prompt is not None
            assert len(prompt.system_prompt) > 100


class TestEvaluatorFactory:
    """평가자 팩토리 테스트"""

    def test_all_modes_have_evaluators(self, evaluation_modes):
        """모든 모드에 평가자가 등록되어 있는지 테스트"""
        from debate_evaluator.evaluators.base import EvaluatorFactory
        # 평가자 모듈 import하여 등록
        from debate_evaluator.evaluators import dqi, aaf, hybrid, afra  # noqa: F401

        for mode in evaluation_modes:
            assert mode in EvaluatorFactory._registry
