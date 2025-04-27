import argparse
import asyncio
import signal
import sys
import uuid
import warnings
from typing import Any, List, Optional, Dict

import json

import nest_asyncio
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages.tool import ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

QUERY_THREAD_ID = str(uuid.uuid4())
USE_ASTREAM_LOG = True
RECURSION_LIMIT = 100
TIMEOUT_SECONDS = 60 * 5
MCP_CHAT_PROMPT = """
    You are a helpful AI assistant that can use tools to answer questions.
    You have access to the following tools:

    {tools}

    Use the following format:

    Question: the input question you must answer
    Thought: you should always think about what to do
    Action: the action to take, should be one of [{tool_names}]
    Action Input: the input to the action
    Observation: the result of the action
    ... (this Thought/Action/Action Input/Observation can repeat N times)
    Thought: I now know the final answer
    Final Answer: the final answer to the original input question

    When using tools, think step by step:
    1. Understand the question and what information is needed.
    2. Look at the available tools ({tool_names}) and their descriptions ({tools}).
    3. Decide which tool, if any, is most appropriate to find the needed information.
    4. Determine the correct input parameters for the chosen tool based on its description.
    5. Call the tool with the determined input.
    6. Analyze the tool's output (Observation).
    7. If the answer is found, formulate the Final Answer. If not, decide if another tool call is needed or if you can answer based on the information gathered.
    8. Only provide the Final Answer once you are certain. Do not use a tool if it's not necessary to answer the question.
    """

def get_streaming_callback():
    accumulated_text = []
    accumulated_tool_info = []  # Store tool name and response separately

    # data receives chunk.ops[0]['value']
    def callback_func(data: Any):
        nonlocal accumulated_text, accumulated_tool_info

        if isinstance(data, dict):
            # Try to find the key associated with the agent step containing messages
            agent_step_key = next(
                (
                    k
                    for k in data
                    if isinstance(data.get(k), dict) and "messages" in data[k]
                ),
                None,
            )

            if agent_step_key:
                messages = data[agent_step_key].get("messages", [])
                for message in messages:
                    if isinstance(message, AIMessage):
                        # Check if it's an intermediate message (tool call) or final answer chunk
                        if message.tool_calls:
                            # Tool call requested by the model (won't print content yet)
                            pass  # Or log if needed: print(f"DEBUG: Tool call requested: {message.tool_calls}")
                        elif message.content and isinstance(
                            message.content, str
                        ):  # Check content is a string
                            # Append and print final response chunks from AIMessage
                            content_chunk = message.content.encode(
                                "utf-8", "replace"
                            ).decode("utf-8")
                            if content_chunk:  # Avoid appending/printing empty strings
                                accumulated_text.append(content_chunk)
                                print(content_chunk, end="", flush=True)

                    elif isinstance(message, ToolMessage):
                        # Result of a tool execution
                        tool_info = f"Tool Used: {message.name}\nResult: {message.content}\n---------------------"
                        print(
                            f"\n[Tool Execution Result: {message.name}]"
                        )  # Indicate tool use clearly
                        # print(message.content) # Optionally print the full tool result
                        accumulated_tool_info.append(tool_info)
        return None  # Callback doesn't need to return anything

    return callback_func, accumulated_text, accumulated_tool_info

async def process_query(
    agent, system_prompt, query: str, timeout: int = TIMEOUT_SECONDS
):
    
    # Set up streaming callback
    streaming_callback, accumulated_text, accumulated_tool_info = (
        get_streaming_callback()
    )
    initial_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=query),  # Assuming user_input holds the user's query
    ]

    # Define input for the agent/graph
    inputs = {"messages": initial_messages}

    # Configuration for the graph run
    config = RunnableConfig(
        recursion_limit=RECURSION_LIMIT,
        configurable={
            "thread_id": QUERY_THREAD_ID
        },  # Ensure unique thread for stateful execution
        # Add callbacks=[streaming_callback] if astream_log is used
    )

    if USE_ASTREAM_LOG:
        # Generate response using astream_log for richer streaming data
        # Using astream_log is often standard for LangGraph agents
        async for chunk in agent.astream_log(
            inputs, config=config, include_types=["llm", "tool"]
        ):
            # The callback function needs to process the structure of these chunks
            # print(f"DEBUG RAW CHUNK: {chunk}") # Debug raw output from astream_log
            streaming_callback(
                chunk.ops[0]["value"]
            )  # Pass the relevant part to callback

        # Wait for the streaming to complete (astream_log handles this implicitly)
    else:
        try:
            # Generate response using invoke instead of astream_log
            response = await agent.ainvoke(inputs, config=config)

            # Process the final response
            if isinstance(response, dict) and "messages" in response:
                final_message = response["messages"][-1]
                if isinstance(final_message, (AIMessage, ToolMessage)):
                    content = final_message.content
                    print(content, end="", flush=True)
                    accumulated_text.append(content)

                    if isinstance(
                        final_message, AIMessage
                    ) and final_message.additional_kwargs.get("tool_calls"):
                        tool_calls = final_message.additional_kwargs["tool_calls"]
                        for tool_call in tool_calls:
                            tool_info = (
                                f"\nTool Used: {tool_call.get('name', 'Unknown')}\n"
                            )
                            accumulated_tool_info.append(tool_info)

        except Exception as e:
            print(f"\nError during response generation: {str(e)}")
            return {"error": str(e)}

    # Return accumulated text and tool info
    full_response = (
        "".join(accumulated_text).strip()
        if accumulated_text
        else "AI did not produce a text response."
    )
    tool_info = "\n".join(accumulated_tool_info) if accumulated_tool_info else ""
    return {"output": full_response, "tool_calls": tool_info}

