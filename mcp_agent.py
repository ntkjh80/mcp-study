import uuid
from typing import Optional, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_core.runnables import RunnableConfig

class MCPAgent:
    QUERY_THREAD_ID = str(uuid.uuid4())
    TIMEOUT_SECONDS = 300
    RECURSION_LIMIT = 100
    USE_ASTREAM_LOG = True
    
    MCP_CHAT_PROMPT = """You are a helpful AI assistant that can use tools to answer questions..."""  # 원본 프롬프트 유지

    def __init__(self, temperature: float, system_prompt: Optional[str], tools: list):
        self.chat_model = ChatOllama(
            model="MFDoom/deepseek-r1-tool-calling:14b",
            temperature=temperature
        )
        self.agent = create_react_agent(
            model=self.chat_model,
            tools=tools,
            checkpointer=MemorySaver()
        )
        self.system_prompt = system_prompt or self.MCP_CHAT_PROMPT

    def _get_streaming_callback(self):
        accumulated_text = []
        accumulated_tool_info = []

        def callback_func(data: Any):
            if isinstance(data, dict):
                agent_step_key = next(
                    (k for k in data if isinstance(data.get(k), dict) and "messages" in data[k]),
                    None
                )
                if agent_step_key:
                    messages = data[agent_step_key].get("messages", [])
                    for message in messages:
                        if isinstance(message, AIMessage) and message.content:
                            content_chunk = message.content.encode("utf-8", "replace").decode("utf-8")
                            accumulated_text.append(content_chunk)
                            print(content_chunk, end="", flush=True)
                        elif isinstance(message, ToolMessage):
                            tool_info = f"Tool Used: {message.name}\nResult: {message.content}"
                            accumulated_tool_info.append(tool_info)

        return callback_func, accumulated_text, accumulated_tool_info

    async def process_query(self, query: str) -> Dict:
        callback_func, accumulated_text, accumulated_tool_info = self._get_streaming_callback()
        initial_messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=query)
        ]

        config = RunnableConfig(
            recursion_limit=self.RECURSION_LIMIT,
            configurable={"thread_id": self.QUERY_THREAD_ID}
        )

        try:
            async for chunk in self.agent.astream_log(
                {"messages": initial_messages},
                config=config,
                include_types=["llm", "tool"]
            ):
                callback_func(chunk.ops[0]["value"])
        except Exception as e:
            print(f"\nError during response generation: {str(e)}")
            return {"error": str(e)}

        return {
            "output": "".join(accumulated_text).strip(),
            "tool_calls": "\n".join(accumulated_tool_info) if accumulated_tool_info else ""
        }
