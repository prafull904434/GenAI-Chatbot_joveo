def guardrail(question: str) -> str:
    blocked = ["password", "malware", "hack account", "bypass security", "exploit"]

    if any(word in question.lower() for word in blocked):
        return "I can help with GitLab handbook and direction topics, not unsafe requests."

    return ""