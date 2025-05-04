from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    "Weather", #서버 이름
    instructions="You are a weather assistant that can answer questions about the weather in a given location.",  # LLM이 이 툴이 뭔지 확인할때 사용하는 내용
    host="0.0.0.0",
    port=8005,
    settings={"initialization_timeout": 10.0}
)


@mcp.tool()
async def get_weather(location: str) -> str: #실제 호출되서 사용되는 Tool이며, 비즈니스 로직이 여기 들어감
    """
    Get current weather information for the specified location.

    This function simulates a weather service by returning a fixed response.
    In a production environment, this would connect to a real weather API.

    Args:
        location (str): The name of the location (city, region, etc.) to get weather for

    Returns:
        str: A string containing the weather information for the specified location
    """
    # Return a mock weather response
    # In a real implementation, this would call a weather API
    print(f"\n[DEBUG] MCP: get_weather called: {location}\n")
    return f"It's sunny in the morning, cloudy in the afternoon and snowing in the evening in {location}"


if __name__ == "__main__":
    # Start the MCP server with stdio transport
    # stdio transport allows the server to communicate with clients
    # through standard input/output streams, making it suitable for
    # local development and testing
    mcp.run(transport="stdio")
