"""Durable service-to-service jobs composing the existing GEO research pipeline."""
from __future__ import annotations
import hashlib,json,os
from datetime import datetime,timezone,timedelta
from urllib.parse import urlparse
from sqlalchemy import MetaData,Table,Column,String,Text,Integer,select,text

metadata=MetaData()
job_table=Table('outreach_research_jobs',metadata,
    Column('id',String,primary_key=True),Column('request_hash',String,nullable=False),Column('profile',Text,nullable=False),
    Column('status',String,nullable=False),Column('property_id',Integer),Column('audit_id',Integer),Column('opportunity_id',Integer),
    Column('experiment_id',Integer),Column('result',Text),Column('error',Text),Column('created_at',String),Column('updated_at',String))
record_table=Table('outreach_research_records',metadata,Column('id',String,primary_key=True),Column('kind',String,index=True),
    Column('profile_id',String,index=True),Column('profile_version',String),Column('payload',Text,nullable=False))

def encoded(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def now():return datetime.now(timezone.utc).isoformat()

def insert_once(db,table,values):
    if db.bind.dialect.name=='postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    db.execute(insert(table).values(**values).on_conflict_do_nothing(index_elements=['id']))
    db.commit()

class DurableStore:
    def __init__(self,db):self.db=db
    def append(self,kind,record):
        insert_once(self.db,record_table,dict(id=record['record_id'],kind=kind,profile_id=record.get('source_profile_id'),profile_version=record.get('source_profile_version'),payload=encoded(record)))
    def records(self,kind):
        return [json.loads(r[0]) for r in self.db.execute(select(record_table.c.payload).where(record_table.c.kind==kind))]
    def find_profile(self,ident,version):
        raw=self.db.scalar(select(record_table.c.payload).where(record_table.c.kind=='profile_import',record_table.c.profile_id==ident,record_table.c.profile_version==version))
        return json.loads(raw) if raw else None

def public(row):
    return {'job_id':row['id'],'status':row['status'],'property_id':row['property_id'],'audit_id':row['audit_id'],
            'opportunity_ids':[row['opportunity_id']] if row['opportunity_id'] else [],'experiment_id':row['experiment_id'],
            'result':json.loads(row['result']) if row['result'] else None,'error':row['error'],'created_at':row['created_at'],'updated_at':row['updated_at']}

def get_job(db,key):
    row=db.execute(select(job_table).where(job_table.c.id==key)).mappings().first()
    return public(row) if row else None

def submit(db,key,profile):
    from app.integration.contracts import normalize_profile_import
    if not key.startswith('outreach-v2:inv-') or len(key)>180:raise ValueError('Invalid idempotency key')
    normalized=normalize_profile_import(profile)
    consent=profile.get('consent') or {};url=(profile.get('identity') or {}).get('website','')
    parsed=urlparse(url)
    if parsed.scheme!='https' or not parsed.hostname:raise ValueError('An authorized HTTPS website is required')
    if profile.get('controlled_fixture') is not False:raise ValueError('Synthetic execution is not accepted')
    if consent.get('research_interest')!='YES' or consent.get('research_authorization')!='YES' or consent.get('scope_website')!=url:
        raise ValueError('Independent interest, authorization and exact website scope are required')
    payload=encoded(profile);digest=hashlib.sha256(payload.encode()).hexdigest()
    insert_once(db,job_table,dict(id=key,request_hash=digest,profile=payload,status='QUEUED',created_at=now(),updated_at=now()))
    row=db.execute(select(job_table).where(job_table.c.id==key)).mappings().one()
    if row['request_hash']!=digest:raise ValueError('Idempotency key was already bound to a different profile or scope')
    return public(row)

def update(db,key,**values):
    db.execute(job_table.update().where(job_table.c.id==key).values(updated_at=now(),**values));db.commit()

def advance(db,key):
    """Synchronous bounded attempt. The external scheduler resumes after cold starts.

    PostgreSQL session advisory lock survives the pipeline's internal commits,
    preventing overlapping HTTP requests from duplicating properties/experiments.
    """
    from app.integration.adapter import GeoResearchIntegrationAdapter
    from app.integration.research_pipeline import run_owner_research_pipeline,ResearchPipelineBlocked
    from app.models.website_audit import WebsiteAudit
    from app.models.property import Property
    from app.services.website_audit.audit_service import run_website_audit
    if db.bind.dialect.name!='postgresql':raise RuntimeError('Live research requires PostgreSQL advisory locks')
    lock=int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'big',signed=True)
    with db.bind.connect() as guard:
        if not guard.scalar(text('SELECT pg_try_advisory_lock(:key)'),{'key':lock}):return get_job(db,key)
        try:
            row=db.execute(select(job_table).where(job_table.c.id==key)).mappings().first()
            if not row:raise LookupError('Research job not found')
            if row['status']=='COMPLETED':return public(row)
            if os.environ.get('GEO_OUTREACH_RESEARCH_ENABLED')!='true':
                update(db,key,status='BLOCKED_CONFIGURATION',error='Unattended read-only GEO research is not enabled');return get_job(db,key)
            profile=json.loads(row['profile']);store=DurableStore(db)
            update(db,key,status='RUNNING',error=None)
            # Property creation and durable profile mapping are serialized by website
            # identity as well, so concurrent invitations cannot create two properties.
            site_lock=int.from_bytes(hashlib.sha256(profile['identity']['website'].encode()).digest()[:8],'big',signed=True)
            guard.execute(text('SELECT pg_advisory_lock(:key)'),{'key':site_lock})
            try:
                imported=GeoResearchIntegrationAdapter(db,'.unused',store=store).import_profile(profile)
            finally:guard.execute(text('SELECT pg_advisory_unlock(:key)'),{'key':site_lock})
            property_id=imported['property_id'];update(db,key,property_id=property_id)
            # Reuse only a completed, recent audit for the SAME property and scope.
            audit=db.query(WebsiteAudit).filter(WebsiteAudit.property_id==property_id,WebsiteAudit.status=='completed').order_by(WebsiteAudit.id.desc()).first()
            cutoff=datetime.now(timezone.utc)-timedelta(days=30)
            audit_time=(audit.completed_at or audit.created_at) if audit else None
            if audit_time and audit_time.tzinfo is None:audit_time=audit_time.replace(tzinfo=timezone.utc)
            if not audit or not audit_time or audit_time<cutoff or urlparse(audit.base_url).hostname!=urlparse(profile['identity']['website']).hostname:
                prop=db.get(Property,property_id)
                audit=run_website_audit(db,prop,browser_fallback_enabled=False)
            if audit.status!='completed':raise RuntimeError('Website audit did not complete')
            opportunities=sorted([r for r in audit.recommendations if r.observed_evidence],key=lambda r:r.id)
            if not opportunities:raise ResearchPipelineBlocked('No evidence-backed optimization opportunity is available')
            opportunity=opportunities[0];update(db,key,audit_id=audit.id,opportunity_id=opportunity.id)
            outcome=run_owner_research_pipeline(db,profile={**profile,'property_id':property_id},store_root='.unused',
                audit_id=audit.id,opportunity_id=opportunity.id,durable_store=store,resume_incomplete=True)
            if outcome.get('status')=='COMPLETED':
                result=outcome['result'];baseline=result.get('baseline') or {}
                if not baseline.get('results') or int(baseline.get('model_calls') or 0)<2 or str(baseline.get('provider','')).lower() in {'','mock','controlled_fixture'}:
                    raise RuntimeError('Research output lacks real model execution evidence')
                update(db,key,status='COMPLETED',result=encoded(result),experiment_id=outcome.get('experiment_id'),error=None)
            else:update(db,key,status='RUNNING',experiment_id=outcome.get('experiment_id'))
        except ResearchPipelineBlocked as exc:
            db.rollback();update(db,key,status='BLOCKED_CONFIGURATION',error=str(exc)[:400])
        except Exception as exc:
            db.rollback();update(db,key,status='RETRY_PENDING',error=type(exc).__name__+' during GEO research; existing job preserved')
        finally:
            guard.execute(text('SELECT pg_advisory_unlock(:key)'),{'key':lock});guard.commit()
    return get_job(db,key)
