# cyhealth

Simple docker container that checks outgoing and incoming "pings" and goes unhealthy if they aren't received before their timeout.

The code and configuration is kept simple on purpose.
There are various more fully-featured monitoring softwares out there, but most of them require configuration via UI.

cyhealth:
- Requires a simple .ini file configuration
- Doesn't have a webinterface
- Doesn't do notifications
- It simply sets its own container status to "unhealthy" when one of the pings times-out

Use whatever you are already using to monitor docker containers status to send you a notification.

# Example Configuration

Configuration lives at `/etc/cyhealth.ini`:

```
[test_incoming]
name = helloworld
type = incoming_ping
timeout = 60

[test_outgoing]
name = google
type = outgoing_ping
url = https://www.google.com/
timeout = 60
```

The incoming_ping will provide an endpoint on /helloworld that has to be POSTed to (eg like this) in order to satisfy the ping:
```
curl -X POST http://127.0.0.1:8085/helloworld
```

The configured default healthcheck (which you can overwrite in your docker-compose) has the following properties:
- start period 5s
- interval 60s
- retries 2

# How It Works In Detail
Docker will query the API endpoint /health every interval (60s). This API endpoint returns "OK" or 503 in case there was an error with one of the pings.

The health endpoint queries all "outgoing" pings before returning.
If any configured checks fail (ie it has been too long after the last ping), 503 will be returned and after X retries (2) the container goes to unhealthy state.

