# The address we should listen to
# Can be e.g. 127.0.0.1, or 0.0.0.0 for all interfaces
LISTEN_ADDRESS = "0.0.0.0"

# Which port to subscribe to
LISTEN_PORT = 52525

# List of what channels are valid, supports wildcards (*, ?) as per fnmatch
# https://docs.python.org/2/library/fnmatch.html
ALLOWED_CHANNELS = (
    "*",
)

# Authorization manager, by default there is none required
# This is a combination of module import path and class inside it, separated
# by a colon (:), e.g.: wspsserver.auth:NullAuthManager
AUTHORIZATION_MANAGER = "wspsserver.auth:NullAuthManager"


# SettingsAuthManager configuration
#
# If using wspsserver.auth:SettingsAuthManager, you'll probably want to use
# SUBSCRIBE_KEYS and PUBLISH_KEYS.
#
# These are maps from channel match (supports wildcards like ALLOWED_CHANNELS)
# to valid key. If the channel is not defined in this a list it does not
# require a key.
#
# You'll generally want to make sure your ALLOWED_CHANNELS and *_KEYS -configs
# are synced.
#
SUBSCRIBE_KEYS = {}
PUBLISH_KEYS = {}


# How many seconds between showing connection statistics in the log
STATS_SECONDS = 60

# Enable debug mode, auto-reloads code on changes and logs more things
DEBUG = False

# Load local overrides
try:
    from local_settings import *
except ImportError:
    pass
