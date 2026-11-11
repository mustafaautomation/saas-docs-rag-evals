---
id: versioning
title: API versioning
version: shared
---

Two API versions are documented: v1 and v2. Put the version in the first segment of the resource path. You can also send the header Northline-Version. The value 2024-06-01 selects v1 behavior. The value 2025-09-15 selects v2 behavior. If the header and the path disagree, the path wins.

v1 is scheduled to be removed on 2027-01-01. New integrations should call v2. Read the migration page before you move an existing client.
