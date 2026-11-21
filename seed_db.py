"""Create tables and load demo data.

Run once before starting the app:

    python seed_db.py
    python app.py
"""

from app import create_app
from data.seed import seed

app = create_app()
session = app.config["DB"].session()
seed(session)
session.close()
app.config["DB"].remove()
print("Seeded demo data: 3 users (admin/driver/customer), 5 inventory items.")
