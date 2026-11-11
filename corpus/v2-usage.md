---
id: v2-usage
title: v2 usage records
version: v2
---

Record usage with POST /v2/usage_records. The body fields are customer_id (required), meter_id (required), quantity (decimal string, required), and timestamp (ISO-8601, optional). quantity is a decimal string, not an integer. List the meters you can send with GET /v2/meters. Meters are created in the dashboard.

v2 usage records identify the counter with meter_id.
