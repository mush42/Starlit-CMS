from starlit.boot.sqla import db
from starlit.models.abstract import AbstractPage


class Page(AbstractPage):
    __contenttype__ = "page"
    id = db.Column(db.Integer, primary_key=True)
