import hashlib
import pytest
from types import SimpleNamespace
from decimal import Decimal
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import Session
from app.integration.durable_outreach import metadata,job_table,record_table,submit,get_job,DurableStore,encoded,authorized_single_job,AUTHORIZED_TEST_JOB_ID,AUTHORIZED_TEST_WEBSITE
from app.experiment.token_usage_profiler import OutreachProviderBudget

@pytest.fixture
def db():
    engine=create_engine('sqlite://');metadata.create_all(engine)
    with Session(engine) as db:yield db

def profile():
    return {'profile_id':'fresh-owner','profile_version':'inv-clean','profile_type':'owner_controlled_test',
        'identity':{'name':'GeoAIResume','website':'https://geo-ai-resume.vercel.app'},'controlled_fixture':False,
        'consent':{'status':'VERIFIED','consent_id':'submission-clean','version':'v2','research_scope':'Read-only website research',
                   'research_interest':'YES','research_authorization':'YES','scope_website':'https://geo-ai-resume.vercel.app'}}

def test_same_key_is_idempotent_and_conflicting_scope_is_rejected(db):
    p=profile();one=submit(db,'outreach-v2:inv-clean',p);two=submit(db,'outreach-v2:inv-clean',p)
    assert one==two and one['status']=='QUEUED' and one['result'] is None
    assert db.scalar(select(func.count()).select_from(job_table))==1
    p['identity']['name']='Another business'
    with pytest.raises(ValueError,match='different profile'):submit(db,'outreach-v2:inv-clean',p)


def test_corrected_geoairesume_canonical_payload_resumes_existing_job_without_conflicting_scope(db):
    p={
        'consent':{'consent_id':'submission-00a5fcfc9643aef10155e359d8e58ed7b3b364e0742cd2799782615db4c867b2','invitation_reference':'GEO-A67A912BDB53E20447BD1E323C935738',
            'research_authorization':'YES','research_interest':'YES',
            'research_scope':'Read-only public website analysis and model-based research; no website modifications or monitoring',
            'scope_website':'https://geo-ai-resume.vercel.app','status':'VERIFIED',
            'submission_id':'submission-00a5fcfc9643aef10155e359d8e58ed7b3b364e0742cd2799782615db4c867b2','version':'outreach-consent-v2'},
        'controlled_fixture':False,
        'identity':{'name':'GeoAIResume controlled test website','website':'https://geo-ai-resume.vercel.app'},
        'profile_id':'geoairesume-owner-test-v1','profile_type':'owner_controlled_test',
        'profile_version':'inv-45e793f424654bb4a1b744cd25e95855',
    }
    key='outreach-v2:inv-45e793f424654bb4a1b744cd25e95855'
    digest=hashlib.sha256(encoded(p).encode()).hexdigest()
    db.execute(job_table.insert().values(id=key,request_hash=digest,profile=encoded(p),status='QUEUED',
        property_id=None,audit_id=None,opportunity_id=None,experiment_id=None,result=None,error=None,
        created_at='original-created-at',updated_at='original-updated-at'))

    resumed=submit(db,key,p)
    assert resumed['status']=='QUEUED'
    assert resumed['created_at']=='original-created-at'
    assert db.scalar(select(func.count()).select_from(job_table))==1

    conflicting={**p,'consent':{**p['consent'],'invitation_reference':'placeholder'}}
    with pytest.raises(ValueError,match='different profile'):
        submit(db,key,conflicting)

@pytest.mark.parametrize('field,value',[('research_interest','NO'),('research_authorization','NO'),('scope_website','https://wrong.example')])
def test_consent_and_scope_are_independent(db,field,value):
    p=profile();p['consent'][field]=value
    with pytest.raises(ValueError):submit(db,'outreach-v2:inv-clean',p)
    assert db.scalar(select(func.count()).select_from(job_table))==0

def test_durable_results_do_not_depend_on_files_or_old_profile_versions(db):
    store=DurableStore(db)
    row={'record_id':'fresh-result','source_profile_id':'fresh-owner','source_profile_version':'inv-clean','baseline':{'provider':'CONTROLLED_FIXTURE'}}
    store.append('research_result_export',row);store.append('research_result_export',row)
    assert len(DurableStore(db).records('research_result_export'))==1
    assert store.find_profile('fresh-owner','old-invitation') is None
    assert get_job(db,'unknown') is None

