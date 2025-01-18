from app import app, db


@app.errorhandler(404)
def not_found_error(error):
    return "Page not found", 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return "Internal server error", 500
