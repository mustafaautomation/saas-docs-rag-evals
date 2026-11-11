---
id: v1-usage
title: v1 usage records
version: v1
---

Record usage with POST /v1/usage_records. The body fields are customer (required), metric (string, required, for example emails_sent), quantity (integer, required), and timestamp (unix seconds, optional). quantity must be a whole number in v1. v1 has no list method for usage records.

The field name metric is the v1 name of the thing you are counting.