def test_capability_status_does_not_claim_a_paid_research_run(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'test')
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    monkeypatch.setenv('OPENAI_API_KEY', 'configured-but-not-tested')
    from app.api.v1.integration_routes import outreach_capabilities
    from app.core.config import settings
    monkeypatch.setenv('GEO_ENGINE_HANDOFF_TOKEN', 'test-service-token')
    monkeypatch.delenv('GEO_OUTREACH_RESEARCH_ENABLED', raising=False)
    monkeypatch.setattr(settings, 'OPENAI_API_KEY', 'configured-but-not-tested')
    monkeypatch.setattr(settings, 'SEARCH_PROVIDER', 'exa')
    monkeypatch.setattr(settings, 'EXA_API_KEY', 'configured-but-not-tested')
    status = outreach_capabilities('Bearer test-service-token')
    assert status['durable_jobs'] is True
    assert status['model_credentials_configured'] is True
    assert status['search_credentials_configured'] is True
    assert status['provider_connectivity_verified'] is False
    assert status['research_execution_enabled'] is False
    assert status['research_ready'] is False


def test_outreach_budget_reserves_then_persists_actual_cost_and_is_idempotently_closed(db):
    store=DurableStore(db)
    with OutreachProviderBudget(store,'outreach-v2:inv-clean') as budget:
        budget.reserve_search('exa')
        budget.settle_search('exa',5)
        sequence=budget.reserve_model('gpt-6-luna',[{'role':'user','content':'x'*200}],512)
        budget.settle_model(sequence,'gpt-6-luna',type('Usage',(),{'prompt_tokens':50,'completion_tokens':200})())
        assert budget.committed_and_reserved_cost < .25
    again=OutreachProviderBudget(store,'outreach-v2:inv-clean')
    assert again.search_reserved is True
    assert again.search_settled is True
    assert len(again.reservations)==1
    with pytest.raises(RuntimeError,match='only search request'):
        again.reserve_search('exa')
    with pytest.raises(RuntimeError,match='model path'):
        again.reserve_model('retired-model',[{'role':'user','content':'x'}],512)


def test_outreach_budget_fails_closed_on_oversized_inputs_and_outputs(db):
    budget=OutreachProviderBudget(DurableStore(db),'outreach-v2:inv-clean')
    with pytest.raises(RuntimeError,match='input exceeds'):
        budget.reserve_model('gpt-6-luna',[{'role':'user','content':'x'*(budget.MAX_INPUT_BYTES_PER_CALL+1)}],512)
    with pytest.raises(RuntimeError,match='output token cap'):
        budget.reserve_model('gpt-6-luna',[{'role':'user','content':'short'}],budget.MAX_OUTPUT_TOKENS_PER_CALL+1)


def test_budget_tracks_cost_and_preserves_provider_call_limits(db):
    budget=OutreachProviderBudget(DurableStore(db),'outreach-v2:inv-clean')
    budget.reserve_search('exa')
    with pytest.raises(RuntimeError,match='only search request'):
        budget.reserve_search('exa')
    budget.settle_search('exa',5)
    for _ in range(budget.MAX_MODEL_CALLS):
        sequence=budget.reserve_model('gpt-6-luna',[{'role':'user','content':'x'}],1024)
        budget.settle_model(sequence,'gpt-6-luna',type('Usage',(),{'prompt_tokens':1,'completion_tokens':1})())
    with pytest.raises(RuntimeError,match='five model-call allowance'):
        budget.reserve_model('gpt-6-luna',[{'role':'user','content':'x'}],1024)
    records=DurableStore(db).records('outreach_provider_budget')
    assert len([r for r in records if r['event']=='reserve_model'])==5
    assert len([r for r in records if r['event']=='reserve_search'])==1
    assert budget.committed_and_reserved_cost > 0


def test_unresolved_search_reservation_blocks_model_provider_call(db):
    store=DurableStore(db)
    budget=OutreachProviderBudget(store,'outreach-v2:inv-uncertain-search')
    budget.reserve_search('exa')
    with pytest.raises(RuntimeError,match='search request has an unresolved billable outcome'):
        budget.reserve_model('gpt-6-luna',[{'role':'user','content':'prompt'}],512)
    assert len(store.records('outreach_provider_budget'))==1


