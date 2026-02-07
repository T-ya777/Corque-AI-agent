import os
from pathlib import Path
from typing import TypedDict



class Skill(TypedDict):
    """A skill that can be progressively disclosed to the agent."""
    name: str # Unique identifier for the skill
    description: str # 1-2 sentence description to show in system prompt
    content: str 




def get_skill_from_markdown(directory: str="skills") -> list[Skill]:
    """
    Load a skill from a markdown file in the given directory.
    """
    skill_list: list[Skill] = []
    baseDir = Path(__file__).resolve().parent.parent
    skills_dir = baseDir / "skills"

    if not os.path.exists(skills_dir):
        print(f"Warning: Skills directory not found at {skills_dir}")
        return []
    for filename in os.listdir(skills_dir):
        if filename.endswith(".md"):
            file_path = skills_dir / filename
            with open(file_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
                name = filename.replace(".md", "")
                if not lines:
                    continue
                description = lines[0].strip()
                content = "".join(lines[2:]) if len(lines) > 2 else "".join(lines)
                skill_list.append(Skill(name=name, description=description, content=content))
    return skill_list

SKILLS: list[Skill] = get_skill_from_markdown()