def process_input(chat_input: str) -> Optional[str]:
    cleaned_input = chat_input.strip()
    if cleaned_input.lower() in ["quit", "exit", "bye"]:
        return None
    return cleaned_input

def create_chat_model(temperature: float = 0.9, system_prompt: Optional[str] = None, mcp_tools: Optional[List]=None
)->ChatOllama:
    
    chat_model = ChatOllama(
        model="MFDoom/deepseek-r1-tool-calling:14b",
        temperature=temperature,
    )
    
    return create_react_agent(
            model=chat_model, tools = mcp_tools, checkpointer=MemorySaver()
            )

    
def load_mcp_server_list() -> Dict[str, Any]:
    try:
        with open("mcp_server.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        return config["mcpServers"]
    except FileNotFoundError:
        return {"mcpServers": {}}

async def initialize_mcp_client():
    mcp_server_list = load_mcp_server_list()

    try:
        client = MultiServerMCPClient(mcp_server_list)
        await client.__aenter__()
        tools = client.get_tools()
        return client, tools
    except Exception as e:
        print(f"Error in loading MCP list: {str(e)}")



async def amain(args):
    mcp_client = None

    print("\nMCP client 초기화")
    mcp_client, mcp_tools = await initialize_mcp_client()
    print(f"Loading list complete {len(mcp_tools)} MCP tools")

    for tool in mcp_tools:
        print(f"[Tool] {tool.name}")
    
    chat_model= create_chat_model(
        temperature=args.temp,
        mcp_tools=mcp_tools
    )

    #채팅 가보자고~
    print("\nStarting Ollama Chat")
    print("\nEnter 'quit', 'exit', or 'bye' to exit.")
    
    while True:
        chat_input = input("\nUser: ")

        cleaned_input = process_input(chat_input)
        if cleaned_input is None:
            print("\nNo Question? Go away~")
            break

        print("Agent:\n", end="", flush=True)
        
        response = await process_query(
            chat_model,
            args.system_prompt or MCP_CHAT_PROMPT,
            cleaned_input,
            timeout=TIMEOUT_SECONDS,
        )

        if (
                args.show_tools
                and "tool_calls" in response
                and response["tool_calls"].strip()
            ):
                print("\n--- Tool Activity ---")
                print(response["tool_calls"].strip())
                print("---------------------\n")




def sig_handler(signum, frame):
    print("\nProgram terminated!")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, sig_handler) # 프로그램 종료를 위한 시그널 핸들러 처리

    warnings.filterwarnings(
        "ignore", category=ResourceWarning, message="unclose.*<socket.socket.*>" 
    ) # 없애고 테스트 1
    
    loop = None # 이벤트 loop 초기화

    parser = argparse.ArgumentParser(
        description="Ollama Chat CLI with MCP Tools"
    )  # Updated description
    parser.add_argument(
        "--temp",
        type=float,
        default=0.9,
        help=f"Temperature value (0.0 ~ 1.0). Default: 0.9",
    )
    parser.add_argument(
        "--system-prompt",
        type=str,
        default=None,
        help="Custom base system prompt (Note: ReAct agent uses a specific format)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT_SECONDS,
        help=f"Response generation timeout (seconds). Default: {TIMEOUT_SECONDS}",
    )
    parser.add_argument(
        "--show-tools", action="store_true", help="Show tool execution information"
    )
    args = parser.parse_args()

    #LLM 질문 온도 설정 확인
    if not 0.0 <= args.temp <= 1.0:
        print(
               f"Warning: Temperature {args.temp} is outside the typical range [0.0, 1.0]. Using default: 0.9"
           )
        args.temp = 0.9
    
    nest_asyncio.apply()
    asyncio.run(amain(args))

if __name__ == "__main__":
    main()




