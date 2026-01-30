# cyhealth

cyhealth is a small helper service that aggregates multiple incoming and outgoing “pings” and
exposes a single `/health` endpoint for Docker healtchecks or other external monitoring tools.

If any configured check times out, the container becomes unhealthy.
What happens next (eg alerting) is entirely up to whatever is watching the
docker healthstatus or querying the API endpoint.

There’s no UI, no notifications, and no scheduling logic beyond Docker’s own healthcheck.

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
- Aggregates them behind a single `/health` (or `/status`) endpoint
- Relies entirely on Docker’s healthcheck mechanism for timing and retries
- Marks the container unhealthy when a check times out
- Uses a simple `.ini` file for configuration

---

## What cyhealth does not do

- No web interface
- No notifications
- No metrics or history
- No internal timers or schedulers

Checks are triggered whenever `/health` is called (which is scheduled by the Docker healthcheck).

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
```

## Incoming pings
An incoming_ping exposes an HTTP endpoint that must be POSTed to within the configured timeout.

Example:
```
curl -X POST http://127.0.0.1:8085/helloworld
```

If no POST is received before the timeout expires, the check fails and /health will start returning 503.

One typical use case might be to have your backup system ping this URL on backup success. If no ping is received, you
know that your backup is having issues.

## Outgoing pings
An outgoing_ping checks a remote URL whenever /health is called.

If the request fails and the last successful check is older than the timeout, the check fails.
This is useful for monitoring your own services, but can also be used for external APIs etc.

## Health and Status endpoints
cyhealth exposes:
```
GET /health
GET /status
```

- Returns 200 OK if all checks are within their timeout
- Returns 503 if any check has failed
- /health triggers outgoing pings before checking timeout status, while status only checks the timeout status
- Docker uses the `/health` endpoint to determine container health

## Docker healthcheck
The container includes a default Docker healthcheck:
- start-period: 5s
- interval: 60s
- retries: 2

These control how often checks are evaluated and when the container becomes unhealthy.
cyhealth itself does not run background timers.
You can override these values in docker-compose.yml if needed.
