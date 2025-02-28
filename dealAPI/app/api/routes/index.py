from app.api import bp


@bp.route("/", methods=["GET"])
@bp.route("/index", methods=["GET"])
def index():
    return "Hello, World!"
