"""Explicit transfer of data from Legacy Workspace into a registered company.

Run inside api container after verifying a backup:
python -m scripts.transfer_legacy --company kings-palace
python -m scripts.transfer_legacy --company kings-palace --apply

The target must have NO employees or kiosks. Never auto-guess company ownership.
"""
from __future__ import annotations
import argparse
from sqlalchemy import select,func
from backend.database import SessionLocal
from backend.models import Company,Employee,Device,AttendanceEvent,SecurityEvent,AuditLog,utc_naive


def transfer(slug,apply):
    with SessionLocal() as db:
        legacy=db.scalar(select(Company).where(Company.slug=='legacy-workspace'))
        target=db.scalar(select(Company).where(Company.slug==slug))
        if not legacy or not target:raise RuntimeError('Legacy workspace or destination company was not found')
        if legacy.id==target.id:raise RuntimeError('Choose a different company')
        counts={}
        for cls in (Employee,Device,AttendanceEvent,SecurityEvent):
            counts[cls.__tablename__]=db.scalar(select(func.count()).select_from(cls).where(cls.company_id==legacy.id)) or 0
        print('Source:',legacy.name,'→ Target:',target.name)
        print('Rows to transfer:',counts)
        for cls in (Employee,Device):
            if db.scalar(select(cls.id).where(cls.company_id==target.id).limit(1)):
                raise RuntimeError('Destination already contains employees/kiosks. Merge manually after reviewing duplicates.')
        if not apply:
            print('DRY RUN ONLY. Re-run with --apply after taking a verified backup.')
            return
        # Same row IDs remain; therefore face-template AES-GCM AAD remains valid.
        for cls in (Employee,Device,AttendanceEvent,SecurityEvent):
            db.query(cls).filter(cls.company_id==legacy.id).update({cls.company_id:target.id},synchronize_session=False)
        db.add(AuditLog(actor='migration',action='legacy.transfer',company_id=target.id,
                        detail=f'Legacy data transferred from company {legacy.id}'))
        db.commit()
        print('Transfer completed. Reconcile employee and attendance totals in both portals.')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--company',required=True,help='Target company slug')
    parser.add_argument('--apply',action='store_true',help='Actually transfer (default dry run)')
    args=parser.parse_args()
    transfer(args.company,args.apply)
