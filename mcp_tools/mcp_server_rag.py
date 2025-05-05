# -*- coding: utf-8 -*-
# 필요한 라이브러리 임포트
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings # 로컬 모델 사용
from mcp.server.fastmcp import FastMCP
# from dotenv import load_dotenv # 로컬 모델 사용 시 API 키 로드는 불필요
from typing import Any, List, Optional # Optional 추가
from langchain_core.documents import Document
# from langchain_core.vectorstores import VectorStoreRetriever # 구체적인 타입 힌트
import os
import traceback
import asyncio # 비동기 락 사용 

# --- 전역 변수 ---
# 생성된 Retriever 인스턴스를 저장 (Lazy Initialization)
_retriever_instance: Optional[Any] = None # Any 대신 VectorStoreRetriever 사용 가능
# Retriever 초기화 중 발생한 오류 저장
_retriever_initialization_error: Optional[Exception] = None
# 초기화 진행 중 동시 접근을 막기 위한 비동기 락 
_init_lock = asyncio.Lock()

# --- Retriever 생성 및 초기화 함수 ---
# 서버 시작 시 또는 첫 호출 시 한 번만 실행되어 Retriever를 생성하고 캐싱합니다.
def _build_and_initialize_retriever() -> Optional[Any]:
    """
    실제 Retriever 객체를 생성하고 초기화하는 내부 함수. (한국어 설명)
    성공 시 Retriever 객체를 반환하고 전역 변수에 저장하며, 실패 시 오류를 기록하고 None 반환.
    """
    # 전역 변수 참조 (값을 변경하기 위함)
    global _retriever_instance, _retriever_initialization_error

    pdf_path = "./data/hyundai_2025.pdf" # PDF 파일 경로
    print(f"[Retriever Init] '{pdf_path}'에서 PDF 로딩 시작...")

    if not os.path.exists(pdf_path):
        error = FileNotFoundError(f"필요한 PDF 파일 '{pdf_path}'를 찾을 수 없습니다.")
        print(f"[Retriever Init] 오류: {error}")
        _retriever_initialization_error = error # 오류 기록
        return None # 실패 시 None 반환

    try:
        # 1단계: 문서 로드
        loader = PyMuPDFLoader(pdf_path)
        docs = loader.load()
        print(f"[Retriever Init] PDF 로드 완료. 총 {len(docs)} 페이지.")

        # 2단계: 문서 분할
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
        split_documents = text_splitter.split_documents(docs)
        print(f"[Retriever Init] 문서 분할 완료. 총 {len(split_documents)} 청크 생성.")

        # 3단계: 임베딩 생성 (로컬 모델)
        model_name = "mixedbread-ai/mxbai-embed-large-v1"
        model_kwargs = {'device': 'cpu'} # 또는 {'device': 'cuda'}
        print(f"[Retriever Init] 로컬 임베딩 모델 로딩 시작: {model_name} (장치: {model_kwargs.get('device')})...")
        embeddings = HuggingFaceEmbeddings(model_name=model_name, model_kwargs=model_kwargs)
        print("[Retriever Init] 로컬 임베딩 모델 로딩 완료.")

        # 4단계: 벡터 데이터베이스 생성 (FAISS)
        print("[Retriever Init] FAISS 벡터 저장소 구축 시작...")
        # FAISS.from_documents는 동기 함수일 수 있음. 매우 큰 문서의 경우 비동기 처리 고려.
        vectorstore = FAISS.from_documents(documents=split_documents, embedding=embeddings)
        print("[Retriever Init] FAISS 벡터 저장소 구축 완료.")

        # 5단계: Retriever 생성
        retriever = vectorstore.as_retriever()
        print("[Retriever Init] Retriever 생성 및 초기화 성공.")

        # 성공 시 전역 변수에 저장하고 오류 상태 초기화
        _retriever_instance = retriever
        _retriever_initialization_error = None
        return retriever # 생성된 retriever 반환

    except Exception as e:
        # 초기화 중 어떤 단계에서든 오류 발생 시
        print(f"[Retriever Init] FATAL: Retriever 초기화 중 심각한 오류 발생: {e}")
        traceback.print_exc()
        _retriever_initialization_error = e # 오류 기록
        _retriever_instance = None # 확실히 실패 상태로 설정
        return None # 실패 시 None 반환


# --- FastMCP 서버 초기화 ---
mcp = FastMCP(
    name="Retriever",
    instructions="데이터베이스에서 정보를 검색할 수 있는 Retriever입니다. 검색할 내용을 query로 입력하세요.",
    host="0.0.0.0",
    port=8005,
)

