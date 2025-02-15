from app.api import bp


@bp.route("/restaurants/<int:id>", methods=["GET"])
def get_restaurant(id):
    return "This is a restaurant"


@bp.route("/restaurants", methods=["GET"])
def get_restaurants():
    return "This is a restaurant"


@bp.route("/restaurants/<int:id>/deals", methods=["GET"])
def get_deals(id):
    return "This is a restaurant"


@bp.route("/restaurants", methods=["POST"])
def create_restaurant():
    return "This is a restaurant"


@bp.route("/restaurants/<int:id>", methods=["PUT"])
def update_restaurant():
    return "This is a restaurant"
