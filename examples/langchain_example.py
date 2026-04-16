"""
Example: Using Pith with LangChain.

1. Start Pith: pith serve
2. pip install langchain-openai
3. Run: python examples/langchain_example.py
"""

from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o-mini",
    base_url="http://localhost:8000/v1",  # Pith proxy
    api_key="sk-your-real-key",
)

response = llm.invoke("I would like you to please explain what LangChain is and how it works.")
print(response.content)
