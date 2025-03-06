import sqlalchemy as sa
from flask import request

from app import db
from app.api import bp
from app.models import Deal, Restaurant


@bp.route("/restaurants/<int:id>", methods=["GET"])
def get_restaurant(id):
    return db.get_or_404(Restaurant, id).to_dict()


@bp.route("/restaurants", methods=["GET"])
def get_restaurants():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    return Restaurant.to_collection_dict(
        sa.select(Restaurant), page, per_page, "api.get_restaurants"
    )


@bp.route("/restaurants/<int:id>/deals", methods=["GET"])
def get_restaurant_deals(id):
    restaurant = db.get_or_404(Restaurant, id)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    return Deal.to_collection_dict(
        restaurant.deals.select(), page, per_page, "api.get_restaurant_deals", id=id
    )


@bp.route("/restaurants", methods=["POST"])
def create_restaurant():
    return "This is a restaurant"


@bp.route("/restaurants/<int:id>", methods=["PUT"])
def update_restaurant():
    return "This is a restaurant"
