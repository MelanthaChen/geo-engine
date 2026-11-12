import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace

from app.api.v1.integration_routes import _enrich_result_sources


class Query:
    def __init__(self, rows): self.rows=rows
    def filter(self, *args): return self
    def order_by(self, *args): return self
    def first(self): return self.rows[0] if self.rows else None
    def all(self): return self.rows


class DB:
    def __init__(self, rows): self.rows=rows
    def query(self, model): return Query(self.rows.get(model, []))


def test_result_enrichment_exposes_hash_verified_sources_and_citation_use():
    text="GeoAIResume is a research site."; digest=hashlib.sha256(text.encode()).hexdigest()
    query=SimpleNamespace(id=3)
    doc=SimpleNamespace(rank=1,title="Target page",url="https://geo-ai-resume.vercel.app/",plain_text=text,
        content_sha256=digest,source_role="audited_target",retrieval_provider="exa",
        retrieval_timestamp=datetime(2026,11,1,tzinfo=timezone.utc))
    result={"record_id":"r","experiment_summary":{"experiment_id":8},
        "baseline":{"results":[{"strategy":"original","response":"Finding [1]."}]},
        "recommendations":[{"proposed_revision":"x"*1000,"original_quote":"q"*1000}]}
    enriched=_enrich_result_sources(result,DB({__import__('app.models.experiment',fromlist=['ExperimentQuery']).ExperimentQuery:[query],
        __import__('app.models.experiment',fromlist=['ExperimentDocument']).ExperimentDocument:[doc]}))
    source=enriched["research_sources"][0]
    assert source["content_sha256"]==digest and source["source_type"]=="target website"
    assert source["relevance"].startswith("Cited in persisted strategy response(s): original")
    assert enriched["recommendations"][0]["proposed_revision"] is None
    assert enriched["recommendations"][0]["original_quote"] is None
    assert enriched["recommendations"][0]["supporting_evidence_ids"]==["experiment:8:document:1"]


def test_result_enrichment_rejects_tampered_source_text():
    from fastapi import HTTPException
    query=SimpleNamespace(id=3)
    doc=SimpleNamespace(rank=1,title="Target",url="https://example.test",plain_text="tampered",content_sha256="0"*64,
        source_role="audited_target",retrieval_provider="exa",retrieval_timestamp=None)
    import app.models.experiment as models
    result={"record_id":"r","experiment_summary":{"experiment_id":8},"baseline":{"results":[]}}
    try:
        _enrich_result_sources(result,DB({models.ExperimentQuery:[query],models.ExperimentDocument:[doc]}))
        assert False,"tampered content must not be exported"
    except HTTPException as error:
        assert error.status_code==409 and "integrity mismatch" in error.detail
