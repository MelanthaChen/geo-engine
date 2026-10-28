import pytest
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import Session
from app.integration.durable_outreach import metadata,job_table,record_table,submit,get_job,DurableStore

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
