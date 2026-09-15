from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app.utils.decorators import admin_required
from app.models.ai_insight import AIInsight
from app.services.ai_service import generate_insights

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")


@ai_bp.route("/insights")
@login_required
@admin_required
def insights():
    all_insights = AIInsight.query.order_by(AIInsight.created_at.desc()).limit(50).all()
    return render_template("admin/ai_insights.html", insights=all_insights)


@ai_bp.route("/insights/refresh", methods=["POST"])
@login_required
@admin_required
def refresh_insights():
    new_insights = generate_insights(persist=True)
    flash(f"Generated {len(new_insights)} new insight(s).", "success")
    return redirect(url_for("ai.insights"))
