"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import sqlite3

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DB_PATH = current_dir / "activities.db"

DEFAULT_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def seed_default_activities(connection):
    for name, data in DEFAULT_ACTIVITIES.items():
        connection.execute(
            """
            INSERT INTO activities(name, description, schedule, max_participants)
            VALUES (?, ?, ?, ?)
            """,
            (name, data["description"], data["schedule"], data["max_participants"])
        )

        connection.executemany(
            """
            INSERT INTO activity_participants(activity_name, email)
            VALUES (?, ?)
            """,
            [(name, email) for email in data["participants"]]
        )


def init_database():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS activities (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS activity_participants (
                activity_name TEXT NOT NULL,
                email TEXT NOT NULL,
                PRIMARY KEY (activity_name, email),
                FOREIGN KEY (activity_name) REFERENCES activities(name) ON DELETE CASCADE
            );
            """
        )

        activity_count = connection.execute(
            "SELECT COUNT(*) AS count FROM activities"
        ).fetchone()["count"]

        if activity_count == 0:
            seed_default_activities(connection)


def fetch_activities():
    with get_connection() as connection:
        activity_rows = connection.execute(
            """
            SELECT name, description, schedule, max_participants
            FROM activities
            ORDER BY name
            """
        ).fetchall()

        participant_rows = connection.execute(
            """
            SELECT activity_name, email
            FROM activity_participants
            ORDER BY email
            """
        ).fetchall()

    activities = {
        row["name"]: {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": []
        }
        for row in activity_rows
    }

    for row in participant_rows:
        activities[row["activity_name"]]["participants"].append(row["email"])

    return activities


@app.on_event("startup")
def startup_event():
    init_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return fetch_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with get_connection() as connection:
        activity = connection.execute(
            "SELECT max_participants FROM activities WHERE name = ?",
            (activity_name,)
        ).fetchone()

        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        is_already_signed_up = connection.execute(
            """
            SELECT 1
            FROM activity_participants
            WHERE activity_name = ? AND email = ?
            """,
            (activity_name, email)
        ).fetchone()

        if is_already_signed_up:
            raise HTTPException(
                status_code=400,
                detail="Student is already signed up"
            )

        signup_count = connection.execute(
            "SELECT COUNT(*) AS count FROM activity_participants WHERE activity_name = ?",
            (activity_name,)
        ).fetchone()["count"]

        if signup_count >= activity["max_participants"]:
            raise HTTPException(status_code=400, detail="Activity is full")

        connection.execute(
            "INSERT INTO activity_participants(activity_name, email) VALUES (?, ?)",
            (activity_name, email)
        )

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with get_connection() as connection:
        activity = connection.execute(
            "SELECT 1 FROM activities WHERE name = ?",
            (activity_name,)
        ).fetchone()

        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        is_signed_up = connection.execute(
            """
            SELECT 1
            FROM activity_participants
            WHERE activity_name = ? AND email = ?
            """,
            (activity_name, email)
        ).fetchone()

        if not is_signed_up:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

        connection.execute(
            "DELETE FROM activity_participants WHERE activity_name = ? AND email = ?",
            (activity_name, email)
        )

    return {"message": f"Unregistered {email} from {activity_name}"}
