from dotenv import load_dotenv
import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

load_dotenv()

model = ChatAnthropic(model="claude-haiku-4-5")
messages = [HumanMessage(content="What's the most traded commodity by volume?")]
response1 = model.invoke(messages)
messages.append(response1)
messages.append(HumanMessage(content="And by dollar value?"))
response2 = model.invoke(messages)
print(response2.content)