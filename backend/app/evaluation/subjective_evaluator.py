import math
import time
from dataclasses import dataclass
from functools import lru_cache
from urllib.request import urlopen

from openai import OpenAI

from app.core.config import settings
from app.experiment.token_usage_profiler import record_provider_usage


OFFICIAL_PROMPT_COMMIT = "c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888"
OFFICIAL_PROMPT_FILES = {
    "relevance": "relevance_detailed.txt",
    "influence": "influence_detailed.txt",
    "uniqueness": "uniqueness_detailed.txt",
    "diversity": "diversity_detailed.txt",
    "follow_up": "follow_detailed.txt",
    "subjective_position": "subjpos_detailed.txt",
    "subjective_count": "subjcount_detailed.txt",
}


@dataclass
class SubjectiveEvaluationResult:
    scores: dict[str, float]

    @property
    def average(self) -> float:
        return sum(self.scores.values()) / len(self.scores)


class SubjectiveImpressionEvaluator:
    """Port of the paper's GPT-3.5-instruct expected-logprob judge."""

    name = "princeton_geo_subjective_impression"
    version = "official-public-repo-v1"
    model = "gpt-3.5-turbo-instruct"

    def __init__(self, client=None):
        self.client = client or OpenAI(api_key=settings.OPENAI_API_KEY)

    def evaluate(
        self,
        *,
        query: str,
        answer: str,
        selected_rank: int,
    ) -> SubjectiveEvaluationResult:
        scores = {}
        for metric in OFFICIAL_PROMPT_FILES:
            prompt = self._official_prompt(metric).replace(
                "[1]", f"[{selected_rank}]"
            ).format(query=query, answer=answer)
            started = time.perf_counter()
            response = self.client.completions.create(
                model=self.model,
                prompt=prompt,
                temperature=0,
                max_tokens=3,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                logprobs=5,
                n=1,
            )
            record_provider_usage(
                purpose="subjective_evaluation",
                requested_model=self.model,
                actual_model=response.model,
                usage=response.usage,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            top_logprobs = response.choices[0].logprobs.top_logprobs[0]
            scores[metric] = self._expected_score(top_logprobs)
        return SubjectiveEvaluationResult(scores=scores)

    @staticmethod
    @lru_cache(maxsize=7)
    def _official_prompt(metric: str) -> str:
        filename = OFFICIAL_PROMPT_FILES[metric]
        url = (
            "https://raw.githubusercontent.com/GEO-optim/GEO/"
            f"{OFFICIAL_PROMPT_COMMIT}/geval_prompts/{filename}"
        )
        with urlopen(url, timeout=60) as response:
            return response.read().decode("utf-8")

    def _expected_score(self, top_logprobs: dict[str, float]) -> float:
        """Match the public repo's convert_to_number + probability weighting."""
        weighted = 0.0
        probability = sum(math.exp(logprob) for logprob in top_logprobs.values())
        if probability == 0:
            raise ValueError("Subjective evaluator returned zero probability mass.")
        for token, logprob in top_logprobs.items():
            try:
                score = min(5.0, max(1.0, float(token.strip())))
            except (TypeError, ValueError):
                score = 1.0
            weight = math.exp(logprob)
            weighted += score * weight
        return weighted / probability


def calibrate_subjective_scores(
    raw_scores: list[float],
    pawc_scores: list[float],
) -> list[float]:
    """Match subjective mean and variance to PAWC as specified by the paper."""
    if len(raw_scores) != len(pawc_scores) or not raw_scores:
        raise ValueError("Calibration requires aligned non-empty score vectors.")
    raw_mean = sum(raw_scores) / len(raw_scores)
    pawc_mean = sum(pawc_scores) / len(pawc_scores)
    raw_variance = sum((x - raw_mean) ** 2 for x in raw_scores) / len(raw_scores)
    pawc_variance = sum((x - pawc_mean) ** 2 for x in pawc_scores) / len(pawc_scores)
    if raw_variance == 0:
        return [pawc_mean for _ in raw_scores]
    scale = math.sqrt(pawc_variance / raw_variance)
    return [pawc_mean + (value - raw_mean) * scale for value in raw_scores]
