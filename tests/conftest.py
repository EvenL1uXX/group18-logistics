import pytest

from app import create_app
from data.seed import seed


@pytest.fixture()
def app(tmp_path):
    db_file = tmp_path / "test-logistics.db"
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file.as_posix()}",
        }
    )
    session = app.config["DB"].session()
    seed(session)
    session.close()
    yield app
    app.config["DB"].remove()


@pytest.fixture()
def client(app):
    return app.test_client()
