---
id: pagination
title: Pagination
version: shared
---

List endpoints accept limit and starting_after. limit defaults to 20 and the maximum is 100. starting_after is a cursor. Pass the id of the last object you received. The response has has_more, a boolean, and data, an array.

There is no offset parameter. Do not send page numbers. If has_more is false, you have reached the end of the list.
