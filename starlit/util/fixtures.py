import os
import sys
import json
from dateutil.parser import parse
from werkzeug import import_string
from werkzeug.utils import cached_property
from starlit.exceptions import BadlyFormattedFixture
from starlit.boot.exts.sqla import db


class _Fixtured(object):
    """
    A Mixin class to enable the installation of fixtures
    from the path of an instance of `Starlit.wrappers.StarlitModule`.
    """
    
    def deserialize_instance(self, model, **obj):
        """Given a model and fields as a dict of keyword args
        this will return an instance of model with the fields
        """
        for k, v in obj.items():
            if hasattr(v, 'strip') and v.startswith('_file'):
                to_read = os.path.join(self.root_path, 'fixtures', '_files', v.lstrip('_file:'))
                obj[k] = open(to_read, 'r').read()
            elif 'date' in k:
                obj[k] = parse(v)
        return model(**obj)

    @cached_property
    def fixtures(self):
        """Returns the json decoded fixture or None"""
        try:
            with self.open_resource('fixtures/data.json') as datafile:
                return json.load(datafile)
        except IOError:
            return
        except json.JSONDecodeError:
            raise BadlyFormattedFixture("Error deserializing fixtures for: " + self.module)

    def install_fixtures(self):
        if not self.fixtures:
            return
        for model_import_path, objs in self.fixtures.items():
            model = import_string(model_import_path)
            # Continue gracefully if there is some data in the table
            if model.query.count():
                print("Skipping the installation of %s fixtures. Table is not empty." %model_import_path,)
                continue
            for obj in objs:
                instance = self.deserialize_instance(model, **obj)
                db.session.add(instance)
                db.session.commit()