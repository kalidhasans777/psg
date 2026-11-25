import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app


def test_health_and_seeded_demo_patient_history():
    with TestClient(app) as client:
        h = client.get("/api/health")
        assert h.status_code == 200
        assert h.json()["application"] == "MEDORA"

        # Login as Demo Patient (MED-2026-00125)
        res = client.post("/api/auth/login", json={"identifier": "patient@medora.health", "password": "Patient@1234"})
        assert res.status_code == 200
        token = res.json()["access_token"]
        assert res.json()["user"]["permanent_patient_id"] == "MED-2026-00125"

        # Check multi-year visits (2026, 2027, 2029) are preserved
        hist = client.get("/api/patients/MED-2026-00125/history", headers={"Authorization": f"Bearer {token}"})
        assert hist.status_code == 200
        data = hist.json()
        assert data["total_visits"] >= 3
        years = {v["visit_year"] for v in data["visits"]}
        assert {2026, 2027, 2029}.issubset(years)


def test_patient_a_cannot_access_patient_b_records():
    with TestClient(app) as client:
        # Log in as Patient A (MED-2026-00126)
        login_a = client.post("/api/auth/login", json={"identifier": "patienta@medora.health", "password": "PatientA@123"})
        assert login_a.status_code == 200
        token_a = login_a.json()["access_token"]

        # Attempt to read Patient B (MED-2026-00127) profile & history
        r1 = client.get("/api/patients/MED-2026-00127", headers={"Authorization": f"Bearer {token_a}"})
        assert r1.status_code == 403

        r2 = client.get("/api/patients/MED-2026-00127/history", headers={"Authorization": f"Bearer {token_a}"})
        assert r2.status_code == 403

        # Patient cannot search other patients
        r3 = client.get("/api/patients/search?q=MED-2026", headers={"Authorization": f"Bearer {token_a}"})
        assert r3.status_code == 403


def test_permanent_patient_id_registration_and_uniqueness():
    suffix = secrets.token_hex(3)
    phone = f"99{int(suffix, 16) % 100000000:08d}"
    with TestClient(app) as client:
        reg = client.post(
            "/api/auth/register",
            json={
                "full_name": "Test Citizen",
                "date_of_birth": "1992-04-11",
                "gender": "Female",
                "phone": phone,
                "email": f"testcitizen_{suffix}@medora.health",
                "address": "12 Gandhi Nagar, Chennai",
                "password": "StrongPassword123",
                "consent_accepted": True,
            },
        )
        assert reg.status_code == 201
        pid = reg.json()["patient_card"]["permanent_patient_id"]
        assert pid.startswith("MED-2026-")

        # Duplicate phone + DOB registration must be rejected
        dup = client.post(
            "/api/auth/register",
            json={
                "full_name": "Test Citizen",
                "date_of_birth": "1992-04-11",
                "gender": "Female",
                "phone": phone,
                "email": f"testcitizen2_{suffix}@medora.health",
                "address": "12 Gandhi Nagar, Chennai",
                "password": "StrongPassword123",
                "consent_accepted": True,
            },
        )
        assert dup.status_code == 409


def test_concurrent_registrations_generate_distinct_ids():
    with TestClient(app) as client:
        def register_one(idx: int):
            s = secrets.token_hex(3)
            return client.post(
                "/api/auth/register",
                json={
                    "full_name": f"Concurrent User {idx}",
                    "date_of_birth": "1990-01-15",
                    "gender": "Male",
                    "phone": f"98{int(s, 16) % 100000000:08d}",
                    "email": f"conc_{idx}_{s}@medora.health",
                    "address": "Chennai, TN",
                    "password": "Password123!",
                    "consent_accepted": True,
                },
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(register_one, range(4)))
        assert all(r.status_code == 201 for r in responses)
        pids = [r.json()["patient_card"]["permanent_patient_id"] for r in responses]
        assert len(set(pids)) == 4


def test_tamil_voice_ai_report_upload_and_doctor_review():
    with TestClient(app) as client:
        # Patient logs in and confirms Tamil voice transcript
        p_login = client.post("/api/auth/login", json={"identifier": "patient@medora.health", "password": "Patient@1234"})
        p_token = p_login.json()["access_token"]

        voice_confirm = client.post(
            "/api/voice/confirm-transcript",
            headers={"Authorization": f"Bearer {p_token}"},
            json={
                "language": "ta-IN",
                "raw_transcript": "எனக்கு மூன்று நாட்களாக காய்ச்சல் இருக்கு. தலைவலியும் உடம்பு வலியும் இருக்கு.",
                "confirmed_transcript": "எனக்கு மூன்று நாட்களாக காய்ச்சல் இருக்கு. தலைவலியும் உடம்பு வலியும் இருக்கு.",
                "duration": "3 days",
                "severity": "moderate",
                "current_medications": "No medication reported",
                "audio_consent": True,
                "generate_ai_summary": True,
            },
        )
        assert voice_confirm.status_code == 200
        v_id = voice_confirm.json()["visit_id"]
        summary_id = voice_confirm.json()["ai_summary"]["id"]
        assert "Fever" in voice_confirm.json()["ai_summary"]["ai_generated_json"]["chief_complaints"]

        # Upload sample CBC PDF
        sample_pdf = Path(__file__).resolve().parent.parent / "sample_reports" / "sample_cbc_demo_patient.pdf"
        with open(sample_pdf, "rb") as f:
            up = client.post(
                f"/api/visits/{v_id}/reports",
                headers={"Authorization": f"Bearer {p_token}"},
                files={"file": ("sample_cbc.pdf", f, "application/pdf")},
                data={"category": "CBC", "process_sync": "true"},
            )
        assert up.status_code == 201
        findings = up.json()["findings"]
        assert any(item["test_name"] == "Hemoglobin" and item["status_relative_to_range"] == "below" for item in findings)

        # Doctor logs in, searches patient, generates overview, and approves summary
        d_login = client.post("/api/auth/login", json={"identifier": "doctor@medora.health", "password": "Doctor@1234"})
        d_token = d_login.json()["access_token"]

        ov = client.post(
            "/api/ai/patient-overview",
            headers={"Authorization": f"Bearer {d_token}"},
            json={"patient_identifier": "MED-2026-00125", "current_visit_id": v_id},
        )
        assert ov.status_code == 200
        assert ov.json()["disclaimer"] == "AI-Generated Summary – Pending Doctor Verification"

        rev = client.put(
            f"/api/ai/summaries/{summary_id}/review",
            headers={"Authorization": f"Bearer {d_token}"},
            json={"decision": "approved", "review_notes": "Verified with patient in clinic"},
        )
        assert rev.status_code == 200
        assert rev.json()["verification_status"] == "approved"

        # Admin cannot access confidential patient clinical history directly
        a_login = client.post("/api/auth/login", json={"identifier": "admin@medora.health", "password": "Admin@1234"})
        a_token = a_login.json()["access_token"]
        a_hist = client.get("/api/patients/MED-2026-00125/history", headers={"Authorization": f"Bearer {a_token}"})
        assert a_hist.status_code == 403
