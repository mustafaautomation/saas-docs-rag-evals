---
id: authentication
title: Authentication
version: shared
---

Authenticate every request with the Authorization header. Send a bearer token: Authorization: Bearer followed by the key. Live keys use the prefix nl_live_ and test keys use the prefix nl_test_. The full key is shown once in the dashboard and is not written in these docs. Do not commit a key to source control.

Test keys call the same resources as live keys. They are subject to the lower test-key limit documented on each version's rate limit page. A missing or rejected key returns status 401 and error code authentication_failed.