# --- MCP 도구 정의 ---
@mcp.tool()
async def retrieve(query: str) -> str:
    """
    주어진 질의(query)를 기반으로 미리 로드된 문서 데이터베이스에서 관련 정보를 검색합니다. (한국어 설명)
    Retriever는 최초 호출 시 초기화되며 이후 재사용됩니다.

    Args:
        query (str): 관련 정보를 찾기 위한 검색 질의.

    Returns:
        str: 검색된 모든 문서의 텍스트 내용을 개행 문자로 연결한 단일 문자열.
             초기화 실패 또는 검색 중 오류 발생 시 오류 메시지 문자열.
    """
    global _retriever_instance, _retriever_initialization_error, _init_lock

    print(f"[Retriever Tool] Received query: '{query}'")

    # --- Retriever 인스턴스 확인 및 초기화 (Lazy Initialization + Lock) ---
    # 비동기 락을 사용하여 동시에 여러 요청이 초기화를 시도하는 것을 방지 (선택적이지만 권장)
    async with _init_lock:
        if _retriever_instance is None:
            # 이전에 초기화 시도가 실패했는지 확인
            if _retriever_initialization_error is not None:
                print("[Retriever Tool] 이전에 Retriever 초기화 실패함. 오류 반환.")
                return f"오류: Retriever를 초기화할 수 없습니다. 서버 로그를 확인하세요. (저장된 오류: {str(_retriever_initialization_error)})"

            # 첫 호출 시 초기화 시도
            print("[Retriever Tool] Retriever가 초기화되지 않았습니다. 지금 초기화를 시작합니다...")
            # _build_and_initialize_retriever 함수는 동기 함수이므로,
            # asyncio 이벤트 루프를 차단하지 않도록 별도 스레드에서 실행하는 것이 좋음 (중요 성능 개선)
            # loop = asyncio.get_running_loop()
            # await loop.run_in_executor(None, _build_and_initialize_retriever)
            # --- 간단한 구현을 위해 우선 동기적으로 호출 (테스트용) ---
            _build_and_initialize_retriever()
            # --------------------------------------------------

            # 초기화 함수 실행 후 다시 상태 확인
            if _retriever_instance is None:
                # 초기화 함수 내부에서 오류가 발생하여 _retriever_instance가 여전히 None인 경우
                return f"오류: Retriever 초기화에 실패했습니다. 서버 로그를 확인하세요. (현재 오류: {str(_retriever_initialization_error)})"
            else:
                print("[Retriever Tool] Retriever 초기화 및 캐싱 완료.")
        else:
            print("[Retriever Tool] 캐시된 Retriever 인스턴스를 사용합니다.")
    # --- 초기화 및 확인 완료 ---

    # 이제 _retriever_instance는 사용 가능한 상태여야 함 (초기화 성공 시)
    try:
        print(f"[Retriever Tool] '{query}'에 대한 문서 검색 실행 (캐시된 retriever 사용)...")

        # retriever.invoke가 동기 함수일 가능성이 높으므로 비동기 환경에서는 주의 필요
        # 매우 긴 검색 작업이라면 run_in_executor 사용 권장
        # loop = asyncio.get_running_loop()
        # retrieved_docs: List[Document] = await loop.run_in_executor(None, _retriever_instance.invoke, query)

        # --- 간단한 구현을 위해 우선 동기적으로 호출 (테스트용) ---
        retrieved_docs: List[Document] = _retriever_instance.invoke(query)
        # --------------------------------------------------

        print(f"[Retriever Tool] {len(retrieved_docs)}개의 관련 문서를 찾았습니다.")

        if not retrieved_docs:
            return f"'{query}'에 해당하는 정보를 찾을 수 없습니다."

        # 검색된 문서 내용 결합
        result = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])
        print(f"[Retriever Tool] Returning retrieved content (first 300 chars):\n{result[:300]}...")
        return result

    except Exception as e:
        # 검색(invoke) 중 발생할 수 있는 오류 처리
        print(f"[Retriever Tool] Error during retrieval using cached instance: {e}")
        traceback.print_exc()
        return f"정보 검색 중 오류가 발생했습니다: {str(e)}"


# --- 메인 실행 블록 ---
if __name__ == "__main__":
    print("[Retriever Server] Retriever MCP 서버 시작 중 (stdio 전송 방식, 로컬 임베딩, 재사용)...")
    # 여기에서 서버 시작 시 Retriever를 미리 초기화할 수도 있습니다.
    # print("서버 시작 시 Retriever 초기화 시도...")
    # _build_and_initialize_retriever() # 첫 요청 전에 미리 로딩 (선택 사항)

    mcp.run(transport="stdio")
    print("[Retriever Server] Retriever MCP 서버가 중지되었습니다.")