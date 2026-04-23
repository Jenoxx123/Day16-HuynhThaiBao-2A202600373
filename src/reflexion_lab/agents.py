from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from .mock_runtime import FAILURE_MODE_BY_QID, actor_answer as mock_actor_answer, evaluator as mock_evaluator, reflector as mock_reflector
from .ollama_runtime import actor_answer as ollama_actor_answer, evaluator as ollama_evaluator, reflector as ollama_reflector
from .schemas import AttemptTrace, QAExample, ReflectionEntry, RunRecord


@dataclass
class BaseAgent:
    agent_type: Literal["react", "reflexion"]
    max_attempts: int = 1
    mode: Literal["mock", "ollama"] = "mock"
    model: str | None = None

    def run(self, example: QAExample) -> RunRecord:
        reflection_memory: list[str] = []
        reflections: list[ReflectionEntry] = []
        traces: list[AttemptTrace] = []
        final_answer = ""
        final_score = 0
        for attempt_id in range(1, self.max_attempts + 1):
            if self.mode == "ollama":
                answer, actor_tokens, actor_latency = ollama_actor_answer(example, reflection_memory, model=self.model)
                judge, eval_tokens, eval_latency = ollama_evaluator(example, answer, model=self.model)
                token_estimate = actor_tokens + eval_tokens
                latency_ms = actor_latency + eval_latency
            else:
                answer = mock_actor_answer(example, attempt_id, self.agent_type, reflection_memory)
                judge = mock_evaluator(example, answer)
                token_estimate = 320 + (attempt_id * 65) + (120 if self.agent_type == "reflexion" else 0)
                latency_ms = 160 + (attempt_id * 40) + (90 if self.agent_type == "reflexion" else 0)
            final_answer = answer
            final_score = judge.score
            if judge.score == 0 and self.agent_type == "reflexion" and attempt_id < self.max_attempts:
                if self.mode == "ollama":
                    reflection, reflection_tokens, reflection_latency = ollama_reflector(
                        example,
                        attempt_id,
                        answer,
                        judge,
                        model=self.model,
                    )
                    token_estimate += reflection_tokens
                    latency_ms += reflection_latency
                else:
                    reflection = mock_reflector(example, attempt_id, judge)
                reflections.append(reflection)
                reflection_memory.append(reflection.next_strategy)
                trace_reflection = reflection
            else:
                trace_reflection = None
            trace = AttemptTrace(
                attempt_id=attempt_id,
                answer=answer,
                score=judge.score,
                reason=judge.reason,
                reflection=trace_reflection,
                token_estimate=token_estimate,
                latency_ms=latency_ms,
            )
            traces.append(trace)
            if judge.score == 1:
                break
        total_tokens = sum(t.token_estimate for t in traces)
        total_latency = sum(t.latency_ms for t in traces)
        failure_mode = "none" if final_score == 1 else FAILURE_MODE_BY_QID.get(example.qid, "wrong_final_answer")
        return RunRecord(
            qid=example.qid,
            question=example.question,
            gold_answer=example.gold_answer,
            agent_type=self.agent_type,
            predicted_answer=final_answer,
            is_correct=bool(final_score),
            attempts=len(traces),
            token_estimate=total_tokens,
            latency_ms=total_latency,
            failure_mode=failure_mode,
            reflections=reflections,
            traces=traces,
        )


class ReActAgent(BaseAgent):
    def __init__(self, mode: Literal["mock", "ollama"] = "mock", model: str | None = None) -> None:
        super().__init__(agent_type="react", max_attempts=1, mode=mode, model=model)


class ReflexionAgent(BaseAgent):
    def __init__(self, max_attempts: int = 3, mode: Literal["mock", "ollama"] = "mock", model: str | None = None) -> None:
        super().__init__(agent_type="reflexion", max_attempts=max_attempts, mode=mode, model=model)

