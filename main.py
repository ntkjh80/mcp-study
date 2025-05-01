import argparse
import asyncio
import signal
import sys
import warnings
from mcp_client import MCPClient
from mcp_agent import MCPAgent

def sig_handler(signum, frame):
    print("\nProgram terminated!")
    sys.exit(0)

async def amain(args):
    print("\nInitializing MCP client")
    mcp_client = MCPClient()
    await mcp_client.initialize()
    
    print(f"\nLoaded {len(mcp_client.tools)} MCP tools")
    for tool in mcp_client.tools:
        print(f"[Tool] {tool.name}")

    agent = MCPAgent(
        temperature=args.temp,
        system_prompt=args.system_prompt,
        tools=mcp_client.tools
    )

    print("\nStarting Ollama Chat")
    print("Enter 'quit', 'exit', or 'bye' to exit.")
    while True:
        chat_input = input("\nUser: ").strip()
        if chat_input.lower() in ["quit", "exit", "bye"]:
            print("\nGoodbye!")
            break
            
        print("Agent:\n", end="", flush=True)
        response = await agent.process_query(chat_input)
        
        if args.show_tools and response.get('tool_calls'):
            print("\n--- Tool Activity ---")
            print(response['tool_calls'].strip())
            print("---------------------\n")

def main():
    signal.signal(signal.SIGINT, sig_handler)
    warnings.filterwarnings("ignore", category=ResourceWarning)
    
    parser = argparse.ArgumentParser(description="Ollama Chat CLI with MCP Tools")
    parser.add_argument("--temp", type=float, default=0.9, help="Temperature value (0.0 ~ 1.0)")
    parser.add_argument("--system-prompt", type=str, default=None)
    parser.add_argument("--timeout", type=int, default=300, help="Response timeout in seconds")
    parser.add_argument("--show-tools", action="store_true")
    
    args = parser.parse_args()
    asyncio.run(amain(args))

if __name__ == "__main__":
    main()
