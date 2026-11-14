"""A Harbor agent that answers multiple-choice WSPNest tasks by log-likelihood with an open-weight model.

  harbor run -p <tasks> --agent-import-path wspnest.agents.logprob:LogprobReader \
      --ak model=Qwen/Qwen3.5-4B --ak adapter=<path-or-hub-id-of-a-LoRA> -e modal

The task's container must have the scoring script at /opt/wspnest/score.py and its Python dependencies (the
"scorer" variant of a task image provides both). The model reads its own weights, so this is auto-WSP.
"""
import shlex

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


class LogprobReader(BaseAgent):
    def __init__(self, *args, model: str = "", adapter: str = "", **kwargs):
        super().__init__(*args, model_name=model or kwargs.pop("model_name", None), **kwargs)
        self.model = model or (self.model_name or "")
        self.adapter = adapter

    @staticmethod
    def name() -> str:
        return "wspnest-logprob"

    def version(self) -> str:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        pass

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        if not self.model:
            raise ValueError("pass the model with --ak model=<hub id>")
        cmd = f"python3 /opt/wspnest/score.py --model {shlex.quote(self.model)}"
        if self.adapter:
            cmd += f" --adapter {shlex.quote(self.adapter)}"
        result = await environment.exec(cmd, timeout_sec=1800)
        context.metadata = {"model": self.model, "adapter": self.adapter, "exit_code": getattr(result, "return_code", None)}
