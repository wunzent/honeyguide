# Wireframe: `/{path}`

**Module**: {Module Name}
**Path**: `/{path}`
**Layout**: `layout.vue`
<!-- validate-skills: example -->
**Ref Spec**: [page-{name}-spec.md](./page-{name}-spec.md)
**Ref Diagram**: [page-{name}-diagram.md](./page-{name}-diagram.md)
**Status**: Draft
**Version**: 1.0
**Designer**: —
**Reviewed by**: —
**Figma**: —
**Last Updated**: YYYY-MM-DD

---

## 1. Overview

{1-2 ประโยคอธิบายว่าหน้านี้ใช้ทำอะไร + flow ออก/เข้า}

---

## 2. Visual Layout

### Desktop (≥1024px)
**Figma**: {link หรือ —}
**Image**: `./images/page-{name}-desktop.png`

```
┌─────────────────────────────────────────────────┐
│  [ASCII art ของ layout — header / sidebar /     │
│   content / footer ตามแต่ละหน้า]                │
│                                                  │
│   อธิบาย element สำคัญด้วย ← arrow              │
└─────────────────────────────────────────────────┘
```

### Mobile (<1024px)
**Figma**: {link หรือ —}
**Image**: `./images/page-{name}-mobile.png`

```
┌──────────────────────────────┐
│  [ASCII art ของ mobile        │
│   layout]                     │
└──────────────────────────────┘
```

---

## 3. Interaction States

### Inputs / Buttons / Links

| Element | Default | Hover | Focus | Active | Disabled | Loading | Error |
|---|---|---|---|---|---|---|---|
| Input | - | — | - | — | - | — | - |
| Button | - | — | - | — | - | — | - |
| Link | - | — | - | — | - | — | - |

**Note**: Style ของแต่ละ state ให้ยึดตาม Design System, Theme และ UI Component ของแต่ละ Project เป็นหลัก หลีกเลี่ยงการ hardcode color, border, ring หรือ state style หากมี existing token/component รองรับอยู่แล้ว

### Form-level States

| State | Trigger | Visual |
|---|---|---|
| **Idle** | initial | ฟอร์มปกติ ไม่มี banner |
| **Validation Error** | Zod fail แดง | input border แดง |
| **Loading** | submit pressed | ปุ่ม spinner + disabled |
| **API Error** | error code | toast สีแดง + error message|
| **Success** | API ok | toast + navigate |

---

## 4. Copy & i18n Keys

| Element | TH | EN | i18n Key | Status |
|---|---|---|---|---|
| Heading | ... | ... | `module.section.title` | ❌ hardcoded / ✅ migrated |
| Subtitle | ... | ... | `module.section.subtitle` | ❌ |
| Submit | ... | ... | `module.section.submit` | ❌ |

> ระบุ Status: `❌ hardcoded` ถ้ายังไม่ migrate · `✅` ถ้ามี key ใน `i18n/th.ts` + `i18n/en.ts` แล้ว

---

## 5. Design Tokens
**note**: Design Tokens ในเอกสารนี้ใช้เป็น reference สำหรับ UI เท่านั้น
ให้ยึด Design System, Theme และ UI Components ที่มีอยู่ในระบบเป็นหลัก หลีกเลี่ยงการ hardcode style และควร reuse existing token/component ก่อนสร้างใหม่

### Colors
| Token | ใช้ที่ |
|---|---|
| `text-gray-900` / `dark:text-white` | heading |
| `text-primary-600` | links |
| `bg-red-50 border-red-200 text-red-700` | error banner |

### Typography
| Element | Spec |
|---|---|
| Heading | `text-[20px] font-bold leading-[1.15] tracking-[-0.02em]` |
| Field label | `text-[13px] font-medium` |
| Submit button | `text-[15px] font-semibold tracking-wide` |

### Spacing & Radius
| Property | Value |
|---|---|
| Card max-width | `max-w-95` |
| Form gap | `flex flex-col gap-5` |
| Input radius | `rounded-[10px]` |

### Breakpoint
| BP | Behavior |
|---|---|
| `<lg` (<1024px) | single column |
| `lg` (≥1024px) | 2-column grid `minmax(0, 1.15fr) minmax(0, 1fr)` |

---

## 6. Accessibility Notes (optional)

### Focus Order (Tab key)
1. {first focusable element}
2. ...

### ARIA / Semantic
- {ARIA labels ที่ไม่ obvious — เช่น password show/hide button}
- Form ใช้ semantic `<form>` หรือใช้ UI Component / Design System ของ Project แทน native element หากมีรองรับ

### Color Contrast
- {text/bg pairs ที่ต้องระวัง WCAG AA 4.5:1}

### Other
