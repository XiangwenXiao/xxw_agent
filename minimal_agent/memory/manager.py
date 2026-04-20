"""Memory manager for loading, saving, and managing memories."""

import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .types import Memory, MemoryType, MemoryIndex


DEFAULT_MEMORY_DIR = ".xxw_memory"
MEMORY_INDEX_FILE = "MEMORY.md"

MEMORY_GUIDANCE = """## Memory System

You have a persistent memory system. Use it to remember:
- User preferences and feedback
- Project context and constraints
- Important reference information

### Memory Types

- **user**: User's role, goals, knowledge (对应 USER.md)
- **feedback**: Guidance on what to do/avoid (对应 FEEDBACK.md)
- **project**: Ongoing work, deadlines, constraints (对应 PROJECT.md)
- **reference**: Pointers to external resources (对应 REFERENCE.md)

### How to Save Memories

When you learn something worth remembering:
1. Create a new .md file in .xxw_memory/
2. Use frontmatter format:
   ```
   ---
   name: Memory Name
   description: Brief description
   type: user | feedback | project | reference
   ---
   ```
3. Add content below the frontmatter
4. Update MEMORY.md index

### When to Access Memories

- Check memories at the start of each conversation
- Reference relevant memories when making decisions
- Verify memories are still current before acting on them
"""


class MemoryManager:
    """Manages persistent memory storage."""

    def __init__(self, memory_dir: str = DEFAULT_MEMORY_DIR):
        """Initialize memory manager with storage directory."""
        self.memory_dir = Path(memory_dir)
        self.index_file = self.memory_dir / MEMORY_INDEX_FILE
        self.memories: List[Memory] = []
        self._ensure_directory()
        self._load_memories()

    def _ensure_directory(self) -> None:
        """Create memory directory if it doesn't exist."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def _load_memories(self) -> None:
        """Load all memories from disk."""
        if not self.memory_dir.exists():
            return

        for file_path in self.memory_dir.glob("*.md"):
            if file_path.name == MEMORY_INDEX_FILE:
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                memory = Memory.from_frontmatter(content, file_path.name)
                self.memories.append(memory)
            except Exception as e:
                print(f"[MemoryManager] Failed to load {file_path}: {e}")

    def get_all_memories(self) -> List[Memory]:
        """Return all loaded memories."""
        return self.memories

    def get_memories_by_type(self, memory_type: MemoryType) -> List[Memory]:
        """Return memories filtered by type."""
        return [m for m in self.memories if m.type == memory_type]

    def get_memory(self, name: str) -> Optional[Memory]:
        """Get a specific memory by name."""
        for memory in self.memories:
            if memory.name == name:
                return memory
        return None

    def save_memory(self, memory: Memory) -> bool:
        """Save a memory to disk."""
        try:
            # Generate filename from name
            filename = memory.name.lower().replace(' ', '_') + '.md'
            file_path = self.memory_dir / filename

            # Write memory file
            file_path.write_text(memory.to_frontmatter(), encoding='utf-8')

            # Update index
            self._update_index()

            # Update in-memory list
            existing_idx = None
            for i, m in enumerate(self.memories):
                if m.name == memory.name:
                    existing_idx = i
                    break

            if existing_idx is not None:
                self.memories[existing_idx] = memory
            else:
                self.memories.append(memory)

            return True
        except Exception as e:
            print(f"[MemoryManager] Failed to save memory: {e}")
            return False

    def delete_memory(self, name: str) -> bool:
        """Delete a memory by name."""
        memory = self.get_memory(name)
        if not memory:
            return False

        try:
            filename = name.lower().replace(' ', '_') + '.md'
            file_path = self.memory_dir / filename

            if file_path.exists():
                file_path.unlink()

            self.memories.remove(memory)
            self._update_index()
            return True
        except Exception as e:
            print(f"[MemoryManager] Failed to delete memory: {e}")
            return False

    def _update_index(self) -> None:
        """Update MEMORY.md index file."""
        try:
            lines = [
                "# Memory Index",
                "",
                "This file tracks all persistent memories.",
                "",
            ]

            # Group by type
            by_type = {}
            for memory in self.memories:
                if memory.type not in by_type:
                    by_type[memory.type] = []
                by_type[memory.type].append(memory)

            # Write sections
            for mem_type in MemoryType:
                if mem_type not in by_type:
                    continue

                lines.append(f"## {mem_type.value.capitalize()}")
                lines.append("")

                for memory in sorted(by_type[mem_type], key=lambda m: m.name):
                    filename = memory.name.lower().replace(' ', '_') + '.md'
                    lines.append(f"- [{memory.name}]({filename}) — {memory.description}")

                lines.append("")

            self.index_file.write_text('\n'.join(lines), encoding='utf-8')
        except Exception as e:
            print(f"[MemoryManager] Failed to update index: {e}")

    def get_memory_context(self) -> str:
        """Generate memory context string for system prompt."""
        if not self.memories:
            return ""

        lines = [MEMORY_GUIDANCE, "", "### Current Memories", ""]

        # Group by type
        by_type = {}
        for memory in self.memories:
            if memory.type not in by_type:
                by_type[memory.type] = []
            by_type[memory.type].append(memory)

        # Format each type
        for mem_type in MemoryType:
            if mem_type not in by_type:
                continue

            lines.append(f"#### {mem_type.value.capitalize()}")
            lines.append("")

            for memory in by_type[mem_type]:
                lines.append(f"**{memory.name}**: {memory.description}")
                lines.append(memory.content)
                lines.append("")

        return '\n'.join(lines)

    def create_sample_memory(self) -> None:
        """Create a sample memory file if no memories exist."""
        if self.memories:
            return

        sample = Memory(
            name="Memory System Guide",
            description="How to use the memory system",
            type=MemoryType.REFERENCE,
            content="""This is a sample memory. Memories are stored in .xxw_memory/ directory.

To save a memory:
1. Create a .md file with frontmatter
2. Use type: user | feedback | project | reference
3. Update MEMORY.md index

Memories persist across conversations and help you remember important context."""
        )

        self.save_memory(sample)
