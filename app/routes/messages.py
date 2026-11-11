from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.message import StaffMessage, MessageRecipient
from app.utils.notify import notify_users, notify_roles, log_action

messages_bp = Blueprint("messages", __name__, url_prefix="/messages")

MAX_SUBJECT, MAX_BODY = 150, 2000


def _staff():
    return User.query.filter(User.role.in_(["seller", "worker"]), User.is_active_account.is_(True)).order_by(User.full_name).all()


@messages_bp.route("/")
@login_required
def inbox():
    tab = request.args.get("tab", "inbox")
    received = (MessageRecipient.query.filter_by(user_id=current_user.id)
                .join(StaffMessage).order_by(StaffMessage.created_at.desc()).limit(100).all())
    sent = []
    if current_user.can_view_admin:
        q = StaffMessage.query
        if current_user.is_admin:
            q = q.filter_by(sender_id=current_user.id)
        sent = q.order_by(StaffMessage.created_at.desc()).limit(100).all()
        if current_user.is_owner:
            tab = "sent"                  # the owner only watches what managers sent
    return render_template("messages/inbox.html", received=received, sent=sent, tab=tab)


@messages_bp.route("/new", methods=["GET", "POST"])
@login_required
def compose():
    if not current_user.is_admin:         # managers only; the owner is read-only
        abort(403)
    staff = _staff()
    form = {}
    if request.method == "POST":
        form = request.form
        audience = request.form.get("audience", "all")
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()
        errors = []
        if not subject:
            errors.append("Please write a subject.")
        elif len(subject) > MAX_SUBJECT:
            errors.append(f"The subject can be at most {MAX_SUBJECT} characters.")
        if not body:
            errors.append("Please write your message.")
        elif len(body) > MAX_BODY:
            errors.append(f"The message can be at most {MAX_BODY} characters.")

        if audience == "sellers":
            targets, label = [u for u in staff if u.role == "seller"], "All sellers"
        elif audience == "workers":
            targets, label = [u for u in staff if u.role == "worker"], "All workers"
        elif audience == "selected":
            wanted = {int(x) for x in request.form.getlist("recipients") if x.isdigit()}
            targets = [u for u in staff if u.id in wanted]
            label = targets[0].full_name if len(targets) == 1 else f"{len(targets)} selected staff"
        else:
            targets, label = staff, "All staff"
        if not targets:
            errors.append("There is nobody to send this to. Choose at least one active staff member.")

        if errors:
            for e in errors:
                flash(e, "error")
        else:
            msg = StaffMessage(sender_id=current_user.id, subject=subject, body=body, audience=label)
            db.session.add(msg)
            db.session.flush()
            for u in targets:
                db.session.add(MessageRecipient(message_id=msg.id, user_id=u.id))
            db.session.commit()
            link = url_for("messages.view", message_id=msg.id)
            preview = body if len(body) <= 220 else body[:217] + "..."
            notify_users([u.id for u in targets], f"{subject}", f"{current_user.full_name}: {preview}",
                         link=link, category="message")
            notify_roles(("owner",), "Manager sent a message", f"{current_user.full_name} to {label}: {subject}",
                         link=link, category="message")
            log_action("sent", "message", msg.id, f"To {label} ({len(targets)}): {subject}")
            flash(f"Message sent to {len(targets)} {'person' if len(targets) == 1 else 'people'}.", "success")
            return redirect(url_for("messages.view", message_id=msg.id))
    return render_template("messages/compose.html", staff=staff, form=form, selected=request.form.getlist("recipients"), max_body=MAX_BODY, max_subject=MAX_SUBJECT)


@messages_bp.route("/<int:message_id>")
@login_required
def view(message_id):
    msg = StaffMessage.query.get_or_404(message_id)
    mine = MessageRecipient.query.filter_by(message_id=msg.id, user_id=current_user.id).first()
    if not (mine or current_user.can_view_admin):
        abort(403)
    if mine and mine.read_at is None:
        mine.read_at = datetime.utcnow()
        db.session.commit()
    return render_template("messages/view.html", msg=msg, show_recipients=current_user.can_view_admin)
