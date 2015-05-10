import signal
import importlib
from fnmatch import fnmatch
from copy import copy
import json
from time import time
import threading

from tornado import websocket, web, ioloop
from tornado.websocket import WebSocketClosedError


_channel_subscribers = {}
_connections = 0
_is_closing = False
_ioloop = None
_periodic_callback = None


def _signal_handler(signum, frame):
    global _is_closing
    _is_closing = True

    print("Caught signal {}".format(signum))


def _check_exit():
    global _is_closing
    if _is_closing:
        print("Stopping IOLoop and periodic callback")
        _ioloop.stop()


def _load_auth_manager(settings):
    """
    Dynamically load the auth manager as defined in settings

    :param module settings: The application settings
    :raises ValueError: In case configuration is invalid
    :return wspsserver.auth.BaseAuthManager: An instance of the auth manager
    """

    try:
        module_name, class_name = settings.AUTHORIZATION_MANAGER.split(":")
    except:
        raise ValueError("AUTHORIZATION_MANAGER \"{}\" is not valid.".format(
            settings.AUTHORIZATION_MANAGER
        ))

    try:
        module = importlib.import_module(module_name)
    except ImportError:
        raise ValueError(
            "AUTHORIZATION_MANAGER \"{}\" is not valid. The module specified "
            "was not found.".format(
                settings.AUTHORIZATION_MANAGER
            )
        )

    try:
        auth_class = getattr(module, class_name)
    except AttributeError:
        raise ValueError(
            "AUTHORIZATION_MANAGER \"{}\" is not valid. The module does not "
            "contain the specified class.".format(
                settings.AUTHORIZATION_MANAGER
            )
        )

    return auth_class(settings)


class ConnectionManager(object):
    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger
        self.subscriptions = {}
        self.auth_manager = _load_auth_manager(settings)

    @staticmethod
    def reset():
        """
        Reset global values for testing purposes
        """

        global _channel_subscribers, _connections

        _channel_subscribers = {}
        _connections = 0

    def get_connections(self):
        """
        Provides access to the globals for tests
        """
        return _connections

    def get_channel_subscribers(self, channel):
        """
        Provides access to the globals for tests
        """

        return _channel_subscribers[channel]

    def on_open(self, handler):
        """
        Called when a new connection is opened by a client
        """

        global _connections
        _connections += 1

        self.subscriptions[handler] = []

        self.logger.info("New client from {}".format(
            handler.request.remote_ip)
        )

    def on_message(self, handler, message):
        """
        Called when a client sends a message of any kind

        :param str message:
        """

        if self.settings.DEBUG:
            self.logger.debug("Client said: {}".format(message))

        try:
            packet = json.loads(message)
        except ValueError:
            self.logger.exception(
                "Client from {} sent an invalid message".format(
                    handler.request.remote_ip
                )
            )
            handler.close(1002, "Invalid message")
            return

        try:
            self._process_packet(handler, packet)
        except Exception:
            self.logger.exception(
                "Uncaught exception when processing message from {}".format(
                    handler.request.remote_ip
                )
            )
            raise

    def on_close(self, handler):
        """
        Called when a client connection is closed
        """

        global _connections
        _connections -= 1

        self.logger.info("Client from {} disconnected!".format(
            handler.request.remote_ip
        ))

        for channel in self.subscriptions[handler]:
            if handler in _channel_subscribers[channel]:
                _channel_subscribers[channel].remove(handler)

    def _process_packet(self, handler, packet):
        """
        Handle WSPS packets

        :param dict packet: Data packet from the client
        """

        try:
            channel = packet["channel"]
            if not self._is_channel_valid(channel):
                self.logger.error(
                    "Client from {} tried an invalid channel {}".format(
                        handler.request.remote_ip,
                        channel
                    )
                )
                handler.close(1002, "Invalid channel")
                return

            # Extract and remove key from packet, so it doesn't
            # accidentally # end up somewhere it shouldn't
            key = None
            if "key" in packet:
                key = packet["key"]
                del packet["key"]

            if packet["type"] == "subscribe":
                self._subscribe(handler, channel, key)
            elif packet["type"] == "publish":
                self._message(handler, channel, packet, key)
            else:
                self.logger.error(
                    "Client from {} sent an invalid message type {}".format(
                        handler.request.remote_ip,
                        packet["type"]
                    )
                )
                handler.close(1002, "Invalid message type")
        except KeyError:
            self.logger.exception(
                "Client from {} sent an invalid packet".format(
                    handler.request.remote_ip
                )
            )
            handler.close(1002, "Invalid message")

    def _subscribe(self, handler, channel, key):
        """
        Client is asking to subscribe to the given channel

        :param str channel:
        :param str key:
        """

        if not self._authenticate("subscribe", channel, key):
            self.logger.error(
                "Client from {} failed subscribe authorization to {}".format(
                    handler.request.remote_ip,
                    channel
                )
            )
            handler.close(1002, "Authorization failed")
            return

        if channel not in _channel_subscribers:
            _channel_subscribers[channel] = []

        self.subscriptions[handler].append(channel)
        _channel_subscribers[channel].append(handler)

        if self.settings.DEBUG:
            self.logger.debug(
                "Client from {} subscribed to {}".format(
                    handler.request.remote_ip,
                    channel
                )
            )

    def _authenticate(self, event, channel, key):
        """
        Check if the user has the permission to do things

        :param str event:
        :param str channel:
        :param str key:
        :return bool:
        """

        return self.auth_manager.authenticate(event, channel, key)

    def _is_channel_valid(self, channel):
        """
        Check if the given channel name is valid based on the configuration

        :param str channel: The name of the channel
        :return bool:
        """

        for match in self.settings.ALLOWED_CHANNELS:
            if fnmatch(channel, match):
                return True

        return False

    def _message(self, handler, channel, packet, key):
        """
        Send out a message to the channel

        :param str channel:
        :param dict packet: Original publish packet from client
        :param str key:
        """

        out_packet = copy(packet)
        out_packet["type"] = "message"
        message = json.dumps(out_packet)

        if not self._authenticate("publish", channel, key):
            self.logger.error(
                "Client from {} failed publish authorization to {}".format(
                    handler.request.remote_ip,
                    channel
                )
            )
            handler.close(1002, "Authorization failed")

        if self.settings.DEBUG:
            self.logger.debug("Sending message from {} to channel {}".format(
                handler.request.remote_ip,
                channel
            ))

        if channel in _channel_subscribers:
            for subscriber in _channel_subscribers[channel]:
                try:
                    subscriber.write_message(message)
                except WebSocketClosedError:
                    self.logger.error("Error writing to client.")


