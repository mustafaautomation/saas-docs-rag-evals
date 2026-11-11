---
id: v1-rate-limits
title: v1 rate limits
version: v1
---

On v1, live keys are allowed 100 requests per minute. Test keys are allowed 20 requests per minute. There is no burst allowance on v1. Response headers are X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset. When a client exceeds the limit, the API returns status 429 and error code rate_limited.

Count every request, including requests that return an error, against the same window.
