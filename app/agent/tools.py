from app.agent.schemas import ToolDefinition


def make_save_fact_tool(username: str | None = None) -> ToolDefinition:
    if username:
        about = f"the user you are talking to right now ({username})"
        example = f'"{username} prefers Python over JavaScript for backend work."'
    else:
        about = "the user you are talking to right now"
        example = '"The user prefers Python over JavaScript for backend work."'

    return ToolDefinition(
        name="save_fact",
        description=(
            f"Save a personal fact worth remembering about {about}. "
            "Use ONLY when the current user explicitly states something in their CURRENT message "
            "that reveals a persistent preference, biographical detail, technical constraint, or important decision. "
            "NEVER call this based on retrieved memories, long-term memory sections, or previous context — "
            "those blocks may describe other users and must not trigger fact-saving. "
            "Do NOT save facts about people mentioned in the conversation — "
            "that context is captured separately. "
            "Do NOT save greetings, acknowledgements, or one-time context. "
            "Use save_chat_fact instead for things that belong to the group or chat as a whole "
            "(shared rules, group vocabulary, ongoing projects). "
            "If the new fact UPDATES or REPLACES existing facts (e.g. user changed preferred name or corrected earlier info), "
            "list the IDs of ALL outdated facts on that topic in `supersedes` — they will be permanently deleted. "
            "Supersede every conflicting fact, not just the most recent one. "
            "Copy IDs exactly from the <user-facts> block. Pass [] if this is a genuinely new fact."
        ),
        parameters={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": (
                        "The fact as a clear standalone statement. "
                        f"Always name the subject explicitly. Example: {example} "
                        "Write the fact in the SAME LANGUAGE the user is currently using."
                    ),
                },
                "supersedes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "IDs of existing facts that this new fact replaces. "
                        "Copy the id values exactly as they appear in the <user-facts> block. "
                        "Pass [] if this fact does not replace any existing ones."
                    ),
                },
            },
            "required": ["content", "supersedes"],
        },
    )


def make_save_chat_fact_tool() -> ToolDefinition:
    return ToolDefinition(
        name="save_chat_fact",
        description=(
            "Save a fact that belongs to this chat or group as a whole — not to any single participant. "
            "Use for: shared vocabulary or slang the whole group uses, ongoing group projects or decisions, "
            "rules or norms of the chat, topics the group is collectively working on. "
            "Do NOT use for personal facts about a specific user — use save_fact for those. "
            "Do NOT use for one-time context or things unlikely to matter in future conversations. "
            "If the new fact UPDATES or REPLACES existing chat facts "
            "(e.g. a project decision changed, a rule was updated), "
            "list the IDs of ALL outdated facts in `supersedes` — they will be permanently deleted. "
            "Copy IDs exactly from the <chat-facts> block. Pass [] if this is genuinely new."
        ),
        parameters={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": (
                        "The fact as a clear standalone statement about this chat or group. "
                        'Example: "This group uses \'лопата\' to mean a large smartphone." '
                        "Write the fact in the SAME LANGUAGE currently being used in the chat."
                    ),
                },
                "supersedes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "IDs of existing chat facts that this new fact replaces. "
                        "Copy the id values exactly as they appear in the <chat-facts> block. "
                        "Pass [] if this fact does not replace any existing ones."
                    ),
                },
            },
            "required": ["content", "supersedes"],
        },
    )
