import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.evaluation.experiment_pipeline import descriptive_statistics
from app.evaluation.evaluator import (
    extract_citations_new,
    impression_pos_count_simple,
    impression_word_count_simple,
    impression_wordpos_count_simple,
)
from app.experiment.geo_bench_loader import GeoBenchLoader
from app.experiment.trend_validation import (
    estimate_stage,
    stage_decision,
    verify_paper_conclusions,
)
from app.experiment.token_usage_profiler import measured_stage_projection
from app.evaluation.subjective_evaluator import (
    SubjectiveImpressionEvaluator,
    calibrate_subjective_scores,
)
from app.evaluation.evaluator import Evaluator
from app.experiment.official_replication_runner import (
    OFFICIAL_ANSWER_COUNT,
    OFFICIAL_ANSWER_MAX_TOKENS,
    OFFICIAL_ANSWER_MODEL,
    OFFICIAL_ANSWER_TEMPERATURE,
    OfficialReplicationRunner,
)
from app.ge.prompt_builder import PromptBuilder
from app.ge.search_provider import RetrievedDocument
from app.providers.chatgpt_provider import ChatGPTProvider


class DescriptiveStatisticsTests(unittest.TestCase):
    def test_complete_descriptive_statistics(self):
        result = descriptive_statistics([1, 2, 3, 4, 5])

        self.assertEqual(result["sample_count"], 5)
        self.assertEqual(result["mean"], 3)
        self.assertEqual(result["median"], 3)
        self.assertEqual(result["variance"], 2.5)
        self.assertEqual(result["min"], 1)
        self.assertEqual(result["max"], 5)
        self.assertLess(result["confidence_low"], result["mean"])
        self.assertGreater(result["confidence_high"], result["mean"])

    def test_single_sample_has_zero_spread(self):
        result = descriptive_statistics([0.25])

        self.assertEqual(result["variance"], 0)
        self.assertEqual(result["stddev"], 0)
        self.assertEqual(result["confidence_low"], 0.25)
        self.assertEqual(result["confidence_high"], 0.25)


