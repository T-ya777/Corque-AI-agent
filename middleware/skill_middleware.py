from langchain.agents.middleware import ModelRequest, ModelResponse, AgentMiddleware
from langchain.messages import SystemMessage
from typing import Callable
from core.skill_loader import SKILLS
from tools.loadskillTools import load_skill
class skillMiddleware(AgentMiddleware):
    tools = [load_skill]
    def __init__(self):
        skill_list = []
        for skill in SKILLS:
            skill_list.append(f"- **{skill['name']}**: {skill['description']}")
        self.skill_prompt = "\n".join(skill_list)

    def wrap_model_call(self,
                        request: ModelRequest,
                        handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        """Inject the skill prompt into the model's system prompt."""
        skills_addendum = (f"\n\n## Available Skills\n\n{self.skill_prompt}\n\n"
            "Use the load_skill tool when you need detailed information "
            "about handling a specific type of request.")

        new_content = list(request.system_message.content_blocks)+[{"type": "text", "text": skills_addendum}]
        new_system_message = SystemMessage(content=new_content)
        modified_request = request.override(system_message=new_system_message)
        return handler(modified_request)