from database import Base, engine
from clinical_models import ClinicalPatient, ClinicalCase, ClinicalVisit, MriOutcome, BiopsyOutcome, ProgressionOutcome, ModelPrediction

def migrate_clinical_longitudinal():
    Base.metadata.create_all(bind=engine, tables=[
        ClinicalPatient.__table__, ClinicalCase.__table__, ClinicalVisit.__table__,
        MriOutcome.__table__, BiopsyOutcome.__table__, ProgressionOutcome.__table__, ModelPrediction.__table__
    ])
    print("ZENPSA DB: longitudinal clinical tables verified", flush=True)
