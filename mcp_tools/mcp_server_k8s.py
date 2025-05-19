# mcp_study/mcp_tools/mcp_server_k8s.py 수정 제안
import sys
import os
import asyncio # asyncio 임포트 추가
import importlib # 이전 제안에서 추가

# 프로젝트 루트 경로 설정 (기존 로직 유지)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 생성된 공유 인스턴스를 가져옵니다.
from mcp_tools.k8s_mcp_instance import mcp_instance as mcp

print(f"[k8s-pilot Server DEBUG] Using shared MCP instance from k8s_mcp_instance.py with ID: {id(mcp)}")

def load_modules(): # 이 함수는 동기적으로 유지
    print("[k8s-pilot Server DEBUG] Attempting to load modules...")
    modules_to_load = [
        "resources.contexts", "tools.cluster", "tools.configmap", "tools.daemonset",
        "tools.deployment", "tools.ingress", "tools.namespace", "tools.node",
        "tools.pod", "tools.pv", "tools.pvc", "tools.replicaset", "tools.role",
        "tools.secret", "tools.service", "tools.serviceaccount", "tools.statefulset"
    ]
    for module_name in modules_to_load:
        try:
            print(f"Importing {module_name}...")
            importlib.import_module(module_name) # importlib 사용 권장
            print(f"Imported {module_name} successfully.")
        except Exception as e:
            print(f"!!! Failed to import {module_name}: {type(e).__name__} - {e}")
            import traceback
            traceback.print_exc()
    print("[k8s-pilot Server DEBUG] Modules import process completed.")

async def main_async(): # 비동기 메인 함수 생성
    # 모듈 로드 함수 호출
    load_modules()

    print(f"[k8s-pilot Server DEBUG] === MCP Instance Tool Inspection (ID: {id(mcp)}) ===")
    try:
        # mcp.list_tools()가 코루틴이므로 await 사용
        registered_tools = await mcp.list_tools() # <<<--- await 추가!

        # 디버깅을 위해 반환된 객체와 타입 출력
        print(f"[k8s-pilot Server DEBUG] Value returned by await mcp.list_tools(): {registered_tools}")
        print(f"[k8s-pilot Server DEBUG] Type of value returned by await mcp.list_tools(): {type(registered_tools)}")

        if registered_tools:
            # list_tools()가 실제 도구 객체의 리스트를 반환하는지, 아니면 다른 구조인지 여기서 확인 필요
            # 예를 들어, langchain tool 객체의 리스트일 수 있음
            if isinstance(registered_tools, list):
                tool_names = []
                for tool_obj in registered_tools:
                    if hasattr(tool_obj, 'name'): # Langchain Tool 객체는 보통 'name' 속성을 가짐
                        tool_names.append(tool_obj.name)
                    elif isinstance(tool_obj, dict) and 'name' in tool_obj: # 또는 딕셔너리 리스트일 수도 있음
                        tool_names.append(tool_obj['name'])
                    else:
                        tool_names.append(str(tool_obj)) # 최후의 수단으로 문자열 변환

                if tool_names:
                    print(f"[k8s-pilot Server DEBUG] SUCCESS: {len(tool_names)} tools registered in MCP instance (ID: {id(mcp)}): {sorted(tool_names)}")
                else:
                    print(f"[k8s-pilot Server DEBUG] INFO: {len(registered_tools)} tool objects found, but couldn't extract names. Objects: {registered_tools}")

            else: # 리스트가 아닌 다른 타입일 경우 (예: 단일 객체, 딕셔너리 등)
                print(f"[k8s-pilot Server DEBUG] INFO: mcp.list_tools() returned a non-list type: {type(registered_tools)}. Value: {registered_tools}")

        else: # None 이거나 빈 컨테이너일 경우
            print(f"[k8s-pilot Server DEBUG] WARNING: await mcp.list_tools() returned no tools or an empty result for MCP instance (ID: {id(mcp)}).")

    except Exception as e:
        print(f"[k8s-pilot Server DEBUG] ERROR during await mcp.list_tools() or tool name extraction: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()

    # 서버 실행
    print(f"[k8s-pilot Server] Starting k8s-pilot MCP server using stdio transport... (Instance ID: {id(mcp)})")
    # mcp.run() 자체가 이미 비동기 처리를 할 수 있으므로, main_async 내에서 호출하거나,
    # run()이 동기 블로킹 함수라면 asyncio.run() 바깥에서 호출해야 할 수 있습니다.
    # FastMCP의 run 메서드가 어떻게 동작하는지 확인 필요.
    # 만약 mcp.run()이 내부적으로 asyncio 루프를 관리한다면, 아래처럼 직접 호출해도 됩니다.
    # 혹은 mcp.run_stdio_async() 와 같은 명시적인 비동기 실행 함수가 있을 수 있습니다.
    # 현재는 mcp.run()이 stdio 전송 방식에서 동기적으로 서버를 실행한다고 가정합니다.
    # 따라서, 도구 확인 후 실제 서버 실행은 __main__ 블록에서 하는 것이 더 안전할 수 있습니다.
    # 이 예제에서는 우선 main_async 내에 두겠습니다.

    # FastMCP 의 run 메소드가 동기 블로킹 함수일 가능성이 높습니다.
    # 만약 그렇다면, 아래의 mcp.run()은 main_async 함수의 마지막에 위치하거나,
    # 혹은 asyncio.run(main_async()) 호출 이후에 동기적으로 호출되어야 합니다.
    # 이 부분은 FastMCP 라이브러리의 동작 방식에 따라 조정이 필요합니다.
    # 우선은 도구 목록 확인 후 서버를 시작하는 로직으로 구성합니다.
    # mcp.run(transport="stdio") # 이 라인은 아래 if __name__ == "__main__": 블록으로 이동 고려


if __name__ == "__main__":
    # asyncio.run()을 사용하여 비동기 메인 함수 실행
    # asyncio.run(main_async()) # 도구 확인까지만 하고 서버 실행은 아래에서

    # 모듈 로드 (동기)
    load_modules()

# mcp_study/mcp_tools/mcp_server_k8s.py 의 __main__ 블록 수정 제안

if __name__ == "__main__":
    # 모듈 로드는 이미 스크립트 상단에서 수행됨
    print(f"[k8s-pilot Server __main__] Process ID: {os.getpid()}") # 프로세스 ID 확인
    print(f"[k8s-pilot Server __main__] All modules loaded. Checking tools before starting server (Instance ID: {id(mcp)})...")

    # 도구 확인 (이전과 동일한 비동기 로직)
    async def check_tools_before_run():
        try:
            registered_tools = await mcp.list_tools()
            if registered_tools and isinstance(registered_tools, list):
                tool_names = [getattr(tool, 'name', str(tool)) for tool in registered_tools]
                print(f"[k8s-pilot Server __main__] SUCCESS: {len(tool_names)} tools confirmed before run: {sorted(tool_names)}")
            else:
                print(f"[k8s-pilot Server __main__] WARNING: No tools or non-list returned by await mcp.list_tools() before run.")
        except Exception as e:
            print(f"[k8s-pilot Server __main__] ERROR checking tools before run: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(check_tools_before_run())

    print(f"[k8s-pilot Server __main__] Proceeding to call mcp.run(transport='stdio')...")
    try:
        mcp.run(transport="stdio") # 서버 실행
    except Exception as e:
        print(f"[k8s-pilot Server __main__] EXCEPTION during mcp.run(): {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc() # mcp.run() 자체에서 예외가 발생하면 출력
    finally:
        print("[k8s-pilot Server __main__] mcp.run() finished or exited.")