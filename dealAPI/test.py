import os

os.environ["DATABASE_USER"] = "postgres"
os.environ["DATABASE_PASS"] = "password"
os.environ["DATABASE_HOST"] = "localhost"
os.environ["DATABASE_PORT"] = "5432"
os.environ["DATABASE_NAME"] = "dealdb"

import sqlalchemy as sa
from app import app, db
from app.models import Deal, Restaurant

app.app_context().push()

# r = Restaurant(
#    url="https://www.themanlyhotel.com.au/",
#    name="The Manly Hotel",
#    address="54 Cambridge Parade, Manly, QLD, 4179",
#    latitude=1.0,
#    longitude=1.0,
# )
# db.session.add(r)
# db.session.commit()

# r = Restaurant(
#    url="https://www.manlydeck.com.au/",
#    name="Manly Deck",
#    address="1/45 Cambridge Parade, Manly, QLD, 4179",
#    latitude=1.0,
#    longitude=1.0,
# )
# db.session.add(r)
# db.session.commit()

query = sa.select(Restaurant)
restaurants = db.session.scalars(query).all()
print(restaurants)

for r in restaurants:
    print(r.id, r.name, r.url)
