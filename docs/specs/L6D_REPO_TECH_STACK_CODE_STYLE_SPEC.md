# L6D Repo Tech Stack / Code Style Spec

## 1. 目的

本文件定義 repo-level 的技術棧與程式碼風格約束。

它存在的原因是：

- 防止 agent 混用不同世代的 Python / SQLAlchemy / Pydantic 寫法
- 防止長時間自主實作時產生 code style drift
- 讓 runtime / tests / migrations / adapters 維持可預期一致性

本文件是：

- `L6A` 的選型補件
- `L6B` 的實作風格約束

---

## 2. Repo Tech Stack Truth

### 2.1 Python

- target runtime = `Python 3.12`

規則：

- 新程式碼以 Python 3.12 可用語法為準
- 可使用：
  - `X | None`
  - built-in generics like `list[str]`
  - `match` only when it clearly improves readability

### 2.2 Web / API Layer

- framework = `FastAPI`

規則：

- HTTP entrypoints 只放在 route layer
- route layer 不承接 domain logic

### 2.3 ORM / Persistence

- ORM = `SQLAlchemy 2.x typed style`

強制風格：

- 使用 `Mapped[...] = mapped_column(...)`
- 使用 `DeclarativeBase`
- 不新增舊式：
  - `Column(Integer, ...)`
  - untyped declarative attributes

### 2.4 Validation / Runtime Contracts

- validation layer = `Pydantic v2`

強制風格：

- 使用 `BaseModel`
- 使用 `Field(...)`
- 輸出序列化優先：
  - `model_dump(mode="json")`
  - `model_dump_json(...)`
- 不新增舊式：
  - `.dict()`
  - `.json()`
  - `Config` v1 style unless forced by legacy compatibility

### 2.5 Test Runner

- primary runner = `pytest`

強制風格：

- 新測試用 `python -m pytest ...`
- fixture 優先明確、局部，不做全域魔法 fixture 擴張

---

## 3. Architecture Layer Boundaries

### 3.1 `app/domain`

放：

- canonical entities / value objects
- domain-level typed models
- pure domain rules

不放：

- SQLAlchemy session handling
- provider API calls
- route/request objects

### 3.2 `app/application`

放：

- runtime orchestration helpers
- commit / proposal / trace services
- pass-to-pass transition logic

不放：

- raw HTTP handling
- provider SDK-specific payload building
- direct DB table definitions

### 3.3 `app/infrastructure`

放：

- repositories
- persistence helpers
- storage adapters
- schema export / import tooling

不放：

- product policy truth
- prompt semantics

### 3.4 `app/providers`

放：

- BuilderSpace adapter
- direct provider adapters
- provider-specific request/response normalization

不放：

- domain truth
- meal classification semantics
- ledger arithmetic

### 3.5 `app/usecases`

定位：

- thin entrypoint / vertical-slice assembly layer

規則：

- 可以組裝 application + provider + persistence
- 不應繼續擴張成厚 orchestrator
- 新責任優先進 `app/application` 或 `app/infrastructure`

### 3.6 `app/observability`

放：

- trace envelope
- request trace writes
- stage trace writes
- replay/triage helpers

不放：

- business decisions

---

## 4. Model / Adapter Style Rules

### 4.1 Logical model roles first

程式內部優先使用：

- `fast_router_model`
- `strict_reasoner_model`
- `response_writer_model`
- `vision_parser_model`

而不是把 provider model id 當成 architecture truth。

### 4.2 Provider model IDs must stay in adapter/config boundary

像：

- `grok-4-fast`
- `gpt-5`
- `gemini-2.5-pro`

只能存在於：

- provider adapter
- provider config
- readiness / trace metadata

不應直接寫死在：

- pass contract logic
- domain logic
- deterministic math

---

## 5. Typing Rules

### 5.1 New Python code must be typed

規則：

- 新函式要有參數型別與回傳型別
- 可接受少量 `Any`，但只限：
  - provider interfaces
  - glue code around legacy runtime
  - test doubles

