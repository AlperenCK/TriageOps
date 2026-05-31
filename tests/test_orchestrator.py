"""Ajan tool-calling dongusunun mock LLM + mock executor ile testi."""

from types import SimpleNamespace

from devops_agent.agent.orchestrator import Orchestrator
from devops_agent.config import Settings


def _tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


class _ScriptedLLM:
    """Onceden tanimlanmis mesaj dizisini sirayla dondurur."""

    def __init__(self, messages):
        self._messages = list(messages)
        self.calls = []

    def chat(self, messages, *, tools=None, temperature=0.1):
        self.calls.append({"messages": list(messages), "tools": tools})
        return self._messages.pop(0)


class _FakeExecutor:
    def __init__(self):
        self.calls = []

    def call(self, name, args):
        self.calls.append((name, args))
        if name == "get_failed_timeline_records":
            return '[{"name": "Compile", "log_id": 12, "issues": ["CS0103"]}]'
        if name == "get_task_log":
            return "error CS0103: 'Foo' yok"
        return "{}"


def test_loop_calls_tools_then_returns_report():
    llm = _ScriptedLLM(
        [
            # 1. tur: timeline cagir
            SimpleNamespace(
                content=None,
                tool_calls=[_tool_call("c1", "get_failed_timeline_records", '{"build_id": 1}')],
            ),
            # 2. tur: log cagir
            SimpleNamespace(
                content=None,
                tool_calls=[_tool_call("c2", "get_task_log", '{"build_id": 1, "log_id": 12}')],
            ),
            # 3. tur: nihai rapor
            SimpleNamespace(content="## Ozet\nCompile hatasi.", tool_calls=None),
        ]
    )
    executor = _FakeExecutor()
    orch = Orchestrator(llm=llm, executor=executor, settings=Settings())

    result = orch.analyze(1)

    assert result.tool_calls == 2
    assert "Compile hatasi" in result.report_markdown
    assert [c[0] for c in executor.calls] == [
        "get_failed_timeline_records",
        "get_task_log",
    ]
    # tool sonuclari sohbete 'tool' rolu ile eklenmis olmali
    last_messages = llm.calls[-1]["messages"]
    assert any(m.get("role") == "tool" for m in last_messages)


def test_loop_handles_immediate_answer():
    llm = _ScriptedLLM(
        [SimpleNamespace(content="## Ozet\nHata yok denetimi.", tool_calls=None)]
    )
    orch = Orchestrator(llm=llm, executor=_FakeExecutor(), settings=Settings())

    result = orch.analyze(99)

    assert result.tool_calls == 0
    assert result.report_markdown.startswith("## Ozet")
