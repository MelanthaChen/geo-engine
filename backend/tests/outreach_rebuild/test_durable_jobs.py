import hashlib
import pytest
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
