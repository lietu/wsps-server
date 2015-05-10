import json
import logging
from unittest import TestCase
from mock import Mock
from tornado.websocket import WebSocketClosedError

from wspsserver.auth import NullAuthManager, SettingsAuthManager
from wspsserver.server import _load_auth_manager, ConnectionManager


def _get_logger():
    # Disable logging from Tornado
    logger = logging.getLogger()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    logger.setLevel(logging.CRITICAL)

    return logger


logger = _get_logger()


class Settings(object):
    AUTHORIZATION_MANAGER = "wspsserver.auth:NullAuthManager"
    ALLOWED_CHANNELS = ("*",)
    DEBUG = True  # Making sure that debug logging doesn't cause errors


class Request(object):
    def __init__(self):
        self.remote_ip = "127.0.0.1"


class Handler(object):
    def __init__(self):
        self.request = Request()


class TestLoadAuthManager(TestCase):
    def test_load_auth_manager(self):
        settings = Settings()

        am = _load_auth_manager(settings)
        self.assertEqual(am.__class__, NullAuthManager)

        settings.AUTHORIZATION_MANAGER = "wspsserver.auth:SettingsAuthManager"
        am = _load_auth_manager(settings)
        self.assertEqual(am.__class__, SettingsAuthManager)

    def test_invalid_string(self):
        settings = Settings()
        settings.AUTHORIZATION_MANAGER = "a.b.c"

        with self.assertRaises(ValueError):
            _load_auth_manager(settings)

    def test_invalid_module(self):
        settings = Settings()
        settings.AUTHORIZATION_MANAGER = "invalid.module.that.does.not.exist:c"

        with self.assertRaises(ValueError):
            _load_auth_manager(settings)

    def test_invalid_class(self):
        settings = Settings()
        settings.AUTHORIZATION_MANAGER = "wspsserver.auth:InvalidClass"

        with self.assertRaises(ValueError):
            _load_auth_manager(settings)


class TestConnectionManager(TestCase):
    def setUp(self):
        ConnectionManager.reset()

    def test_on_open(self):
        settings = Settings()
        cm = ConnectionManager(settings, logger)

        handler = Handler()
        cm.on_open(handler)
        self.assertIn(handler, cm.subscriptions)
        self.assertEqual(cm.get_connections(), 1)

        cm.on_open(Handler())
        self.assertEqual(cm.get_connections(), 2)

    def test_on_message(self):
        settings = Settings()
        cm = ConnectionManager(settings, logger)

        handler = Handler()
        cm.on_open(handler)

        handler.close = Mock()
        cm.on_message(handler, "")
        handler.close.assert_called_once_with(1002, "Invalid message")

        handler.close = Mock()
        cm.on_message(handler, "{")
        handler.close.assert_called_once_with(1002, "Invalid message")

        handler.close = Mock()
        cm.on_message(handler, "{}")
        handler.close.assert_called_once_with(1002, "Invalid message")

    def test_publish_subscribe(self):
        settings = Settings()
        cm = ConnectionManager(settings, logger)

        handler = Handler()

        handler.write_message = Mock()
        cm.on_open(handler)

        packet = {
            "type": "subscribe",
            "channel": "test",
            "key": None
        }
        cm.on_message(handler, json.dumps(packet))

        packet = {
            "type": "publish",
            "channel": "test",
            "key": None,
            "data": "abc123"
        }
        cm.on_message(handler, json.dumps(packet))
        expected = '{"data": "abc123", "type": "message", "channel": "test"}'
        handler.write_message.assert_called_once_with(expected)

    def test_subscribe_auth_failed(self):
        settings = Settings()
        settings.AUTHORIZATION_MANAGER = "wspsserver.auth:SettingsAuthManager"
        settings.SUBSCRIBE_KEYS = {
            "test": "key123"
        }

        cm = ConnectionManager(settings, logger)

        handler = Handler()
        handler.close = Mock()

        cm.on_open(handler)
        cm._subscribe(handler, "test", "invalid key")
        handler.close.assert_called_once_with(1002, "Authorization failed")

    def test_message_auth_failed(self):
        settings = Settings()
        settings.AUTHORIZATION_MANAGER = "wspsserver.auth:SettingsAuthManager"
        settings.PUBLISH_KEYS = {
            "test": "key123"
        }

        cm = ConnectionManager(settings, logger)

        handler = Handler()
        handler.close = Mock()

        packet = {
            "type": "subscribe",
            "channel": "valid-1",
            "key": None
        }

        cm.on_open(handler)
        cm._message(handler, "test", packet, "invalid key")
        handler.close.assert_called_once_with(1002, "Authorization failed")

    def test_invalid_channel(self):
        settings = Settings()
        settings.ALLOWED_CHANNELS = ("valid-*",)
        cm = ConnectionManager(settings, logger)

        handler = Handler()

        handler.close = Mock()
        cm.on_open(handler)

        packet = {
            "type": "subscribe",
            "channel": "valid-1",
            "key": None
        }
        cm.on_message(handler, json.dumps(packet))
        handler.close.assert_has_calls([])

        packet = {
            "type": "subscribe",
            "channel": "invalid",
            "key": None
        }
        cm.on_message(handler, json.dumps(packet))
        handler.close.assert_called_once_with(1002, "Invalid channel")

    def test_invalid_message_type(self):
        settings = Settings()
        cm = ConnectionManager(settings, logger)

        handler = Handler()

        handler.close = Mock()
        cm.on_open(handler)

        packet = {
            "type": "bogus",
            "channel": "test",
        }
        cm.on_message(handler, json.dumps(packet))
        handler.close.assert_called_once_with(1002, "Invalid message type")

    def test_write_failed(self):
        settings = Settings()
        cm = ConnectionManager(settings, logger)

        handler = Handler()
        handler.write_message = Mock()

        fail_handler = Handler()
        fail_handler.write_message = Mock(side_effect=WebSocketClosedError)

        packet = {
            "type": "publish",
            "channel": "test",
            "data": "foo"
        }

        cm.on_open(handler)
        cm.on_open(fail_handler)

        cm._subscribe(handler, "test", None)
        cm._subscribe(fail_handler, "test", None)

        cm._message(fail_handler, "test", packet, None)

        expected = '{"type": "message", "data": "foo", "channel": "test"}'
        handler.write_message.assert_called_once_with(expected)

    def test_on_close(self):
        settings = Settings()
        cm = ConnectionManager(settings, logger)

        handler = Handler()
        cm.on_open(handler)
        cm._subscribe(handler, "test", None)
        self.assertIn(handler, cm.get_channel_subscribers("test"))
        self.assertEqual(cm.get_connections(), 1)
        cm.on_close(handler)

        self.assertEqual(cm.get_channel_subscribers("test"), [])
        self.assertEqual(cm.get_connections(), 0)
