# WSPS server

WSPS stands for WebSocket Pub(lisher)-Sub(scriber), and that pretty much covers what it does. The WSPS server provides a WebSocket interface for clients to subscribe to messages on different "channels", and then publishing messages on those channels.

There is a client made for:

 * JavaScript (both browser and Node.js use): [wsps-javascript](https://github.com/lietu/wsps-javascript)
 * Python: [wsps-python](https://github.com/lietu/wsps-python)

Authorization to subscribe/publish to channels is easily extensible, so if you
want to e.g. use token based authentication, you can easily write your own 
class for that.

Licensed under MIT and new BSD licenses, more details in `LICENSE.md`.


## Setting up

Requirements:

 * Python (tested on 2.7, so far)
 * For WSS (SSL support) you should terminate SSL with something like Nginx

You'll also need to install the libraries as specified in `requirements.txt`, generally this can be done easily with `pip`:
```
pip install -r requirements.txt
```

Using [virtualenv](https://virtualenv.pypa.io/en/latest/) is of course heavily recommended.

If you just want an open server with no security limitations on who can publish or subscribe to channels, just kick it off with the default settings:
```
python wsps.py
```

However I would imagine most users wanting to change e.g. publishing to require an authorization key, then you'll want to create a `local_settings.py` -file and configure it as per your requirements.

## Performance

Using the JavaScript library's `latency.html` -test I've managed to get about 3,000 messages/sec bounced through the WSPS server with the client, with an average latency of 0.3msec over localhost using Chrome 42 with a i7-4930k CPU running Windows 7.

Using 20 tabs on `listener.html` and 5 tabs on `sender.html` I managed to get a total throughput of 1,000 messages in and 10,000 messages out per second.

Keep in mind these are over *localhost*, real world performance will be different but the numbers show the overhead should be fairly low.

## Configuration

### Example

This sets up a WSPS server is running at localhost:52525, with some basic protection for subscribing and publishing to `some-channel`.

The server `local_settings.py` should contain the following:

```python
LISTEN_PORT = 52525

SUBSCRIBE_KEYS = {
    r"some-channel": "subscribe-key"
}

PUBLISH_KEYS = {
    r"some-channel": "publish-key"
}

VALID_CHANNELS = (
    r"some-channel",
)

AUTHORIZATION_MANAGER = 'wspsserver.auth.settings'
```

After that, this code should work in a browser with WSPS script loaded:
```javascript
var subscribeKey = "subscribe-key";
var writeKey = "publish-key";

var wsps = WSPS.create({
    server: "ws://localhost:52525",
    onclose: function() {
        console.log("Disconnected, reconnecting...");
        wsps.connect();
    }
});

var receive = function(packet) {
    console.log(packet.data.msg);
};

wsps.subscribe("some-channel", receive, subscribeKey);
wsps.connect();

var send = function() {
    wsps.publish("some-channel", {msg: "Hello, WSPS!"}, writeKey);
};

setTimeout(send, 2500);
```

In Node.js you only need to prepend:
```javascript
var WSPS = require("wsps");
```


### Configuration

You should not edit `settings.py` -directly so you don't have to worry about
updating it with every update. Instead you should create a `local_settings.py`
-file with all the overrides you want to the default configuration.

When using `local_settings.py`, all of the settings below are OPTIONAL.


**LISTEN_ADDRESS**

Defines what address WSPS listens to, generally you'll want to leave it to
"0.0.0.0" for all available interfaces, or "127.0.0.1" for localhost -only.


**LISTEN_PORT**

Configures which network port WSPS listens to, 52525 is the default.


**ALLOWED_CHANNELS**

List of what channels are valid on this server. Supports wildcards via
[fnmatch](https://docs.python.org/2/library/fnmatch.html), and e.g. `*` means
everything is ok.

You might want to use e.g. something similar to these:

 * `public`
 * `system-status`
 * `user/?*`
 * `product/?*`


**AUTHORIZATION_MANAGER**

Defines which class to use to check for client's authorization to publish or
subscribe to channels. The value is a combination of Python module and class
name separated with a colon (`:`), e.g. `wpsserver.auth:NullAuthManager` uses
the NullAuthManager class inside the python module `wpsserver.auth`.

If you want to create your own auth manager all you really need to do is have
an `__init__` -method that takes in settings as an argument and provides a
method matchin the signature `authenticate(self, event, channel, key)`.
 
You can also extend `wspsserver.auth.BaseAuthManager`, in case more logic is
added to the base class.

Built-in auth managers:

 * `wspsserver.auth:NullAuthManager` - No authentication necessary, ever,
    allow everything
 * `wspsserver.auth.SettingsAuthManager` - Simple authentication via
    SUBSCRIBE_KEYS and PUBLISH_KEYS in settings
    

**SUBSCRIBE_KEYS** and **PUBLISH_KEYS**

Configuration specific to `wspsserver.auth.SettingsAuthManager` which manages
the key clients need to send to be allowed to subscribe or publish to channels.

For example, to require the key `abc123` when publishing to a channel matching
`user/?*` you should set PUBLISH_KEYS to: `{r"user/?*": "abc123"}` 

If the client is trying to publish or subscribe to a channel that is valid
according to ALLOWED_CHANNELS, and there is no match in these settings, it
will be automatically ALLOWED.


**STATS_SECONDS**

Simply a number of seconds between status updates on screen, e.g. `60` will
show you the number of currently connected clients once per minute.


**DEBUG**

Enables debug mode for Tornado (which e.g. auto-reloads code on changes), and
logs many more things. Useful mainly for development purposes.


## Testing

Once you have everything in place you should be able to run the tests with:
```
nosetests --with-coverage --cover-package=wspsserver
```


# Financial support

This project has been made possible thanks to [Cocreators](https://cocreators.ee) and [Lietu](https://lietu.net). You can help us continue our open source work by supporting us on [Buy me a coffee](https://www.buymeacoffee.com/cocreators).

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/cocreators)
