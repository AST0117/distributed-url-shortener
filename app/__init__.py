from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

load_dotenv()
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    user = os.getenv("MYSQL_USER")
    pw = os.getenv("MYSQL_PASSWORD")
    host = os.getenv("MYSQL_HOST")
    dbname = os.getenv("MYSQL_DB")

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{user}:{pw}@{host}/{dbname}?ssl_disabled=True"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    from app.api.routes import bp as api_bp
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()

    return app