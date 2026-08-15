from pathlib import Path

from olive.state.project import Project


class ProjectParser:
    """Parse an Olive Framework PROJECT.md file."""

    def parse(self, project_path: str | Path) -> Project:
        project_path = Path(project_path)

        if not project_path.exists():
            raise FileNotFoundError(
                f"Project file not found: {project_path}"
            )

        if project_path.name != "PROJECT.md":
            raise ValueError(
                "Olive Framework project specifications must be named PROJECT.md"
            )

        text = project_path.read_text(encoding="utf-8")

        name = self._parse_project_name(text)
        sections = self._parse_sections(text)

        return Project(
            name=name,
            goal=sections.get("Goal", ""),
            requirements=sections.get("Requirements", []),
            constraints=sections.get("Constraints", []),
            path=project_path,
        )

    @staticmethod
    def _parse_project_name(text: str) -> str:
        """Extract the project name from the first H1 heading."""

        for line in text.splitlines():
            if line.startswith("# ") and not line.startswith("## "):
                return line[2:].strip()

        raise ValueError("PROJECT.md must contain a # Project heading")

    @staticmethod
    def _parse_sections(text: str) -> dict:
        """Parse ## sections from PROJECT.md."""

        sections: dict[str, list[str] | str] = {}

        current_section = None
        current_lines = []

        for line in text.splitlines():
            if line.startswith("## "):
                if current_section:
                    sections[current_section] = current_lines

                current_section = line[3:].strip()
                current_lines = []

            elif current_section:
                current_lines.append(line)

        if current_section:
            sections[current_section] = current_lines

        parsed = {}

        for name, lines in sections.items():
            cleaned = [
                line.strip()
                for line in lines
                if line.strip()
            ]

            bullets = [
                line[2:].strip()
                for line in cleaned
                if line.startswith("- ")
            ]

            if bullets:
                parsed[name] = bullets
            else:
                parsed[name] = " ".join(cleaned)

        return parsed
