from fnmatch import fnmatch


class BaseAuthManager(object):
    """
    wspsserver.auth.BaseAuthManager

    Base class for managing authentication for publishing and subscribing to
    channels.
    """

    def __init__(self, settings):
        self.settings = settings

    def authenticate(self, event, channel, key):
        """
        Authenticate to this type of event, on the given channel, with the key

        :param str event: "publish" or "subscribe"
        :param str channel: The name of the channel in question
        :param str key: Key the client might have submitted, if any
        :return bool: If the action is ok
        """
        raise NotImplementedError(
            "Your auth manager seems to be rather incomplete"
        )


class NullAuthManager(BaseAuthManager):
    """
    wspsserver.auth.NullAuthManager

    No authentication required -mode. Everything is always allowed regardless
    of what the configuration says, or what the client sends.
    """

    def authenticate(self, event, channel, key):
        return True


class SettingsAuthManager(BaseAuthManager):
    """
    wspsserver.auth.SettingsAuthManager

    Basic authentication via the configuration in settings.

    SUBSCRIBE_KEYS and PUBLISH_KEYS -settings are maps from channel (fnmatch
    -style wildcard patterns are ok) to valid key.

    If there is no key defined for the channel, it's assumed ok. Limiting valid
    channels has a separate setting.
    """

    def authenticate(self, event, channel, key):
        if event == "subscribe":
            channel_keys = self.settings.SUBSCRIBE_KEYS
        elif event == "publish":
            channel_keys = self.settings.PUBLISH_KEYS
        else:
            raise ValueError("Invalid event type {}".format(event))

        for match in channel_keys:
            if match == channel or fnmatch(channel, match):
                # If the channel matches, the key must match
                return channel_keys[match] == key

        # If there's no channel match, it's all good
        return True