def test_paid_model_response_is_durable_before_parser_status_and_keeps_attempt_identity(db):
    store=DurableStore(db)
    budget=OutreachProviderBudget(store,'outreach-v2:inv-clean')
    sequence=budget.reserve_model('gpt-6-luna',[{'role':'user','content':'test prompt'}],512)
    response=SimpleNamespace(
        id='resp-test-123', model='gpt-6-luna',
        usage=SimpleNamespace(prompt_tokens=10,completion_tokens=4,total_tokens=14),
        choices=[SimpleNamespace(index=0,message=SimpleNamespace(content='{malformed}'))],
    )
    budget.persist_model_response(sequence,response,'gpt-6-luna',[{'role':'user','content':'test prompt'}],'strategy_rewrite')
    archived=store.records('outreach_model_response')[0]
    assert archived['raw_outputs']==['{malformed}']
    assert archived['provider_request_id']=='resp-test-123'
    assert archived['job_key']=='outreach-v2:inv-clean'
    assert archived['attempt_id']==budget.attempt_id
    assert archived['parser_status']=='pending'
    budget.record_response_validation('invalid_json')
    budget.record_response_validation('accepted',result={'document':'transformed document'})
    validation=store.records('outreach_model_response_validation')[0]
    assert validation['attempt_id']==budget.attempt_id
    assert validation['parser_status']=='invalid_json'
    accepted=next(r for r in store.records('outreach_model_response_validation') if r['parser_status']=='accepted')
    assert accepted['transformed_result']=='{"document": "transformed document"}'
    assert len(accepted['transformed_result_sha256'])==64


def test_exact_prior_provider_response_can_be_replayed_without_reserving_another_call(db):
    store=DurableStore(db)
    first=OutreachProviderBudget(store,'outreach-v2:inv-clean')
    first.experiment_id=6
    messages=[{'role':'user','content':'exact frozen prompt'}]
    params={'temperature':0,'top_p':1,'max_output_tokens':512,'response_format':{'type':'json_object'}}
    sequence=first.reserve_model('gpt-6-luna',messages,512)
    response=SimpleNamespace(id='resp-recoverable',model='gpt-6-luna',
        usage=SimpleNamespace(prompt_tokens=10,completion_tokens=4,total_tokens=14),
        choices=[SimpleNamespace(index=0,message=SimpleNamespace(content='{"recovered":true}'))])
    first.persist_model_response(sequence,response,'gpt-6-luna',messages,'strategy_rewrite',params)
    first.settle_model(sequence,'gpt-6-luna',response.usage)

    retry=OutreachProviderBudget(store,'outreach-v2:inv-clean')
    retry.experiment_id=6
    assert retry.replay_model_response('gpt-6-luna',messages,'strategy_rewrite',parameters=params)==['{"recovered":true}']
    assert retry.replay_model_response('gpt-6-luna',messages,'strategy_rewrite',parameters=params) is None
    assert len([r for r in store.records('outreach_provider_budget') if r['event']=='reserve_model'])==1


