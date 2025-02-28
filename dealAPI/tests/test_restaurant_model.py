import os

os.environ["DATABASE_URL"] = "postgresql+psycopg2://"

from datetime import datetime, timedelta, timezone

import pytest
from app import app, db
from app.models import Deal, Restaurant


class RestaurantModelTest:
    @pytest.fixture(scope="class")
    def setup_class(self, request):
        # Set up the database
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        def teardown():
            with app.app_context():
                db.session.remove()
                db.drop_all()
                self.app_context.pop()

        request.addfinalizer(teardown)

        return self

    # @pytest.fixture(autouse=True)
    # def setup_method(self, setup_class):
    #    self.restaurant = setup_class.restaurant
    #    self.deal = setup_class.deal
