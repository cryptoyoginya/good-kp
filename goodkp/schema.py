"""Контракт данных отчета. Модель возвращает только это. Раздел 5 спеки."""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

PILLARS = 6
READERS = 3
BANNED = ("—", "·", "ё", "Ё")


class Strict(BaseModel):
    model_config = {"extra": "forbid"}

    @field_validator("*", mode="before")
    @classmethod
    def _no_banned(cls, v):
        if isinstance(v, str):
            for g in BANNED:
                if g in v:
                    raise ValueError(f"запрещенный символ {g!r} в тексте: {v[:60]!r}")
        return v


class Refusal(Strict):
    reason: str
    hint: str


class Meta(Strict):
    kp_number: str
    kp_date: str
    vendor: str
    client: str
    run_date: str
    title: str = Field(max_length=60)


class KV(Strict):
    k: str
    v: str


class FeedItem(Strict):
    step: Literal["pre", "1", "2", "3", "4", "5", "6"]
    text: str
    state: Literal["ok", "drop", "off"]


class Reader(Strict):
    name: str
    role: str
    kind: Literal["decider", "champion", "executor"]
    matters: str
    reads: str
    outcome: str
    feed: list[FeedItem] = Field(min_length=6, max_length=7)


class ChatFile(Strict):
    name: str
    size: str


class ChatMsg(Strict):
    side: Literal["me", "them"]
    name: Optional[str] = None
    text: str = ""
    file: Optional[ChatFile] = None
    status: Optional[Literal["Прочитано", "Доставлено"]] = None
    timer: Optional[Literal["start", "stop"]] = None


class Verdict(Strict):
    speaker: str
    text: str


class Block(Strict):
    id: int = Field(ge=1, le=PILLARS)
    title: str
    summary: str = Field(max_length=60)
    state: Literal["ok", "weak", "crit"]
    quote: str
    quote_src: Optional[str] = Field(default=None, pattern=r"^src-\d+$")
    why: str
    do: str
    was: str
    now: str


class Flag(Strict):
    from_: str = Field(alias="from")
    title: str = Field(max_length=60)
    text: str
    model_config = {"extra": "forbid", "populate_by_name": True}


class Hold(Strict):
    title: str
    text: str


class Section(Strict):
    title: str
    text: str


class FixedPage(Strict):
    subject: str
    from_initials: str = Field(max_length=3)
    sections: list[Section] = Field(min_length=PILLARS, max_length=PILLARS)


class PlanStep(Strict):
    title: str
    text: str
    minutes: int = Field(ge=1, le=40)


class SourceBlock(Strict):
    """Один блок исходного КП: заголовок, абзац, примечание, список или таблица."""
    id: str = Field(pattern=r"^src-\d+$")
    kind: Literal["h", "p", "note", "list", "table"]
    text: Optional[str] = None            # h, p, note
    items: Optional[list[str]] = None     # list
    rows: Optional[list[list[str]]] = None  # table, первая строка это шапка

    @model_validator(mode="after")
    def _payload(self):
        need = {"h": "text", "p": "text", "note": "text", "list": "items", "table": "rows"}[self.kind]
        if getattr(self, need) is None:
            raise ValueError(f"блок {self.id} kind={self.kind} требует поле {need}")
        return self


class Report(Strict):
    version: str
    methodology_version: str
    refusal: Optional[Refusal] = None
    meta: Optional[Meta] = None
    intake: Optional[list[KV]] = Field(default=None, min_length=6, max_length=6)
    readers: Optional[list[Reader]] = Field(default=None, min_length=READERS, max_length=READERS)
    chat: Optional[list[ChatMsg]] = Field(default=None, min_length=8, max_length=14)
    verdict: Optional[Verdict] = None
    blocks: Optional[list[Block]] = Field(default=None, min_length=PILLARS, max_length=PILLARS)
    flags: Optional[list[Flag]] = Field(default=None, min_length=4, max_length=6)
    holds: Optional[list[Hold]] = Field(default=None, min_length=2, max_length=4)
    fixed_page: Optional[FixedPage] = None
    plan: Optional[list[PlanStep]] = Field(default=None, min_length=4, max_length=6)
    source: Optional[list[SourceBlock]] = None

    @model_validator(mode="after")
    def _full_or_refusal(self):
        if self.refusal is not None:
            return self
        required = ["meta", "intake", "readers", "chat", "verdict", "blocks",
                    "flags", "holds", "fixed_page", "plan", "source"]
        missing = [f for f in required if getattr(self, f) is None]
        if missing:
            raise ValueError(f"без refusal обязательны поля: {', '.join(missing)}")
        kinds = [r.kind for r in self.readers]
        if kinds != ["decider", "champion", "executor"]:
            raise ValueError("readers должны идти в порядке decider, champion, executor")
        timers = [m.timer for m in self.chat if m.timer]
        if sorted(timers) != ["start", "stop"]:
            raise ValueError("в chat нужен ровно один timer:start и один timer:stop")
        if [b.id for b in self.blocks] != list(range(1, PILLARS + 1)):
            raise ValueError("blocks должны иметь id 1..6 по порядку")
        total = sum(p.minutes for p in self.plan)
        if not 45 <= total <= 75:
            raise ValueError(f"сумма minutes в plan должна быть от 45 до 75, сейчас {total}")
        ids = {s.id for s in self.source}
        dangling = [b.quote_src for b in self.blocks if b.quote_src and b.quote_src not in ids]
        if dangling:
            raise ValueError(f"quote_src ссылается на несуществующие блоки source: {dangling}")
        words = len(self.verdict.text.split())
        if not 25 <= words <= 70:
            raise ValueError(f"verdict.text: от 25 до 70 слов, сейчас {words}")
        return self


def export_schema() -> dict:
    return Report.model_json_schema(by_alias=True)
