import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from app.services.ai_tools import create_ai_tools


def create_ai_assistant(db, current_user):

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured"
        )

    model = ChatGoogleGenerativeAI(
        model="gemini-3.7-flash",
        google_api_key=api_key,
        temperature=0
    )

    # Create tools according to logged-in user's role
    tools = create_ai_tools(
        db,
        current_user
    )

    system_prompt = """
You are an AI College Assistant.

Your job is to answer questions about college
students using actual database information.

Important rules:

1. Never invent student data.
2. Always use database tools when the question
   requires college or student information.
3. Give simple and clear answers.
4. If data is not available, clearly say that
   the data is not available.
5. Never reveal information that the current user
   is not authorized to access.
6. Keep answers concise and useful.
7. Always follow the access permissions enforced
   by the database tools.
8. Never try to bypass security restrictions.

LANGUAGE RULE:

9. ALWAYS answer in English.
10. Even if the user asks in Hindi, Hinglish,
    Punjabi, or any other language, answer only
    in English.
11. Do not use Hindi script.
12. Keep the English simple and easy to understand.
"""

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt
    )

    return agent