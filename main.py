# --- main.py (Gradio + Tool Display - SyntaxError 재수정) ---
import gradio as gr
import asyncio
import signal
import sys
import warnings
import traceback
import re
from mcp_client import MCPClient
from mcp_agent import MCPAgent

# --- 전역 변수 및 상태 플래그 ---
mcp_client = None
agent = None
initialization_error_message = None
is_initializing = False
initialization_complete = False
available_tool_names = []

# --- 신호 처리기 ---
def sig_handler(signum, frame):
    print("\n[Main] SIGINT received, terminating application...")
    sys.exit(0)

# --- 비동기 에이전트 초기화 (백그라운드 작업용) ---
async def initialize_agent_task():
    """MCP 클라이언트와 MCPAgent를 초기화하는 백그라운드 태스크."""
    global mcp_client, agent, initialization_error_message, is_initializing, initialization_complete, available_tool_names

    if is_initializing or initialization_complete:
        status = "already running" if is_initializing else "already complete"
        print(f"[Initialization Task] Initialization {status}, skipping.")
        return

    is_initializing = True
    initialization_error_message = None
    available_tool_names = []
    print("\n[Initialization Task] Starting agent initialization in background...")

    try:
        print("[Initialization Task] 1. Initializing MCP client...")
        local_mcp_client = MCPClient()
        await local_mcp_client.initialize()
        mcp_client = local_mcp_client

        if mcp_client.tools:
            available_tool_names = sorted([tool.name for tool in mcp_client.tools])
            print(f"[Initialization Task] Found tools: {', '.join(available_tool_names)}")
        else:
            print("[Initialization Task] Warning: No MCP tools loaded.")
            available_tool_names = []

        print(f"[Initialization Task] 1. MCP client initialized.")

        default_temp = 0.9
        default_system_prompt = "You are a helpful AI assistant capable of using tools."
        print("[Initialization Task] 2. Initializing MCPAgent...")
        local_agent = MCPAgent(
            temperature=default_temp, system_prompt=default_system_prompt, tools=mcp_client.tools
        )
        agent = local_agent
        print("[Initialization Task] 2. MCPAgent initialized successfully.")
        initialization_error_message = None

    except Exception as e:
        initialization_error_message = f"Agent initialization failed: {str(e)}"
        print(f"\n[Error][Initialization Task] {initialization_error_message}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        agent = None
        available_tool_names = []

    finally:
        is_initializing = False
        initialization_complete = True
        status = "successfully" if agent else "with errors"
        print(f"[Initialization Task] Background initialization attempt finished {status}.")


# --- Gradio 인터페이스 콜백 함수 ---
async def chat_interface(user_input: str, show_tool_activity: bool) -> tuple[str, str, str]:
    """Gradio 인터페이스 콜백. 에이전트 응답, 전체 툴 로그, 마지막 사용 툴 이름을 반환합니다."""
    # 이 함수 내에서는 전역 변수를 읽기만 하므로 global 선언 불필요
    # 단, 값을 변경해야 한다면 global 필요

    if not initialization_complete:
         if is_initializing:
              wait_message = "⏳ Agent is still initializing... Please wait."
              # print(f"[Interface] Request while initializing.") # 로그 간소화
              await asyncio.sleep(0.5) # 짧게 대기
              return wait_message, "", "N/A"
         else:
              error_msg = initialization_error_message or "not started/failed"
              print(f"[Interface] Error: Init not complete/running. Error: {error_msg}")
              return f"⚠️ Agent not ready ({error_msg}). Reload UI or check logs.", "", "N/A"

    if initialization_error_message:
        print(f"[Interface] Returning init error: {initialization_error_message}")
        return f"⚠️ Agent Init Error: {initialization_error_message}. Check logs.", "", "Error"

    if agent is None:
        print("[Interface] Error: Agent is None (unexpected).")
        return "⚠️ Error: Agent unavailable after initialization.", "", "Error"

    if not user_input or user_input.strip() == "":
        return "Please enter a message.", "", "None"

    print(f"\n[User Input] Received: '{user_input}'")
    print("[Agent] Processing query...")
    last_tool_name_str = "None"

    try:
        response = await agent.process_query(user_input)
        output_text = response.get("output", "[Error] No output.")
        tool_calls_text = response.get("tool_calls", "")
        error_text = response.get("error", "")

        if error_text:
             output_text = f"[Agent Error] {error_text}"
             print(f"[Agent Error] {error_text}", file=sys.stderr)
             last_tool_name_str = "Error"

        print(f"[Agent Output] Sending response.")

        if tool_calls_text:
            found_tools = re.findall(r"Tool Used:\s*([a-zA-Z0-9_]+)", tool_calls_text)
            if found_tools:
                last_tool_name_str = ", ".join(list(dict.fromkeys(found_tools)))
                # print(f"[Interface] Tools used: {last_tool_name_str}") # 로그 간소화

        formatted_tool_calls = ""
        if show_tool_activity and tool_calls_text:
            formatted_tool_calls = (
                "--- Tool Activity ---\n" f"{tool_calls_text.strip()}\n" "---------------------"
            )

        return output_text, formatted_tool_calls, last_tool_name_str

    except Exception as e:
        error_message = f"Critical Error during query processing: {str(e)}"
        print(f"[Error] {error_message}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return f"⚠️ Internal Error: {error_message}", "", "Error"

# --- Gradio 인터페이스 UI 설정 ---
def create_gradio_interface() -> gr.Blocks:
    """Gradio 웹 인터페이스 UI를 생성하고 반환합니다."""
    print("[Gradio] Creating Gradio interface UI...")
    theme = gr.themes.Soft(primary_hue="blue", secondary_hue="sky")

    with gr.Blocks(title="Chat with MCP Tools", theme=theme, analytics_enabled=False) as demo:
        gr.Markdown("# 🤖 Chat with MCP Tools")
        with gr.Row():
            with gr.Column(scale=3, min_width=250):
                initialization_status = gr.Textbox("Agent Status: Loading UI...", label="Status", interactive=False, max_lines=1)
                available_tools_display = gr.Markdown("Loading available tools...", label="Available Tools")
                user_input = gr.Textbox(label="Your Message", placeholder="Ask about weather, YouTube, etc...", lines=4)
                show_tools_checkbox = gr.Checkbox(label="Show Full Tool Activity Log", value=False)
                with gr.Row():
                     submit_button = gr.Button("▶️ Send", variant="primary", scale=2)
                     clear_button = gr.Button("Clear", variant="secondary", scale=1)
            with gr.Column(scale=7, min_width=450):
                chatbot_output = gr.Textbox(label="Agent Response", lines=15, interactive=False, show_copy_button=True)
                last_used_tool_display = gr.Textbox(label="Tool Used (Current Response)", value="N/A", interactive=False, max_lines=1)
                tool_output = gr.Textbox(label="Full Tool Activity Log", lines=8, interactive=False, visible=False, show_copy_button=True)

        show_tools_checkbox.change(
            fn=lambda is_checked: gr.update(visible=is_checked), inputs=show_tools_checkbox, outputs=tool_output, queue=False
        )

        trigger_inputs = [user_input, show_tools_checkbox]
        trigger_outputs = [chatbot_output, tool_output, last_used_tool_display]

        submit_button.click(
            fn=chat_interface, inputs=trigger_inputs, outputs=trigger_outputs, api_name="chat"
        ).then(lambda: gr.update(value=""), inputs=None, outputs=user_input, queue=False)

        user_input.submit(
            fn=chat_interface, inputs=trigger_inputs, outputs=trigger_outputs, api_name="chat_submit"
        ).then(lambda: gr.update(value=""), inputs=None, outputs=user_input, queue=False)

        clear_button.click(
            fn=lambda: ("", "", gr.update(value=""), "N/A"), # 출력 4개 초기화
            inputs=None, outputs=[user_input, chatbot_output, tool_output, last_used_tool_display], queue=False
        )

        # --- Initialization Trigger & Status Update via demo.load ---
        async def run_initialization_and_update_status():
            """Triggers background initialization if needed and returns current status."""
            # ★★★ global 선언이 함수의 가장 처음에 위치 ★★★
            global is_initializing, initialization_complete, initialization_error_message, agent, available_tool_names

            # 이제 지역 변수 할당 및 전역 변수 사용 가능
            current_status = "❓ Status Unknown"
            available_tools_md = "Waiting for initialization..."
            should_trigger_init = False

            # 상태 확인 및 메시지/트리거 결정
            if not initialization_complete and not is_initializing:
                 print("[Gradio Load] Conditions met: Triggering initialization.")
                 should_trigger_init = True
                 current_status = "⏳ Agent Status: Initialization starting..."
                 available_tools_md = "Initializing..."
            elif is_initializing:
                 current_status = "⏳ Agent Status: Initialization in progress..."
                 available_tools_md = "Initializing..."
            elif initialization_error_message:
                 current_status = f"⚠️ Agent Status: Error - {initialization_error_message}"
                 available_tools_md = "**Error during initialization!**"
            elif agent:
                 current_status = "✅ Agent Status: Ready"
                 if available_tool_names:
                      tool_list_items = "\n".join([f"- `{name}`" for name in available_tool_names])
                      available_tools_md = f"**Detected Tools:**\n{tool_list_items}"
                 else:
                      available_tools_md = "No tools detected or loaded."
            else:
                 current_status = "❓ Agent Status: Init finished, but agent not ready."
                 available_tools_md = "Initialization might have failed."

            # 백그라운드 초기화 실행 (필요한 경우)
            if should_trigger_init:
                 print("[Gradio Load] Creating background initialization task...")
                 try:
                      # 현재 실행 중인 이벤트 루프 가져오기 (Gradio/Uvicorn이 제공)
                      loop = asyncio.get_running_loop()
                      # 해당 루프에서 백그라운드 태스크 생성
                      loop.create_task(initialize_agent_task())
                      print("[Gradio Load] Background initialization task created.")
                 except RuntimeError as loop_err:
                      # get_running_loop 실패 시 (이론상 Gradio 환경에선 발생 어려움)
                      print(f"[Error] Could not get running loop to create task: {loop_err}", file=sys.stderr)
                      current_status = f"⚠️ Agent Status: Error getting loop - {loop_err}"
                      available_tools_md = "**Error getting event loop!**"
                      # 전역 상태 업데이트
                      initialization_error_message = f"Failed to get loop: {loop_err}"
                      is_initializing = False
                      initialization_complete = True
                 except Exception as task_e:
                      # 태스크 생성 자체 실패 시
                      print(f"[Error] Failed to create initialization task: {task_e}", file=sys.stderr)
                      current_status = f"⚠️ Agent Status: Error creating init task - {task_e}"
                      available_tools_md = f"**Error creating init task!**"
                      initialization_error_message = f"Failed to create init task: {task_e}"
                      is_initializing = False
                      initialization_complete = True

            # 상태 메시지와 사용 가능 도구 목록 Markdown 반환
            return current_status, available_tools_md

        # UI 로드 시 run_initialization_and_update_status 함수 한 번 실행
        demo.load(
            fn=run_initialization_and_update_status,
            inputs=[],
            outputs=[initialization_status, available_tools_display]
        )

    print("[Gradio] Gradio interface UI created successfully.")
    return demo

# --- 메인 실행 로직 ---
if __name__ == "__main__":
    print("[Main] Application starting...")
    warnings.filterwarnings("ignore", category=UserWarning, module='gradio')
    warnings.filterwarnings("ignore", category=FutureWarning, module='gradio')
    warnings.filterwarnings("ignore", category=ResourceWarning)
    signal.signal(signal.SIGINT, sig_handler)

    print("[Main] Creating Gradio interface (Agent will initialize after UI loads)...")
    try:
        demo = create_gradio_interface()

        SERVER_NAME = "127.0.0.1"
        SERVER_PORT = 8100
        print(f"\n[Main] Launching Gradio server...")
        print(f"      Access the interface at: http://{SERVER_NAME}:{SERVER_PORT}")

        demo.launch(
            server_name=SERVER_NAME,
            server_port=SERVER_PORT,
            inbrowser=True,
        )

    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt received. Exiting.")
    except Exception as e:
        print(f"\n[Error] Failed to create or launch Gradio: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    print("\n[Main] Gradio application has closed.")
    print("[Main] Application finished.")