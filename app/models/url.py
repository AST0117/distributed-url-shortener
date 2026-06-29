from app import db
from datetime import datetime

class URL(db.Model):
    __tablename__ = "urls"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    short_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    long_url = db.Column(db.String(2048), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    click_count = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "short_code": self.short_code,
            "long_url": self.long_url,
            "created_at": self.created_at.isoformat(),
            "click_count": self.click_count
        }