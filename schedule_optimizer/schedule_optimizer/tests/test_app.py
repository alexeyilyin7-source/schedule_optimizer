from pathlib import Path

from fastapi.testclient import TestClient

from app import app

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEDULE_FILE = BASE_DIR / "Ведомость_осенний_семестр_фейк_1x.xlsx"
AUDITORIUM_FILE = BASE_DIR / "Список_аудиторий_фейк_1x.xlsx"

client = TestClient(app)


def test_root_page_opens():
    response = client.get("/")
    assert response.status_code == 200
    assert "АСР ГУУ" in response.text


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_optimize_with_demo_files():
    with SCHEDULE_FILE.open("rb") as schedule_fp, AUDITORIUM_FILE.open("rb") as auditorium_fp:
        response = client.post(
            "/optimize",
            files={
                "schedule_file": ("schedule.xlsx", schedule_fp, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "auditorium_file": ("auditoriums.xlsx", auditorium_fp, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "algorithm": (None, "combined"),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert "error" not in payload
    assert payload["schedule"]
    assert payload["fitness_score"] >= 0
    assert payload["algorithm_used"] in {"genetic", "annealing", "greedy", "combined"}
