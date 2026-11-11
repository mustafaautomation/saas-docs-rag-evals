---
id: v2-rate-limits
title: v2 rate limits
version: v2
---

On v2, live keys are allowed 300 requests per minute. Test keys are allowed 60 requests per minute. The burst allowance of 50 requests is added on top of the per-minute window. Response headers are RateLimit-Limit, RateLimit-Remaining, and RateLimit-Reset. When a client exceeds the limit, the API returns status 429 and error code rate_limited.

Count every request, including requests that return an error, against the same window.
