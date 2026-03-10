# cyhealth

cyhealth is a small helper service that aggregates multiple incoming and outgoing “pings” and
exposes a single `/status` endpoint for Docker healtchecks or other external monitoring tools.

If any configured check times out, the container becomes unhealthy.
What happens next (eg alerting) is entirely up to whatever is watching the
docker healthstatus or querying the API endpoint.

There’s no UI and no notifications. Outgoing pings are triggered by a cron running inside the container.

---

## What this is for

cyhealth exists to answer one question:

> “Are all the things I care about still alive?”

It’s useful when:
- You want to combine multiple health signals into one Docker healthcheck
- Your monitoring system only allows a limited number of checks
- Configuring monitors through a UI is more work than it should be
- You already rely on Docker’s health status for automation

---

## What cyhealth does

- Collects multiple health checks:
  - Incoming pings (something must POST periodically)
  - Outgoing pings (cyhealth checks a URL)
  - Error pings (cyhealth fails for a certain amount of time after a ping is received)
- Aggregates them behind a single `/status` endpoint
- Marks the container unhealthy when a check times out
- Uses a simple `.ini` file for configuration

---

## What cyhealth does not do

- No web interface
- No notifications
- No metrics or history

Checks are triggered whenever `/trigger` is called (which is scheduled by the cron inside the container).

---

## Configuration

Configuration lives at: `/etc/cyhealth.ini`:

```ini
[test_incoming]
name = helloworld
type = incoming_ping
timeout = 60

[test_outgoing]
name = google
type = outgoing_ping
url = https://www.google.com/
timeout = 60

[test_error]
name = error
type = error_ping
timeout = 60
```

## Incoming pings
An incoming_ping exposes an HTTP endpoint that must be POSTed to within the configured timeout.

Example:
```
curl -X POST http://127.0.0.1:8085/helloworld
```

If no POST is received before the timeout expires, the check fails and /status will start returning 503.

One typical use case might be to have your backup system ping this URL on backup success. If no ping is received, you
know that your backup is having issues.

## Outgoing pings
An outgoing_ping checks a remote URL whenever /trigger is called.

If the request fails and the last successful check is older than the timeout, the check fails.
This is useful for monitoring your own services, but can also be used for external APIs etc.

This is automatically called every minute (scheduled by a cron inside the container). The interval can be overwritten with an environment variable.

## Error pings
An error_ping exposes an HTTP endpoint that can be POSTed to. If such a POST occurs, then cyhealth will fail for the
configured timeout.

Example:
```
curl -X POST http://127.0.0.1:8085/error
```

One typical use case might be to receive errors from other health check services (eg hardware monitoring).

## Health and Status endpoints
cyhealth exposes:
```
GET /status
```

- Returns 200 OK if all checks are within their timeout
- Returns 503 if any check has failed
- Docker uses the `/status` endpoint to determine container health

## Docker healthcheck
The container includes a default Docker healthcheck:
- start-period: 5s
- interval: 75s
- retries: 2

These control how often checks are evaluated and when the container becomes unhealthy.
You can override these values in docker-compose.yml if needed.
