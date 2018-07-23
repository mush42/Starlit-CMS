import os
import csv
from flask import request, Response, stream_with_context, render_template
from flask_admin import expose
from flask_admin.model.template import EndpointLinkRowAction
from flask_admin.model.form import InlineFormAdmin
from flask_admin import helpers as h
from flask_admin._compat import csv_encode
from flask_wtf import Form
from werkzeug import secure_filename
from wtforms_alchemy import ModelForm
from wtforms.fields import IntegerField, SelectField
from wtforms.widgets import HiddenInput

from starlit.exceptions import StarlitConfigurationError
from starlit.boot.sqla import db
from starlit.babel import lazy_gettext
from starlit.util.wtf import RichTextAreaField
from starlit.util.helpers import date_stamp, paginate_with_args
from starlit_modules.form.models import Form, Field, FormEntry
from starlit_admin import AdminPlugin
from starlit_admin.core import AuthenticationViewMixin
from starlit_admin.modules.page import PageAdmin


def _process_field_value(field):
    """Used in the csv writing task to return an
    appropriate representation 
    """
    if field.value == '':
        return '[Empty]'
    if field.type == 'boolean':
        return 'True' if field.value else 'False'
    return field.value


def _gen_csv_file_name(form):
    form_updated = date_stamp(form.updated)
    return '-'.join((request.host, form.slug, form_updated)) + '.csv'


class FormAdmin(PageAdmin):
    inline_models = [(Field, dict(
            form_columns=['id', 'name', 'label', 'description', 'type', 'choices', 'default', 'required', 'max_length'],
                form_extra_fields={'type': SelectField(label=Field.type.info['label'], description=Field.type.info['description'], choices=sorted(Field.type.info['choices']))}
            ),),]
    column_extra_row_actions = list(PageAdmin.column_extra_row_actions)
    column_extra_row_actions.append(EndpointLinkRowAction(icon_class='fa fa-download', endpoint='.export_entries', title=lazy_gettext('Export Entries as CSV'), id_arg='pk'))
    column_extra_row_actions.append(EndpointLinkRowAction(icon_class='fa fa-table', endpoint='.view_entries', title=lazy_gettext('View Entries'), id_arg='pk'))
    form_excluded_columns = PageAdmin.form_excluded_columns + ["author", "created", "updated", "entries"]
    form_rules = list(PageAdmin.form_rules)
    form_rules.insert(6, 'fields')
    form_rules.insert(7, 'submit_text')
    form_rules.insert(8, 'submit_message')
    form_overrides = dict(PageAdmin.form_overrides)
    form_overrides.update({
        'submit_message': RichTextAreaField,
    })

    @expose('/export-entries/<int:pk>')
    def export_entries(self, pk):
        """Taken from Flask-Admin with some modifications, no shame!"""
        form = self.get_one(str(pk))
        filename = "attachment; filename=%s" %_gen_csv_file_name(form)
        class Echo(object):
            """
            An object that implements just the write method of the file-like
            interface.
            """
            def write(self, value):
                """
                Write the value by returning it, instead of storing
                in a buffer.
                """
                return value
        writer = csv.writer(Echo())
        def generate():
            # Append the column titles at the beginning
            titles = [csv_encode('date')] + [csv_encode(field.name) for field in form.fields]
            yield writer.writerow(titles)
            for entry in form.entries:
                vals = [csv_encode(entry.created.isoformat())] + [csv_encode(_process_field_value(field)) for field in entry.fields]
                yield writer.writerow(vals)
        return Response(
            stream_with_context(generate()),
            headers={'Content-Disposition': filename},
            mimetype='text/csv'
        )

    @expose('/view-entries/<int:pk>')
    def view_entries(self, pk):
        """View form entries"""
        form = self.get_one(str(pk))
        entries = FormEntry.query.filter_by(form=form)
        paginator = paginate_with_args(entries)
        return self.render('starlit_admin/form-entries.html', form=form, paginator=paginator, val_proc=_process_field_value)

@AdminPlugin.setupmethod
def reg_form_admin(app, admin):
    uploads_path = app.config.get('UPLOADS_PATH')
    if not app.config.get('FORM_UPLOADS_PATH', None):
        if uploads_path:
            app.config['FORM_UPLOADS_PATH'] = os.path.join(uploads_path, "forms")
        else:
            raise StarlitConfigurationError(help_message="Neither the `FORM_UPLOADS_PATH` is defined, nor the `UPLOADS_PATH` is defined. Please add one of these to your application config, for the file admin to start.")
    admin.add_view(FormAdmin(Form, db.session, name=lazy_gettext('Form'), category=lazy_gettext('Pages')))