### 5.2 Avoid untyped dict blobs for stable contracts

若某結構是：

- pass output
- repository return
- canonical write input
- benchmark artifact

則優先使用 typed model，而不是裸 `dict[str, Any]`

例外：

- trace metadata
- provider raw payload excerpts

### 5.3 Enums

若值集合已由 [`L2A Data Dictionary Spec`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2A_DATA_DICTIONARY_SPEC.md) 定義：

- runtime 內不得再隱式擴充
- test fixture 也必須用同一合法值

---

## 6. SQLAlchemy Rules

### 6.1 New ORM declarations

必須使用：

```python
class ExampleRecord(Base):
    __tablename__ = "example"

    id: Mapped[int] = mapped_column(primary_key=True)
```

不得新增：

```python
id = Column(Integer, primary_key=True)
```

### 6.2 Query style

新程式優先使用：

- `select(...)`
- `session.execute(select(...))`

可暫時容忍 legacy `db.query(...)` 在舊路徑中存在，但新程式不再擴張它。

### 6.3 Persistence helpers

repository / persistence helper 必須：

- 明確處理 commit / refresh
- 不偷偷做 product-policy decisions

---

## 7. Pydantic Rules

### 7.1 Serialization

新程式統一使用：

- `model_dump(mode="json")`
- `model_dump_json(ensure_ascii=False)` when writing json strings

### 7.2 Defaults

- 使用 `Field(default_factory=...)` 承載 mutable defaults
- 不用裸 `[]` / `{}` 作 model class default

### 7.3 Contract evolution

若調整既有 pass/result schema：

- 優先 additive change
- 若是 breaking change，需對齊 spec 與 tests

---

## 8. Import / Module Rules

### 8.1 Import style

repo 內模組優先：

- package-relative imports inside `app/*`

script entrypoints 可用：

- repo-root path bootstrap
- 然後 `from app... import ...`

### 8.2 Circular import avoidance

禁止在 package `__init__.py` 內擴張高耦合 runtime imports。

像：

- repository implementation
- commit bridge
- heavy usecase helpers

不應互相透過 package `__init__` 形成隱性 import graph。

---

## 9. Testing / Benchmark Rules

### 9.1 Regression first

修真 bug 時：

- 優先補 regression / unit / focused flow test

### 9.2 Canonical persistence tests

對 canonical persistence 的新變更，至少覆蓋：

- create/read
- active version supersession
- ledger recompute
- proposal/observation skeleton writeability

### 9.3 Benchmark fixtures

benchmark fixture 的 enum 與欄位合法值，必須服從 `L2A`。

---

## 10. Script / Tooling Rules

### 10.1 Repo scripts

新 scripts 放 `scripts/`

規則：

- 可獨立執行
- 若需 import `app`, 必須自行補 repo-root bootstrap
- 輸出應明確、可 grep、可自動化

### 10.2 Docs / spec safety

涉及 canonical docs 的修改必須服從：

- [`docs/governance/SPEC_EDITING_PROTOCOL.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/SPEC_EDITING_PROTOCOL.md)
- [`docs/governance/ENCODING_POLICY.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/ENCODING_POLICY.md)

---

## 11. Anti-Drift Rules for Long-Running Agents

如果 agent 要長時間自主實作：

- 不得混用 SQLAlchemy 1.x / 2.x style
- 不得混用 Pydantic v1 / v2 serialization style
- 不得在 `usecases` 新增越來越厚的 domain logic
- 不得把 provider model id 當 architecture truth
- 不得以自由 dict 取代穩定 pass/result contract

當遇到不確定時，優先：

1. 查 `L2A`
2. 查 `L3.x`
3. 查 `L6A/L6B/L6C`
4. 再決定實作方式

---

## 12. Implementation Rule

任何 agent 在本 repo 新增或重構 Python 程式碼時，必須服從本文件。

如果既有 legacy code 與本文件衝突：

- legacy code 可暫時保留
- 但新變更不得擴張舊風格
- 重構時應朝本文件規定方向收斂