def _frozen_experiment_fixture():
    import json
    from types import SimpleNamespace
    website='https://geo-ai-resume.vercel.app/'
    retrieved_at='2026-11-05T19:19:39.132333+00:00'
    urls=[
        website,
        'https://aicareer.cloud/',
        'https://buildairesume.com/',
        'https://enhancv.com/blog/best-ai-resume-builders-reviewed/',
        'https://huntr.co/blog/best-resume-builders',
    ]
    contents=['audited target content', 'reference one', 'reference two', 'reference three', 'reference four']
    docs=[]
    for rank,(url,content) in enumerate(zip(urls,contents),start=1):
        docs.append({
            'rank':rank,
            'source_role':'audited_target' if rank==1 else 'reference',
            'retrieval_provider':'injected_for_controlled_experiment' if rank==1 else 'exa',
            'url':url,'content':content,'content_sha256':hashlib.sha256(content.encode()).hexdigest(),
            'source_audit_id':7,'retrieved_at':retrieved_at,
        })
    retrieval_urls=urls[1:]+['https://www.handpickedai.com/best-ai-resume-builder/']
    retrieval_results=[{'rank':i,'url':url,'provider_metadata':{'request_id':'exa-request-6'}}
        for i,url in enumerate(retrieval_urls,start=1)]
    evidence={'audit_id':7,'recommendation_id':3,'target_page_id':126,'target_page_url':website,
        'target_retrieval_status':'injected_for_controlled_experiment','target_retrieval_rank':None,
        'source_order':[d['url'] for d in docs],'source_snapshot_hashes':[d['content_sha256'] for d in docs],
        'retrieval_results':retrieval_results}
    for item in docs: item['supporting_evidence']=evidence
    query='What should someone know about Build Better Resumes Faster from GeoAIResume Cloud Acceptance Fixture?'
    experiment=SimpleNamespace(status='failed',run_count=0,property_id=2,llm_model='gpt-6-luna',
        dataset_name='outreach_owner_website_research',benchmark_queries_json=json.dumps([{
            'query':query, 'documents':docs}]), strategies_json='["original","faq"]',id=6)
    audit=SimpleNamespace(id=7,property_id=2,property=SimpleNamespace(name='GeoAIResume Cloud Acceptance Fixture'),
        base_url=website,pages=[SimpleNamespace(id=126,url=website,content_sha256=docs[0]['content_sha256'])])
    return experiment,audit,docs,evidence


def _recover_fixture(experiment,audit):
    from app.integration.research_pipeline import _recover_frozen_experiment_documents
    return _recover_frozen_experiment_documents(experiment,audit=audit,
        website='https://geo-ai-resume.vercel.app/',official_name='GeoAIResume — researcher-controlled E2E test',
        property_id=2,opportunity_id=3,strategy='faq')


def _write_frozen_docs(experiment,docs):
    import json
    payload=json.loads(experiment.benchmark_queries_json)
    payload[0]['documents']=docs
    experiment.benchmark_queries_json=json.dumps(payload)


def test_actual_experiment_shape_recovers_audited_property_query_identity():
    experiment,audit,docs,evidence=_frozen_experiment_fixture()
    recovered=_recover_fixture(experiment,audit)
    assert recovered and recovered['metadata']['status']=='recovered_persisted'
    assert recovered['metadata']['source_experiment_id']==6
    assert len(recovered['documents'])==5
    assert 'GeoAIResume Cloud Acceptance Fixture' in recovered['query']


def test_filtered_exa_references_are_ordered_subsequence_not_first_four():
    experiment,audit,docs,evidence=_frozen_experiment_fixture()
    evidence['retrieval_results']=[
        {'rank':1,'url':'https://geo-ai-resume.vercel.app/about','provider_metadata':{'request_id':'exa-request-6'}},
        {'rank':2,'url':'https://aicareer.cloud/','provider_metadata':{'request_id':'exa-request-6'}},
        {'rank':3,'url':'https://aicareer.cloud','provider_metadata':{'request_id':'exa-request-6'}},
        {'rank':4,'url':'https://buildairesume.com/','provider_metadata':{'request_id':'exa-request-6'}},
        {'rank':5,'url':'https://enhancv.com/blog/best-ai-resume-builders-reviewed/','provider_metadata':{'request_id':'exa-request-6'}},
        {'rank':6,'url':'https://huntr.co/blog/best-resume-builders','provider_metadata':{'request_id':'exa-request-6'}},
    ]
    recovered=_recover_fixture(experiment,audit)
    assert recovered and [d['url'] for d in recovered['documents'][1:]]==[d['url'] for d in docs[1:]]


def test_legitimate_exa_retrieved_target_variant_is_supported():
    experiment,audit,docs,evidence=_frozen_experiment_fixture()
    docs[0]['retrieval_provider']='exa'
    evidence['target_retrieval_status']='retrieved_by_provider'
    evidence['target_retrieval_rank']=7
    evidence['retrieval_results'].append({'rank':7,'url':'https://geo-ai-resume.vercel.app/',
        'provider_metadata':{'request_id':'exa-request-6'}})
    recovered=_recover_fixture(experiment,audit)
    assert recovered and recovered['metadata']['status']=='recovered_persisted'


