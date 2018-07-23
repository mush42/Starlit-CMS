from collections import OrderedDict

# Module system
EXCLUDED_MODULES = []

# Flask SQLAlchemy
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Flask security
SECURITY_PASSWORD_HASH = 'bcrypt'
SECURITY_USER_IDENTITY_ATTRIBUTES = ['email', 'user_name']
SECURITY_CONFIRMABLE = False
SECURITY_RECOVERABLE = True
SECURITY_RESET_URL = '/reset-password/'

# Abstract models

# Update the slug of a particular item if the value of its __slugcolum__ changes
ALLWAYS_UPDATE_SLUGS = False

# Flask Babel support
DEFAULT_LOCALE = 'en'
SUPPORTED_LOCALES = OrderedDict((
    ('en', 'English'),
))

# Starlit specific configurations
STARLIT_LOAD_SETTINGS_JSON = False