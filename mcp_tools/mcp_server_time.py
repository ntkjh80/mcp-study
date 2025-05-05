# -*- coding: utf-8 -*-
# 필요한 라이브러리 임포트
from mcp.server.fastmcp import FastMCP  # MCP 서버 생성을 위한 클래스
from datetime import datetime          # 현재 시간 및 날짜 관련 작업을 위한 모듈
import pytz                            # 시간대(Timezone) 관련 처리를 위한 라이브러리 (pip install pytz 필요)
from typing import Optional            # 타입 힌트(Optional)를 사용하기 위함

# --- FastMCP 서버 초기화 ---
# FastMCP 인스턴스를 생성하고 서버 설정을 구성합니다.
mcp = FastMCP(
    name="TimeService",  # MCP 서버의 고유 이름 (mcp_server.json 등에서 참조될 수 있음)
    instructions="다른 시간대의 현재 시간을 알려줄 수 있는 시간 도우미입니다. 시간대를 입력하면 해당 시간대의 현재 시간을 알려줍니다.", # LLM에게 이 도구의 사용법과 기능을 설명하는 지침
    host="0.0.0.0",      # 서버가 리스닝할 호스트 주소 (0.0.0.0은 모든 네트워크 인터페이스에서 접속 허용)
                        # stdio 전송 방식 사용 시 이 설정은 직접적인 영향을 주지 않을 수 있습니다.
    port=8005,          # 서버가 사용할 포트 번호 (stdio 전송 방식 사용 시 의미 없음)
    # settings={}       # 필요시 추가 설정 (예: 타임아웃, 로그 레벨 등)
)

# --- MCP 도구 정의 ---
# '@mcp.tool()' 데코레이터를 사용하여 이 함수를 MCP 도구로 등록합니다.
# 함수 이름('get_current_time')이 LLM이 호출할 도구의 이름(action)이 됩니다.
@mcp.tool()
async def get_current_time(timezone: Optional[str] = "Asia/Seoul") -> str:
    """
    지정된 시간대(timezone)의 현재 시간 정보를 가져옵니다. (한국어 설명)

    이 함수는 요청된 시간대의 현재 시스템 시간을 반환합니다.
    시간대 문자열은 IANA 시간대 데이터베이스 형식(예: 'America/New_York', 'Europe/London')을 따릅니다.

    Args:
        timezone (str, 선택 사항): 현재 시간을 가져올 시간대 문자열.
                                    입력하지 않으면 기본값으로 "Asia/Seoul" (서울 시간)이 사용됩니다.

    Returns:
        str: 지정된 시간대의 현재 시간 정보가 포함된 문자열.
             오류 발생 시 오류 메시지 문자열을 반환합니다.
    """
    # 입력된 timezone 값을 로그로 출력 (디버깅 목적)
    print(f"[TimeService] Received request for timezone: {timezone}")

    try:
        # 1. pytz 라이브러리를 사용하여 유효한 시간대 객체(tz) 가져오기
        #    잘못된 시간대 문자열이 입력되면 UnknownTimeZoneError 발생
        tz = pytz.timezone(timezone)

        # 2. datetime.now()에 시간대 객체(tz)를 전달하여 해당 시간대의 현재 시간 얻기
        current_time = datetime.now(tz)

        # 3. 얻어온 시간 정보를 지정된 형식의 문자열로 포맷팅
        #    %Y: 년(4자리), %m: 월, %d: 일, %H: 시(24시간제), %M: 분, %S: 초, %Z: 시간대 이름 약어
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")

        # 4. 성공적으로 시간을 가져왔음을 로그로 남기고 결과 문자열 반환
        result_str = f"{timezone}의 현재 시간은 {formatted_time} 입니다."
        print(f"[TimeService] Returning: {result_str}")
        return result_str

    except pytz.exceptions.UnknownTimeZoneError:
        # 사용자가 잘못된 시간대 이름을 입력했을 경우 처리
        error_msg = f"오류: 알 수 없는 시간대 '{timezone}' 입니다. 유효한 시간대 이름을 입력해주세요 (예: 'America/New_York')."
        print(f"[TimeService] Error: {error_msg}")
        return error_msg
    except Exception as e:
        # 그 외 예상치 못한 오류가 발생했을 경우 처리
        error_msg = f"시간 정보를 가져오는 중 오류가 발생했습니다: {str(e)}"
        # 상세 오류 로그를 남기고 싶다면 traceback 사용 가능
        # import traceback
        # traceback.print_exc()
        print(f"[TimeService] Error: {error_msg}")
        return error_msg


# --- 메인 실행 블록 ---
# 이 스크립트 파일이 직접 실행될 때 아래 코드가 동작합니다.
# (예: python your_time_service_script.py 또는 mcp_server.json의 command 설정)
if __name__ == "__main__":
    print("[TimeService] 시간 서비스 MCP 서버 시작 중 (stdio 전송 방식)...")
    # MCP 서버 실행
    # transport="stdio": 클라이언트(MultiServerMCPClient)와 표준 입출력(stdin/stdout) 스트림을 통해 통신합니다.
    #                    별도의 네트워크 포트를 사용하지 않으므로 로컬 개발 및 테스트에 적합합니다.
    mcp.run(transport="stdio")
    # 서버가 정상적으로 종료될 때 아래 메시지가 출력됩니다.
    print("[TimeService] 시간 서비스 MCP 서버가 중지되었습니다.")