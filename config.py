import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = "change-this-to-something-random"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'database', 'school.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
