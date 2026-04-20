"""Memory types for the agent system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MemoryType(Enum):
    """Types of memories."""
    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"


@dataclass
class Memory:
    """Represents a single memory entry."""
    name: str
    description: str
    type: MemoryType
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_frontmatter(self) -> str:
        """Convert memory to markdown with frontmatter."""
        return f"""---
name: {self.name}
description: {self.description}
type: {self.type.value}
---

{self.content}
"""

    @classmethod
    def from_frontmatter(cls, text: str, filename: str) -> "Memory":
        """Parse memory from markdown with frontmatter."""
        lines = text.split('\n')

        # Parse frontmatter
        if not lines or lines[0] != '---':
            # No frontmatter, treat entire text as content
            return cls(
                name=filename.replace('.md', ''),
                description="",
                type=MemoryType.USER,
                content=text
            )

        # Find frontmatter boundaries
        frontmatter_end = -1
        for i, line in enumerate(lines[1:], 1):
            if line == '---':
                frontmatter_end = i
                break

        if frontmatter_end == -1:
            # Invalid frontmatter
            return cls(
                name=filename.replace('.md', ''),
                description="",
                type=MemoryType.USER,
                content=text
            )

        # Parse frontmatter fields
        frontmatter = {}
        for line in lines[1:frontmatter_end]:
            if ':' in line:
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip()

        # Get content (everything after frontmatter)
        content = '\n'.join(lines[frontmatter_end + 1:]).strip()

        return cls(
            name=frontmatter.get('name', filename.replace('.md', '')),
            description=frontmatter.get('description', ''),
            type=MemoryType(frontmatter.get('type', 'user')),
            content=content
        )


@dataclass
class MemoryIndex:
    """Index entry for MEMORY.md."""
    name: str
    file: str
    description: str

    def to_markdown(self) -> str:
        """Convert to markdown list item."""
        return f"- [{self.name}]({self.file}) — {self.description}"
