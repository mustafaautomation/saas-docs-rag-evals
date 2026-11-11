---
id: v2-customers
title: v2 customers
version: v2
---

Create a customer with POST /v2/customers. The body fields are name (required), email (required), account_ref (string, optional), tax_id (string, optional), and billing_address (object with line1, city, and country, optional). account_ref is the v2 name for the caller's own account id. Fetch one customer with GET /v2/customers/{customer_id}. Update tax_id or billing_address with PATCH /v2/customers/{customer_id}. Customer ids start with cus_.

v2 customer create does not accept the v1 caller-account field name.