class PaperMethodValidationTests(unittest.TestCase):
    def test_answer_prompt_is_official_prompt_byte_for_byte(self):
        documents = [
            RetrievedDocument(
                rank=index,
                title=f"Source {index}",
                url=f"https://example.com/{index}",
                plain_text=f"text {index}",
                is_optimization_target=index == 2,
            )
            for index in range(1, 6)
        ]
        prompt = PromptBuilder().build("Q", documents, 2, "modified")
        expected_sources = "\n\n".join(
            f"### Source {index}:\n"
            f"{'modified' if index == 2 else f'text {index}'}\n\n\n"
            for index in range(1, 6)
        )
        expected = (
            "Write an accurate and concise answer for the given user question, using "
            "_only_ the provided summarized web search results. The answer should be "
            "correct, high-quality, and written by an expert using an unbiased and "
            "journalistic tone. The user's language of choice such as English, Français, "
            "Español, Deutsch, or 日本語 should be used. The answer should be informative, "
            "interesting, and engaging. The answer's logic and reasoning should be rigorous "
            "and defensible. Every sentence in the answer should be _immediately followed_ "
            "by an in-line citation to the search result(s). The cited search result(s) "
            "should fully support _all_ the information in the sentence. Search results "
            "need to be cited using [index]. When citing several search results, use "
            "[1][2][3] format rather than [1, 2, 3]. You can use multiple search results "
            "to respond comprehensively while avoiding irrelevant search results.\n\n"
            f"Question: Q\n\nSearch Results:\n{expected_sources}\n"
        )
        self.assertEqual(prompt, expected)

    def test_chat_provider_sends_one_official_n5_request(self):
        captured = {}

        class Completions:
            def create(self, **request):
                captured.update(request)
                return SimpleNamespace(
                    model=OFFICIAL_ANSWER_MODEL,
                    usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30),
                    choices=[
                        SimpleNamespace(index=index, message=SimpleNamespace(content=f"answer {index}"))
                        for index in reversed(range(OFFICIAL_ANSWER_COUNT))
                    ],
                )

        provider = ChatGPTProvider.__new__(ChatGPTProvider)
        provider.client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
        with patch("app.providers.chatgpt_provider.record_provider_usage"):
            answers = provider.generate_texts(
                system_prompt="",
                user_prompt="official prompt",
                model=OFFICIAL_ANSWER_MODEL,
                temperature=OFFICIAL_ANSWER_TEMPERATURE,
                count=OFFICIAL_ANSWER_COUNT,
                top_p=1,
                max_tokens=OFFICIAL_ANSWER_MAX_TOKENS,
                purpose="answer_generation",
            )

        self.assertEqual(captured["n"], 5)
        self.assertEqual(captured["model"], "gpt-3.5-turbo-16k")
        self.assertEqual(captured["temperature"], 0.5)
        self.assertEqual(captured["max_tokens"], 1024)
        self.assertEqual(captured["top_p"], 1)
        self.assertNotIn("seed", captured)
        self.assertNotIn("stop", captured)
        self.assertNotIn("presence_penalty", captured)
        self.assertNotIn("frequency_penalty", captured)
        self.assertEqual(answers, [f"answer {index}\n" for index in range(5)])

    def test_one_query_batch_preserves_metrics_and_persists_before_evaluation(self):
        answers = [
            "Alpha evidence [1]. Beta evidence [2][1].",
            "Beta evidence [2]. Alpha evidence [1].",
            "Gamma evidence [3]. Alpha evidence [1].",
            "Alpha evidence [1][4]. Delta evidence [4].",
            "No selected citation [2][3].",
        ]
        documents = [
            RetrievedDocument(index, f"S{index}", f"https://e/{index}", f"text {index}", index == 1)
            for index in range(1, 6)
        ]
        evaluator = Evaluator()
        legacy_metrics = [evaluator.evaluate(answer, "text 1", "S1", "https://e/1", 1) for answer in answers]
        batched_metrics = [evaluator.evaluate(answer, "text 1", "S1", "https://e/1", 1) for answer in list(answers)]
        self.assertEqual(legacy_metrics, batched_metrics)

        events = []
        experiment = SimpleNamespace(
            id=7,
            llm_model=OFFICIAL_ANSWER_MODEL,
            temperature=OFFICIAL_ANSWER_TEMPERATURE,
            benchmark_queries_json='[{"query":"Q","documents":['
                + ",".join(
                    '{"rank":%d,"title":"S%d","url":"https://e/%d","content":"text %d","is_optimization_target":%s}'
                    % (i, i, i, i, "true" if i == 1 else "false")
                    for i in range(1, 6)
                )
                + "]}]",
            strategies_json='["original"]',
            runs=[],
        )
        query_row = SimpleNamespace(id=11)

        class Repository:
            def get_run(self, _): return experiment
            def mark_running(self, _): pass
            def ensure_experiment_query(self, *args, **kwargs): return query_row
            def strategy_sample_group(self, **kwargs): return experiment.runs
            def store_generated_batch(self, *args, **kwargs):
                events.append("persist")
                for index, answer in enumerate(kwargs["answers"]):
                    result = SimpleNamespace(
                        modified_document_text=kwargs["modified_document_text"],
                        prompt=kwargs["prompt"], answer=answer,
                    )
                    experiment.runs.append(SimpleNamespace(
                        id=index + 1, sample_index=index, status="generated",
                        strategy_result=result, latency_ms=1, metrics=[],
                    ))
                return list(experiment.runs)
            def complete_generated_sample(self, run, *, output):
                events.append(f"complete-{run.sample_index}")
                run.status = "completed"
            def update_progress(self, *args, **kwargs): pass
            def store_calibrated_subjective_metrics(self, *args, **kwargs): pass
            def mark_completed(self, _): pass

        class LLM:
            def generate_many(self, **kwargs):
                events.append("generate")
                self.request = kwargs
                return list(answers)

        class Pipeline:
            def evaluate_outputs(self, outputs, **kwargs):
                self.assert_persisted()
                events.append(f"evaluate-{outputs[0]['sample_index']}")
                outputs[0]["evaluation"] = SimpleNamespace(
                    word_count=0, position=None, pawc=0,
                    citation_count=0, visibility_score=0,
                )
                outputs[0]["evaluation_record"] = {
                    "evaluator": "test", "evaluator_version": "1",
                    "details": {}, "metrics": {},
                }
            def assert_persisted(self):
                if "persist" not in events:
                    raise AssertionError("evaluation started before durable batch persistence")

        runner = OfficialReplicationRunner.__new__(OfficialReplicationRunner)
        runner.repository = Repository()
        runner.llm = LLM()
        runner.rewriter = SimpleNamespace(rewrite=lambda **kwargs: kwargs["document_text"])
        runner.prompt_builder = PromptBuilder()
        runner.pipeline = Pipeline()
        runner.execute(7)

        self.assertEqual(events[:2], ["generate", "persist"])
        self.assertEqual(len([event for event in events if event.startswith("evaluate-")]), 5)
        self.assertTrue(all(run.status == "completed" for run in experiment.runs))

    def test_official_impression_metrics(self):
        sentences = extract_citations_new(
            "First supported sentence [1]. Second evidence [2][1]."
        )

        for metric in (
            impression_wordpos_count_simple,
            impression_word_count_simple,
            impression_pos_count_simple,
        ):
            scores = metric(sentences, n=5, normalize=True)
            self.assertAlmostEqual(sum(scores), 1.0)
            self.assertEqual(len(scores), 5)

    def test_geo_bench_uses_published_suggested_source(self):
        fixture = Path(__file__).parents[1] / "experiment_dataset/geo_bench/test.jsonl"
        entry = GeoBenchLoader(cache_path=fixture).load_test_entries(1)[0]
        targets = [
            document["rank"]
            for document in entry["documents"]
            if document["is_optimization_target"]
        ]

        self.assertEqual(targets, [entry["metadata"]["sugg_idx"] + 1])

    def test_subjective_expected_logprob_score(self):
        evaluator = SubjectiveImpressionEvaluator.__new__(SubjectiveImpressionEvaluator)
        score = evaluator._expected_score({" 1": -2.0, " 3": -0.1, " 5": -1.0})
        self.assertGreater(score, 2)
        self.assertLess(score, 4)

    def test_subjective_nonnumeric_logprob_matches_official_minimum(self):
        evaluator = SubjectiveImpressionEvaluator.__new__(SubjectiveImpressionEvaluator)
        score = evaluator._expected_score({"unknown": 0.0, " 5": 0.0})
        self.assertEqual(score, 3.0)

    def test_subjective_calibration_matches_pawc_moments(self):
        calibrated = calibrate_subjective_scores([1, 2, 3], [0.1, 0.2, 0.3])
        self.assertAlmostEqual(sum(calibrated) / 3, 0.2)


