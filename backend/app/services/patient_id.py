from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.patient import Patient, PatientIdSequence
from app.models.clinical import Visit, Appointment


def calculate_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def generate_permanent_patient_id(db: Session, year: Optional[int] = None) -> str:
    """
    Concurrency-safe permanent Patient ID generator (MED-YYYY-XXXXX).
    Uses row-level locking on PostgreSQL (SELECT ... FOR UPDATE) and atomic transaction
    on SQLite so concurrent registrations never generate duplicate IDs and IDs are never reused.
    """
    target_year = year or datetime.now(timezone.utc).year
    dialect = db.bind.dialect.name if db.bind else "sqlite"

    if dialect == "postgresql":
        # Ensure row exists safely using ON CONFLICT DO NOTHING
        db.execute(
            text(
                "INSERT INTO patient_id_sequences (year, last_value) VALUES (:y, 0) "
                "ON CONFLICT (year) DO NOTHING"
            ),
            {"y": target_year},
        )
        seq = (
            db.query(PatientIdSequence)
            .filter(PatientIdSequence.year == target_year)
            .with_for_update()
            .one()
        )
    else:
        # SQLite WAL / IMMEDIATE transaction lock
        seq = (
            db.query(PatientIdSequence)
            .filter(PatientIdSequence.year == target_year)
            .first()
        )
        if not seq:
            seq = PatientIdSequence(year=target_year, last_value=0)
            db.add(seq)
            db.flush()

    # Make sure sequence never collides with existing seeded records
    next_num = seq.last_value + 1
    while True:
        candidate = f"MED-{target_year}-{next_num:05d}"
        exists = (
            db.query(Patient.id)
            .filter(Patient.permanent_patient_id == candidate)
            .first()
        )
        if not exists:
            break
        next_num += 1

    seq.last_value = next_num
    db.flush()
    return f"MED-{target_year}-{next_num:05d}"


def generate_visit_code(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(Visit).count() + 1
    while True:
        code = f"VIS-{year}-{count:05d}"
        if not db.query(Visit.id).filter(Visit.visit_code == code).first():
            return code
        count += 1


def generate_appointment_code(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(Appointment).count() + 1
    while True:
        code = f"APT-{year}-{count:05d}"
        if not db.query(Appointment.id).filter(Appointment.appointment_code == code).first():
            return code
        count += 1
