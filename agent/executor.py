import time
from typing import Any, Dict
from agent.memory import WorkingMemory
from agent.models import PlannedStep, StepResult
from tools.registry import ToolRegistry


class Executor:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def execute_step(
        self,
        step: PlannedStep,
        memory: WorkingMemory,
    ) -> StepResult:
        tool = self.registry.get(step.tool_name)
        if not tool:
            return StepResult(
                step_id=step.step_number,
                tool_name=step.tool_name,
                action="execute",
                input_data=step.tool_input,
                success=False,
                error_message=f"Tool '{step.tool_name}' not found in registry.",
            )

        # Substitute variable placeholders using working memory
        resolved_input = self._substitute_placeholders(step.tool_input, memory.discovered_facts)

        start_time = time.perf_counter()
        try:
            tool_res = await tool.execute(resolved_input)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            return StepResult(
                step_id=step.step_number,
                tool_name=step.tool_name,
                action=step.description,
                input_data=resolved_input,
                output_data=tool_res.data,
                success=tool_res.success,
                error_message=tool_res.error,
                duration_ms=round(duration_ms, 2),
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return StepResult(
                step_id=step.step_number,
                tool_name=step.tool_name,
                action=step.description,
                input_data=resolved_input,
                success=False,
                error_message=f"Unhandled tool execution exception: {str(e)}",
                duration_ms=round(duration_ms, 2),
            )

    def _substitute_placeholders(self, data: Any, facts: Dict[str, Any]) -> Any:
        if isinstance(data, dict):
            return {k: self._substitute_placeholders(v, facts) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_placeholders(item, facts) for item in data]
        elif isinstance(data, str):
            res = data
            # Expand facts with common alias variations (e.g. amount vs extracted_amount)
            expanded_facts = dict(facts)
            for k, v in list(facts.items()):
                if not k.startswith("extracted_"):
                    expanded_facts[f"extracted_{k}"] = v
                else:
                    expanded_facts[k.replace("extracted_", "")] = v

            for k, v in expanded_facts.items():
                token = f"{{{{{k}}}}}"
                if token in res:
                    # If whole string is token, preserve native type
                    if res.strip() == token:
                        return v
                    res = res.replace(token, str(v))
            return res
        return data
