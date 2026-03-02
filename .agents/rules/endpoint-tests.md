---
trigger: always_on
---

Whenever you create a new endpoint or modify an existing one make sure the endpoint is tested functionally.
To test the endpoint use the TestClient of the django-ninja package.
For fixtures and test dependencies use pytest fixtures.
Do not use any mocks.
Do not monkeypatch anything.