def test_tampered_frozen_evidence_is_rejected_with_specific_reason():
    from app.integration.research_pipeline import ResearchPipelineBlocked
    experiment,audit,docs,evidence=_frozen_experiment_fixture()
    docs[1]['content']='tampered reference content'
    _write_frozen_docs(experiment,docs)
    with pytest.raises(ResearchPipelineBlocked,match='content hash does not match'):
        _recover_fixture(experiment,audit)


def test_exa_reference_identity_must_match_retrieval_ledger():
    from app.integration.research_pipeline import ResearchPipelineBlocked
    experiment,audit,docs,evidence=_frozen_experiment_fixture()
    docs[1]['url']='https://forged.example/'
    evidence['source_order']=[d['url'] for d in docs]
    _write_frozen_docs(experiment,docs)
    with pytest.raises(ResearchPipelineBlocked,match='selected Exa references'):
        _recover_fixture(experiment,audit)


def test_settled_exa_search_is_never_repeated_by_budget_guard(db):
    class SearchSpy:
        provider_id='exa'
        def __init__(self): self.calls=0
        def search(self,**kwargs):
            self.calls+=1
            raise AssertionError('a second Exa request was attempted')
    store=DurableStore(db)
    budget=OutreachProviderBudget(store,'outreach-v2:inv-frozen-recovery')
    budget.reserve_search('exa');budget.settle_search('exa',5)
    search=SearchSpy()
    with pytest.raises(RuntimeError,match='already reserved its only search request'):
        from app.integration.research_pipeline import _BudgetedSearchProvider
        _BudgetedSearchProvider(search,budget).search(query='frozen',top_k=5)
    assert search.calls==0
    assert budget.search_reserved is True and budget.search_settled is True


def test_recovery_does_not_mutate_failed_experiment_or_provider_ledger(db):
    experiment,audit,docs,evidence=_frozen_experiment_fixture()
    before=(experiment.id,experiment.status,experiment.run_count,experiment.benchmark_queries_json)
    store=DurableStore(db)
    budget=OutreachProviderBudget(store,'outreach-v2:inv-frozen-recovery-counts')
    budget.reserve_search('exa');budget.settle_search('exa',5)
    sequence=budget.reserve_model('gpt-6-luna',[{'role':'user','content':'prior prompt'}],512)
    budget.settle_model(sequence,'gpt-6-luna',type('Usage',(),{'prompt_tokens':10,'completion_tokens':2})())
    prior_events=len(store.records('outreach_provider_budget'))
    assert _recover_fixture(experiment,audit)
    assert (experiment.id,experiment.status,experiment.run_count,experiment.benchmark_queries_json)==before
    assert len(store.records('outreach_provider_budget'))==prior_events
    assert budget.search_reserved and budget.search_settled
    assert len([r for r in store.records('outreach_provider_budget') if r['event']=='reserve_model'])==1


def test_budget_cap_blocks_reservation_using_settled_and_reserved_cost(db, monkeypatch):
    store=DurableStore(db)
    budget=OutreachProviderBudget(store,'outreach-v2:inv-cap')
    monkeypatch.setattr(OutreachProviderBudget,'MAX_CUMULATIVE_COST_USD',Decimal('0.010'))
    budget.reserve_search('exa')
    budget.settle_search('exa',5)
    with pytest.raises(RuntimeError,match='budget would be exceeded'):
        budget.reserve_model('gpt-6-luna',[{'role':'user','content':'short'}],512)
    records=store.records('outreach_provider_budget')
    assert [record['event'] for record in records]==['reserve_search','settle_search']
    assert budget.committed_and_reserved_cost==pytest.approx(0.007)


def test_model_settlement_accounts_for_cached_input_and_cache_writes(db):
    store=DurableStore(db)
    budget=OutreachProviderBudget(store,'outreach-v2:inv-cache')
    sequence=budget.reserve_model('gpt-6-luna',[{'role':'user','content':'prompt'}],512)
    details=type('PromptDetails',(),{'cached_tokens':200,'cache_write_tokens':300})()
    usage=type('Usage',(),{'prompt_tokens':1000,'completion_tokens':100,'prompt_tokens_details':details})()
    budget.settle_model(sequence,'gpt-6-luna',usage)
    entry=store.records('outreach_provider_budget')[-1]
    assert entry['cached_input_tokens']==200
    assert entry['cache_write_tokens']==300
    assert entry['cache_write_usage_reported'] is True
    assert entry['actual_cost_usd']==pytest.approx(0.0001395)
    assert budget.committed_and_reserved_cost==pytest.approx(0.0001395)


