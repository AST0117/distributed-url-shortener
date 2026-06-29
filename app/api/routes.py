from flask import Blueprint, request, jsonify, redirect
from app import db
from app.models.url import URL
from app.services.encoder import encode
from app.services.cache import get_cached_url, set_cached_url, invalidate_cache
from functools import wraps
from app.services.rate_limiter import is_allowed

bp = Blueprint("api", __name__)

def rate_limited(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        client_id = request.headers.get("X-API-Key", request.remote_addr)
        if not is_allowed(client_id):
            return jsonify({"error": "rate limit exceeded"}), 429
        return f(*args, **kwargs)
    return wrapper

@bp.route("/shorten", methods=["POST"])
@rate_limited
def shorten():
    data = request.get_json()
    long_url = data.get("url")
    if not long_url:
        return jsonify({"error": "url is required"}), 400

    new_entry = URL(long_url=long_url, short_code="")
    db.session.add(new_entry)
    db.session.flush()

    new_entry.short_code = encode(new_entry.id)
    db.session.commit()

    set_cached_url(new_entry.short_code, long_url)

    return jsonify({"short_code": new_entry.short_code,
                     "short_url": f"/{new_entry.short_code}"}), 201

@bp.route("/<short_code>", methods=["GET"])
def resolve(short_code):
    cached = get_cached_url(short_code)
    if cached:
        _increment_click_async(short_code)
        return redirect(cached, code=302)

    entry = URL.query.filter_by(short_code=short_code).first()
    if not entry:
        return jsonify({"error": "not found"}), 404

    set_cached_url(short_code, entry.long_url)
    entry.click_count += 1
    db.session.commit()
    return redirect(entry.long_url, code=302)

@bp.route("/stats/<short_code>", methods=["GET"])
def stats(short_code):
    entry = URL.query.filter_by(short_code=short_code).first()
    if not entry:
        return jsonify({"error": "not found"}), 404
    return jsonify(entry.to_dict())

def _increment_click_async(short_code):
    entry = URL.query.filter_by(short_code=short_code).first()
    if entry:
        entry.click_count += 1
        db.session.commit()