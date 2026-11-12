# Diagrams: `/{path}`

**Module**: {Module Name} (Phase {N})
<!-- validate-skills: example -->
**Ref Spec**: [page-{name}-spec.md](./page-{name}-spec.md)
**Last Updated**: YYYY-MM-DD

---

## 1. {Feature} Flow — Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant FE as Frontend
    participant API as Backend API

    User->>FE: กระทำอะไร
    FE->>API: METHOD /endpoint

    alt Success
        API-->>FE: 200 response
        FE->>FE: ทำต่อ
    else Error
        API-->>FE: 4xx error code
        FE->>FE: แสดง error
    end
```
