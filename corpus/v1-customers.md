---
id: v1-customers
title: v1 customers
version: v1
---

Create a customer with POST /v1/customers. The body fields are name (string, required), email (string, required), and external_id (string, optional). Fetch one customer with GET /v1/customers/{id}. List customers with GET /v1/customers. Customer ids start with cus_.

v1 does not accept a tax identifier or a billing address object. There is no PATCH method on v1 customers.
