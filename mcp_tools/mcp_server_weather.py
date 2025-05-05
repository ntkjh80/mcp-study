# 필요한 라이브러리 임포트
from mcp.server.fastmcp import FastMCP  # MCP 서버 생성을 위한 클래스
import os  # 경로 관련 작업 (예시 추가)
import asyncio # 비동기 작업

# --- 실제 날씨 API 연동을 위한 준비 (예시) ---
# 실제 구현 시 주석 해제 및 API 키 설정 필요
# import httpx # 비동기 HTTP 요청 라이브러리 (requests 대체)
# WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY") # 환경 변수에서 API 키 로드
# WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"

# --- FastMCP 서버 인스턴스 생성 ---
# 서버 이름은 mcp_server.json의 키와 일치시키는 것이 관리상 용이할 수 있음 (필수는 아님)
mcp = FastMCP(
    name="Weather", # 서버의 고유 이름 (클라이언트가 이 이름으로 도구를 식별)
    instructions="주어진 위치의 현재 날씨 정보를 제공하는 도구입니다. 위치 이름을 입력하세요.", # LLM에게 이 도구의 용도를 설명하는 지침
    host="0.0.0.0", # 서버가 리스닝할 호스트 주소 (0.0.0.0은 모든 인터페이스에서 접속 허용)
    port=8005,      # 서버가 사용할 포트 번호 (mcp_server.json 설정과 무관, stdio 사용 시 의미 없음)
    settings={
        "initialization_timeout": 10.0, # 초기화 타임아웃 설정 (초) - stdio에서는 큰 의미 없을 수 있음
        # "log_level": "debug" # 필요 시 로그 레벨 설정
    }
)

# --- MCP 도구 정의 ---
@mcp.tool() # 이 함수를 MCP 도구로 등록 (함수 이름이 도구 이름이 됨: 'get_weather')
async def get_weather(location: str) -> str: # 실제 호출되어 사용될 비동기 함수
    """
    지정된 위치의 현재 날씨 정보를 가져옵니다.

    Args:
        location (str): 날씨 정보를 조회할 위치(도시 이름 등). 영문으로 받는 것이 API 호출에 유리할 수 있음.

    Returns:
        str: 지정된 위치의 현재 날씨 정보 요약 문자열. 오류 발생 시 오류 메시지 반환.

    --- 실제 구현 노트 ---
    현재는 고정된 모의(mock) 응답을 반환합니다.
    실제 날씨 정보를 제공하려면 다음 단계를 구현해야 합니다:
    1. OpenWeatherMap, AccuWeather 등 날씨 API 서비스 가입 및 API 키 발급.
    2. `httpx` (비동기) 또는 `requests` (동기) 라이브러리를 사용하여 API 호출.
       - 위치 이름(location)을 사용하여 API에 쿼리 (필요시 위경도 변환).
       - API 키 인증 포함.
    3. API 응답 (주로 JSON 형식)을 파싱하여 필요한 날씨 정보(온도, 상태, 습도 등) 추출.
    4. 추출된 정보를 자연스러운 문장으로 조합하여 반환.
    5. API 호출 실패, 잘못된 위치 등의 오류 처리 로직 추가.
    """
    print(f"\n[Weather Server DEBUG] MCP Tool 'get_weather' called with location: {location}\n")

    # === 모의 응답 (Mock Response) ===
    # 실제 구현 시 이 부분을 API 호출 및 결과 처리 로직으로 대체해야 합니다.
    mock_responses = {
        "seoul": "서울의 현재 날씨는 맑음, 기온은 25도입니다.",
        "suwon": "수원의 현재 날씨는 구름 조금, 기온은 23도입니다.",
        "london": "런던의 현재 날씨는 비, 기온은 15도입니다."
    }
    # 입력된 위치(소문자 변환)에 해당하는 모의 응답 반환, 없으면 기본 메시지
    return mock_responses.get(location.lower(), f"{location}의 날씨 정보를 찾을 수 없습니다. 도시 이름을 확인해주세요.")

    # === 실제 API 호출 구현 예시 (httpx 사용, 주석 처리됨) ===
    # if not WEATHER_API_KEY:
    #     return "오류: 날씨 API 키가 설정되지 않았습니다."
    #
    # params = {
    #     'q': location,
    #     'appid': WEATHER_API_KEY,
    #     'units': 'metric', # 섭씨 온도 사용
    #     'lang': 'kr'       # 한국어 설명 요청
    # }
    # try:
    #     async with httpx.AsyncClient() as client:
    #         response = await client.get(WEATHER_API_URL, params=params)
    #         response.raise_for_status() # HTTP 오류 발생 시 예외 발생
    #         data = response.json()
    #
    #         # 필요한 정보 추출
    #         weather_description = data['weather'][0]['description']
    #         temperature = data['main']['temp']
    #         feels_like = data['main']['feels_like']
    #         humidity = data['main']['humidity']
    #
    #         # 결과 문자열 생성
    #         result = (f"{location}의 현재 날씨: {weather_description}. "
    #                   f"기온은 {temperature}°C (체감온도 {feels_like}°C), 습도는 {humidity}% 입니다.")
    #         return result
    #
    # except httpx.HTTPStatusError as e:
    #     if e.response.status_code == 404:
    #         return f"오류: '{location}' 위치를 찾을 수 없습니다."
    #     else:
    #         return f"오류: 날씨 정보를 가져오는 중 오류 발생 (HTTP {e.response.status_code})"
    # except httpx.RequestError as e:
    #     return f"오류: 날씨 API 요청 실패 - {e}"
    # except Exception as e:
    #     return f"오류: 날씨 정보 처리 중 예기치 못한 오류 발생 - {e}"


# --- 스크립트가 직접 실행될 때 서버 시작 ---
if __name__ == "__main__":
    # 이 파일이 직접 실행될 때 (예: python mcp_server_weather.py)
    # `mcp_server.json`의 "command" 설정에 의해 실행될 때 해당됩니다.
    print("[Weather Server] Starting Weather MCP server using stdio transport...")
    print(f"[Weather Server] Process ID: {os.getpid()}")
    # MCP 서버 실행
    # transport="stdio": 표준 입출력(stdin/stdout)을 통해 클라이언트(MultiServerMCPClient)와 통신.
    #                    별도의 네트워크 포트를 열지 않음.
    #                    로컬 환경에서 프로세스로 직접 실행될 때 주로 사용.
    mcp.run(transport="stdio")
    # 서버 종료 시 아래 메시지 출력 (정상 종료 시)
    print("[Weather Server] Weather MCP server stopped.")