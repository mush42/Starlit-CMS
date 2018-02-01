import sys
import os
from importlib import import_module
from warnings import warn
from werkzeug import import_string
from jinja2 import ChoiceLoader, FileSystemLoader
from flask import Flask, Blueprint
from flask.config import Config
from flask.helpers import locked_cached_property, get_root_path
from starlit.util.helpers import find_modules, import_modules


class StarlitConfig(Config):
    def from_module_defaults(self, import_name):
        pymod = sys.modules[import_name]
        if not pymod.__file__.endswith("__init__.py"):
            # A module, try to get the parent package
            import_name = ".".join(import_name.rsplit(".")[:-1])
        defaults_mod = import_string(import_name + ".defaults", silent=True)
        self.from_object(defaults_mod)


class StarlitModule(Blueprint):

    def __init__(self, name, import_name, *args, **kwargs):
        self.name = name
        self.import_name = import_name
        if kwargs.pop('builtin', False):
            self.name = "starlit-{}" .format(self.name)
        # flask wouldn't serve static files if this is not set 
        if not getattr(self, 'static_url_path', None):
            self.static_url_path="/static/" + self.name
        super(StarlitModule, self).__init__(
            self.name,
            self.import_name,
            static_url_path=self.static_url_path,
            *args, **kwargs)
        self.settings_providers = []
        self.finalize_funcs = []

    def register(self, app, *args, **kwargs):
        super(StarlitModule, self).register(app, *args, **kwargs)
        app.config.from_module_defaults(self.import_name)
        # Run the finalization functions
        for f in self.finalize_funcs:
            f(app)


    def settings_provider(self, func):
        self.settings_providers.append(func)
        def wrapped(*a, **kw):
            return func(*a, **kw)
        return wrapped

    def after_setup(self, func):
        self.finalize_funcs.append(func)
        def wrapped(*a, **kw):
            return func(*a, **kw)
        return wrapped

    def get_provided_settings(self):
        for provider in self.settings_providers:
            yield provider()


class Starlit(Flask):
    config_class = StarlitConfig

    def __init__(self, *args, **kwargs):
        super(Starlit, self).__init__(*args, **kwargs)
        self.modules = {}
        self.plugins = {}

    @locked_cached_property
    def jinja_loader(self):
        """Starlit modules should have higher priority"""
        mod_templates = [
            FileSystemLoader(self.template_folder),
            super(Starlit, self).jinja_loader,
        ]
        for mod in self.modules.values():
            if mod.template_folder:
                templates_dir = os.path.join(get_root_path(mod.import_name), mod.template_folder)
                mod_templates.append(FileSystemLoader(templates_dir))
        return ChoiceLoader(mod_templates)

    def register_module(self, module, **options):
        super(Starlit, self).register_blueprint(blueprint=module, **options)
        self.modules[module.name] = module

    def find_starlit_modules(self, pkg):
        for module in import_modules(pkg):
            modname = module.__name__
            if modname in self.config['EXCLUDED_MODULES']:
                continue
            starlit_modules = (v for v in module.__dict__.values() if isinstance(v, StarlitModule))
            for mod in set(starlit_modules):
                yield mod

    def provided_settings(self):
        opts = []
        for mod in self.modules.values():
            provider = getattr(mod, 'get_provided_settings', None)
            if provider is None:
                continue
            for provided in  provider():
                for p in provided:
                    p.module = mod
                opts.extend(provided)
        return opts

    def use(self, plugin, *args, **kwargs):
        plugin = plugin()
        self.plugins[plugin.name] = plugin
        plugin.init_app(self, *args, **kwargs)
        if plugin.needs_module_registration:
            self.register_module(plugin)
        return plugin
