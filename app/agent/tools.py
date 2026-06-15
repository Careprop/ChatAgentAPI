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
            f"Save a fact worth remembering about {about}. "
            "Use only when they directly reveal a persistent preference, "
            "biographical detail, technical constraint, or important decision. "
            "Do NOT save facts about people mentioned in the conversation — "
            "that context is captured separately. "
            "Do NOT save greetings, acknowledgements, or one-time context."
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
                }
            },
            "required": ["content"],
        },
    )
