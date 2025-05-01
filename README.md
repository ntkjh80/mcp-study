# MCP 동작을 이해하기 위한 코드 작성 예제

## 시스템 동작
- A[main.py] - 초기화 -> B[mcp_client.py] 
- A - 생성 -> C[mcp_agent.py]    
- B - Tool 등록 -> C
- C - 실행 결과 -> A

## 설치법
0. ollama 설치
    <br/> https://ollama.com/ 
1. Source 다운로드
    <br/> git clone git@github.com:ntkjh80/mcp-study.git
2. uv 설치
    <br/> # Using pip: pip install uv
    <br/> # Using curl: curl -LsSf https://astral.sh/uv/install.sh | sh
3. uv 실행
    <br/> uv venv
    <br/> source .venv/bin/activate
    <br/> uv sync
4. LLM 모델 다운로드 (이론상 tool calling 기능만 되면 다 가능함)
    <br/> ollama pull MFDoom/deepseek-r1-tool-calling:14b
5. 실행
    <br/> uv run main.py

## 참고 사이트
- https://github.com/godstale/ollama-mcp-agent/tree/main
- https://hellollama.net/ollamamcp-agent-%eb%b9%84%ec%9a%a9-%ea%b1%b1%ec%a0%95%ec%97%86%eb%8a%94-ai-agent-1/
