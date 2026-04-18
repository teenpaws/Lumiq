# bridge/routes/cron.py
from flask import Blueprint, jsonify

bp = Blueprint("cron", __name__)

@bp.post("/cron/run-now")
def cron_run_now():
    return jsonify({"error": "Self-improvement cron not implemented in MVP"}), 501