class TrendValidationTests(unittest.TestCase):
    def test_paper_ordering_claims_are_machine_verified(self):
        values = {
            "original": 0.193, "keyword_stuffing": 0.177,
            "unique_words": 0.205, "easy_to_understand": 0.220,
            "authoritative": 0.213, "technical_terms": 0.227,
            "fluency": 0.247, "citation": 0.246,
            "statistics": 0.252, "quotation": 0.272,
        }
        rows = [
            {"strategy": strategy, "metric": metric, "mean": value}
            for metric in ("pawc", "subjective_impression_calibrated")
            for strategy, value in values.items()
        ]
        result = verify_paper_conclusions(rows)
        self.assertEqual(result["trend_similarity"], 1.0)
        self.assertEqual(stage_decision("stage1", 1.0, True)["decision"], "PROCEED")

    def test_stage_plan_is_cost_aware(self):
        stage1 = estimate_stage("stage1", subjective=True)
        full = estimate_stage("full", subjective=True)
        measured_stage1 = measured_stage_projection("stage1", subjective=True)
        self.assertEqual(stage1["queries"], 30)
        self.assertEqual(
            stage1["estimated_cost_usd"],
            round(measured_stage1["cost_usd"], 2),
        )
        self.assertEqual(
            stage1["estimation_basis"],
            "Measured 3-query real-pipeline token profile",
        )
        self.assertGreater(full["total_calls"], stage1["total_calls"])
        self.assertGreater(full["estimated_cost_usd"], stage1["estimated_cost_usd"])


if __name__ == "__main__":
    unittest.main()
