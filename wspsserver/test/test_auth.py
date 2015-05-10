from unittest import TestCase
from wspsserver.auth import BaseAuthManager, NullAuthManager, \
    SettingsAuthManager


class Settings(object):
    SUBSCRIBE_KEYS = {
        "a-channel": "foobar",
        "some-channel": "abc123"
    }

    PUBLISH_KEYS = {
        "a-channel": "barfoo",
        "another-channel": "cba321"
    }


class TestBaseAuthManager(TestCase):
    def test_authenticate(self):
        settings = Settings()
        am = BaseAuthManager(settings)

        with self.assertRaises(NotImplementedError):
            am.authenticate("a", "b", "c")


class TestNullAuthManager(TestCase):
    def test_authenticate(self):
        settings = Settings()

        am = NullAuthManager(settings)
        for event in ("abc", "publish", "subscribe"):
            for channel in ("some-channel", "abc123"):
                for key in (None, "", "foo"):
                    self.assertEqual(
                        am.authenticate(event, channel, key),
                        True
                    )


class TestSettingsAuthManager(TestCase):
    def test_invalid_message_type(self):
        settings = Settings()

        am = SettingsAuthManager(settings)
        with self.assertRaises(ValueError):
            am.authenticate("invalid-event", "a-channel", "")

    def test_authenticate_a_channel(self):
        settings = Settings()

        am = SettingsAuthManager(settings)

        self.assertEqual(
            am.authenticate("subscribe", "a-channel", None),
            False
        )

        self.assertEqual(
            am.authenticate("subscribe", "a-channel", "wrong password"),
            False
        )

        self.assertEqual(
            am.authenticate("subscribe", "a-channel", "foobar"),
            True
        )

        self.assertEqual(
            am.authenticate("publish", "a-channel", None),
            False
        )

        self.assertEqual(
            am.authenticate("publish", "a-channel", "wrong password"),
            False
        )

        self.assertEqual(
            am.authenticate("publish", "a-channel", "foobar"),
            False
        )

        self.assertEqual(
            am.authenticate("publish", "a-channel", "barfoo"),
            True
        )

    def test_authenticate_some_channel(self):
        settings = Settings()

        am = SettingsAuthManager(settings)

        self.assertEqual(
            am.authenticate("subscribe", "some-channel", None),
            False
        )

        self.assertEqual(
            am.authenticate("subscribe", "some-channel", "any password"),
            False
        )

        self.assertEqual(
            am.authenticate("subscribe", "some-channel", "abc123"),
            True
        )

        self.assertEqual(
            am.authenticate("publish", "some-channel", None),
            True
        )

        self.assertEqual(
            am.authenticate("publish", "some-channel", "any password"),
            True
        )

    def test_authenticate_another_channel(self):
        settings = Settings()

        am = SettingsAuthManager(settings)

        self.assertEqual(
            am.authenticate("subscribe", "another-channel", None),
            True
        )

        self.assertEqual(
            am.authenticate("subscribe", "another-channel", "any password"),
            True
        )

        self.assertEqual(
            am.authenticate("publish", "another-channel", None),
            False
        )

        self.assertEqual(
            am.authenticate("publish", "another-channel", "wrong password"),
            False
        )

        self.assertEqual(
            am.authenticate("publish", "another-channel", "cba321"),
            True
        )

    def test_authenticate_unknown_channel(self):
        settings = Settings()

        am = SettingsAuthManager(settings)

        self.assertEqual(
            am.authenticate("subscribe", "unknown-channel", None),
            True
        )

        self.assertEqual(
            am.authenticate("subscribe", "unknown-channel", "any password"),
            True
        )

        self.assertEqual(
            am.authenticate("publish", "unknown-channel", None),
            True
        )

        self.assertEqual(
            am.authenticate("publish", "unknown-channel", "any password"),
            True
        )

