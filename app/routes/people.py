from flask import Blueprint, Response, abort
from flask_login import login_required, current_user
from app.models.user import User

people_bp = Blueprint("people", __name__, url_prefix="/people")


@people_bp.route("/<int:user_id>/photo")
@login_required
def photo(user_id):
    u = User.query.get_or_404(user_id)
    if not (current_user.can_view_admin or current_user.id == u.id):
        abort(403)
    if not (u.profile and u.profile.photo):
        abort(404)
    return Response(u.profile.photo, mimetype=u.profile.photo_mime or "image/jpeg",
                    headers={"Cache-Control": "private, max-age=300"})


@people_bp.route("/<int:user_id>/id-document")
@login_required
def id_document(user_id):
    if not current_user.can_view_admin:          # manager or owner only
        abort(403)
    u = User.query.get_or_404(user_id)
    if not (u.profile and u.profile.id_document):
        abort(404)
    return Response(u.profile.id_document, mimetype=u.profile.id_doc_mime or "application/octet-stream",
                    headers={"Content-Disposition": f'inline; filename="{u.profile.id_doc_name or "id-document"}"',
                             "Cache-Control": "private, no-store"})
