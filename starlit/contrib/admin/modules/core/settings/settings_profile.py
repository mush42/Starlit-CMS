from starlit.boot.sqla import db
from starlit.babel import gettext, lazy_gettext
from starlit.models.settings import SettingsProfile
from starlit_admin.core import StarlitModelView


def active_formatter(view, context, model, name):
    if getattr(model, name):
        return gettext("Yes")
    return gettext("No")


class SettingsProfileAdmin(StarlitModelView):
    can_view_details = True
    # Edit in a dialog not in a new page.
    edit_modal = True
    details_modal = True
    # Enable CSRF protection.
    form_excluded_columns = ['settings']
    # How many entries to display per page?
    page_size = 5
    # Column formatters.
    column_formatters = {'is_active': active_formatter}
    column_default_sort = ("is_active", True)
    column_editable_list = ["name"]