def test_unknown_cache_write_breakdown_is_reserved_conservatively(db):
    store=DurableStore(db)
    budget=OutreachProviderBudget(store,'outreach-v2:inv-cache-unknown')
    sequence=budget.reserve_model('gpt-6-luna',[{'role':'user','content':'prompt'}],512)
    usage=type('Usage',(),{'prompt_tokens':1000,'completion_tokens':100})()
    budget.settle_model(sequence,'gpt-6-luna',usage)
    entry=store.records('outreach_provider_budget')[-1]
    assert entry['cache_write_tokens']==1000
    assert entry['cache_write_usage_reported'] is False
    assert entry['actual_cost_usd']==pytest.approx(0.000175)


def test_unresolved_model_reservation_blocks_any_retry(db):
    store=DurableStore(db)
    initial=OutreachProviderBudget(store,'outreach-v2:inv-uncertain')
    initial.reserve_model('gpt-6-luna',[{'role':'user','content':'prompt'}],512)
    resumed=OutreachProviderBudget(store,'outreach-v2:inv-uncertain')
    with pytest.raises(RuntimeError,match='unresolved billable outcome'):
        resumed.reserve_model('gpt-6-luna',[{'role':'user','content':'prompt'}],512)
    assert len(store.records('outreach_provider_budget'))==1


def test_cumulative_budget_counts_existing_legacy_settlements_conservatively(db,monkeypatch):
    store=DurableStore(db)
    key='outreach-v2:inv-legacy-budget'
    store.append('outreach_provider_budget',{
        'record_id':f'outreach-budget:{key}:model:1:reserve','event':'reserve_model',
        'job_key':key,'sequence':1,'model':'gpt-6-luna','input_token_limit':48000,
        'output_token_limit':1024,'worst_case_cost_usd':0.006512,
    })
    store.append('outreach_provider_budget',{
        'record_id':f'outreach-budget:{key}:model:1:settle','event':'settle_model',
        'job_key':key,'sequence':1,'model':'gpt-6-luna','prompt_tokens':40000,
        'completion_tokens':100,'actual_cost_usd':0.00405,
    })
    budget=OutreachProviderBudget(store,key)
    # Old entries have no cache breakdown; count non-cached input at write rate.
    assert budget.committed_and_reserved_cost==pytest.approx(0.00505)
    monkeypatch.setattr(OutreachProviderBudget,'MAX_CUMULATIVE_COST_USD',Decimal('0.005'))
    with pytest.raises(RuntimeError,match='budget would be exceeded'):
        budget.reserve_model('gpt-6-luna',[{'role':'user','content':'prompt'}],128)


def test_single_job_guard_requires_exact_key_verified_yes_yes_and_exact_website():
    profile={
        'profile_type':'owner_controlled_test','controlled_fixture':False,
        'identity':{'website':AUTHORIZED_TEST_WEBSITE},
        'consent':{'status':'VERIFIED','research_interest':'YES','research_authorization':'YES',
                   'scope_website':AUTHORIZED_TEST_WEBSITE,'submission_id':'existing-consent',
                   'invitation_reference':'existing-invitation'},
    }
    assert authorized_single_job(AUTHORIZED_TEST_JOB_ID,profile,True,AUTHORIZED_TEST_JOB_ID)
    assert not authorized_single_job('outreach-v2:inv-other',profile,True,AUTHORIZED_TEST_JOB_ID)
    assert not authorized_single_job(AUTHORIZED_TEST_JOB_ID,profile,False,AUTHORIZED_TEST_JOB_ID)
    assert not authorized_single_job(AUTHORIZED_TEST_JOB_ID,{**profile,'identity':{'website':'https://other.example/'}},True,AUTHORIZED_TEST_JOB_ID)
    bad_consent={**profile,'consent':{**profile['consent'],'research_authorization':'NO'}}
    assert not authorized_single_job(AUTHORIZED_TEST_JOB_ID,bad_consent,True,AUTHORIZED_TEST_JOB_ID)