def _get_handler(settings, logger):
    """
    Returns the WebSocket handler, giving it access to the settings

    :param module settings:
    :return:
    """

    manager = ConnectionManager(settings, logger)

    class SocketHandler(websocket.WebSocketHandler):
        """
        Handler for all communications over WebSockets
        """

        def check_origin(self, origin):
            """
            This is a security protection against cross site scripting attacks
            on browsers, since WebSockets are allowed to bypass the usual
            same-origin policies and don't use CORS headers.

            In the current system there is no need for this yet, thus we allow
            all.

            :param origin:
            :return:
            """

            return True

        def open(self):
            """
            Called when a new connection is opened by a client
            """
            manager.on_open(self)

        def on_message(self, message):
            """
            Called when a client sends a message of any kind

            :param str message:
            """
            manager.on_message(self, message)

        def on_close(self):
            """
            Called when a client connection is closed
            """
            manager.on_close(self)

    return SocketHandler


class Server(object):
    """
    Main manager for the server application
    """

    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger

        handlers = [
            (r'/', _get_handler(settings, logger))
        ]

        self.app = web.Application(
            handlers,
            autoreload=settings.DEBUG,
            debug=settings.DEBUG
        )

    def start(self):
        """
        Start the server
        """
        global _ioloop, _periodic_callback

        self.logger.info("Listening to {addr}:{port}".format(
            addr=self.settings.LISTEN_ADDRESS,
            port=self.settings.LISTEN_PORT
        ))

        self.app.listen(port=self.settings.LISTEN_PORT,
                        address=self.settings.LISTEN_ADDRESS)

        signal.signal(signal.SIGINT, _signal_handler)

        _ioloop = ioloop.IOLoop.instance()

        next_stat = time() + self.settings.STATS_SECONDS

        def _check():
            global next_stat
            _check_exit()
            current = time()
            if current > next_stat:
                self.show_stats()
                next_stat = current + self.settings.STATS_SECONDS

            if not _is_closing:
                _ioloop.call_later(0.25, _check)

        def _run():
            self.logger.info("Starting periodic checks")
            _ioloop.call_later(0.25, _check)

            self.logger.info("Starting IOLoop")

            _ioloop.start()
            # Waits until loop is stopped
            _ioloop.close()

            self.logger.info("IOLoop closed")

        thread = threading.Thread(target=_run)
        thread.start()

    def stop(self):
        """
        Stop the server
        """

        self.logger.info("Stopping server")
        _ioloop.stop()

    def show_stats(self):
        """
        Called periodically to show the system stats
        """

        self.logger.info("Connected clients: {}".format(_connections))