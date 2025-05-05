# -*- coding: utf-8 -*-
# 필요한 라이브러리 임포트
from langchain_text_splitters import RecursiveCharacterTextSplitter # 텍스트 분할 도구
from langchain_community.document_loaders import PyMuPDFLoader    # PDF 문서 로더 (pymupdf 필요)
from langchain_community.vectorstores import FAISS                 # FAISS 벡터 저장소 (faiss-cpu 또는 faiss-gpu 필요)
# --- 수정: OpenAI 대신 HuggingFace 임베딩 사용 ---
# from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings # 로컬 또는 HuggingFace 모델용 임베딩 (sentence-transformers, torch 필요)
# -------------------------------------------------
from mcp.server.fastmcp import FastMCP                           # MCP 서버 클래스
from dotenv import load_dotenv                                   # .env 파일 로더 (선택 사항, API 키 불필요 시 제거 가능)
from typing import Any, List                                     # 타입 힌트
from langchain_core.documents import Document                    # Document 타입 힌트 (선택 사항)
import os                                                        # 파일 경로 확인 등
import traceback                                                 # 오류 로깅

# --- 환경 변수 로드 (선택 사항) ---
# OpenAI API 키는 더 이상 필요하지 않지만, 다른 설정이 있을 수 있으므로 유지하거나 제거합니다.
# load_dotenv(override=True)
# print("[Retriever Server] 환경 변수 로딩 시도 (참고: OpenAI API 키는 더 이상 임베딩에 사용되지 않음)...")

# --- Retriever 생성 함수 ---
# 중요 경고: 여전히 매번 호출 시 전체 RAG 파이프라인을 새로 구축합니다. (매우 비효율적)
def create_retriever() -> Any:
    """
    FAISS 벡터 저장소 기반의 문서 검색기(Retriever)를 생성하여 반환합니다. (한국어 설명)
    로컬 HuggingFace 임베딩 모델('mixedbread-ai/mxbai-embed-large-v1')을 사용합니다.

    이 함수는 다음 단계를 수행합니다:
    1. 지정된 경로의 PDF 문서를 로드합니다.
    2. 문서를 관리 가능한 크기의 청크(chunk)로 분할합니다.
    3. 각 청크에 대한 임베딩 벡터를 로컬 모델을 사용하여 생성합니다. (**주의: 첫 실행 시 모델 다운로드 필요, CPU/GPU 자원 사용**)
    4. 임베딩으로부터 FAISS 벡터 저장소를 구축합니다.
    5. 벡터 저장소에 대한 검색 인터페이스(Retriever)를 반환합니다.

    **성능 경고**: 현재 이 함수는 호출될 때마다 위의 모든 과정을 반복합니다.
                  실제 애플리케이션에서는 벡터 저장소나 검색기를 미리 빌드하고
                  재사용하는 방식(예: 서버 시작 시 초기화)이 필수적입니다.

    Returns:
        Any: 문서 데이터베이스를 쿼리하는 데 사용할 수 있는 Retriever 객체.
    """
    pdf_path = "./data/hyundai_2025.pdf" # PDF 파일 경로 (실제 경로 확인 필요)
    print(f"[Retriever Server] '{pdf_path}'에서 PDF 로딩 시작...")

    if not os.path.exists(pdf_path):
        print(f"[Retriever Server] 오류: PDF 파일을 찾을 수 없습니다! 경로: {pdf_path}")
        raise FileNotFoundError(f"필요한 PDF 파일 '{pdf_path}'를 찾을 수 없습니다.")

    try:
        # 1단계: 문서 로드
        loader = PyMuPDFLoader(pdf_path)
        docs = loader.load()
        print(f"[Retriever Server] PDF 로드 완료. 총 {len(docs)} 페이지.")

        # 2단계: 문서 분할
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
        split_documents = text_splitter.split_documents(docs)
        print(f"[Retriever Server] 문서 분할 완료. 총 {len(split_documents)} 청크 생성.")

        # --- 수정: 로컬 HuggingFace 임베딩 모델 설정 ---
        # 3단계: 임베딩 생성 (로컬 모델 사용)
        # 사용할 Hugging Face 모델 ID (정확한 ID 확인 필요)
        model_name = "mixedbread-ai/mxbai-embed-large-v1"
        # 계산 장치 설정 ('cuda'는 GPU, 'cpu'는 CPU) - 환경에 맞게 선택
        # model_kwargs = {'device': 'cuda'} # GPU 사용 시 (NVIDIA GPU 및 CUDA 설치 필요)
        model_kwargs = {'device': 'cpu'}   # CPU 사용 시
        # 임베딩 결과 정규화(normalize) 여부 등 추가 설정 가능
        # encode_kwargs = {'normalize_embeddings': True}

        print(f"[Retriever Server] 로컬 임베딩 모델 로딩 시작: {model_name} (장치: {model_kwargs.get('device')})...")
        # 처음 실행 시 모델 파일 다운로드에 시간이 소요될 수 있습니다.
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
            # encode_kwargs=encode_kwargs # 필요시 주석 해제
        )
        print("[Retriever Server] 로컬 임베딩 모델 로딩 완료.")
        # -------------------------------------------------

        # 4단계: 벡터 데이터베이스 생성 (FAISS)
        print("[Retriever Server] FAISS 벡터 저장소 구축 시작...")
        vectorstore = FAISS.from_documents(documents=split_documents, embedding=embeddings)
        print("[Retriever Server] FAISS 벡터 저장소 구축 완료.")

        # 5단계: Retriever 생성
        retriever = vectorstore.as_retriever()
        print("[Retriever Server] Retriever 생성 완료.")
        return retriever

    except Exception as e:
        print(f"[Retriever Server] Retriever 생성 중 오류 발생: {e}")
        traceback.print_exc()
        raise e

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
    주어진 질의(query)를 기반으로 문서 데이터베이스에서 관련 정보를 검색합니다. (한국어 설명)
    **로컬 임베딩 모델**을 사용하며, 매번 Retriever를 새로 생성합니다(매우 비효율적).

    **성능 경고**: 이 함수는 호출될 때마다 Retriever를 **새로 생성**합니다.
                  이는 PDF 로딩, 텍스트 분할, **로컬 모델 임베딩 생성(CPU/GPU 부하!)**,
                  FAISS 인덱스 구축을 매번 반복하는 매우 비효율적인 방식입니다.
                  실제 운영 환경에서는 절대 이렇게 사용하면 안 됩니다.
                  Retriever(또는 VectorStore)는 서버 시작 시 한 번만 생성하고 재사용해야 합니다.

    Args:
        query (str): 관련 정보를 찾기 위한 검색 질의.

    Returns:
        str: 검색된 모든 문서의 텍스트 내용을 개행 문자로 연결한 단일 문자열.
             오류 발생 시 오류 메시지 문자열.
    """
    print(f"[Retriever Tool] Received query: '{query}'")
    print("[Retriever Tool] 경고: 매번 Retriever를 새로 생성합니다. (로컬 모델 사용 시에도 매우 비효율적)") # 경고 로그

    try:
        # --- 비효율적인 부분: 매번 Retriever 새로 생성 ---
        retriever = create_retriever()
        # -------------------------------------------

        if retriever is None:
             return "오류: Retriever를 생성하는 데 실패했습니다. 서버 로그를 확인하세요."

        print(f"[Retriever Tool] '{query}'에 대한 문서 검색 실행...")
        # 로컬 임베딩/FAISS 검색은 CPU/GPU 자원을 사용합니다.
        # retriever.invoke 는 동기 함수일 수 있으므로, 필요시 await asyncio.to_thread 사용 고려
        retrieved_docs: List[Document] = retriever.invoke(query)
        print(f"[Retriever Tool] {len(retrieved_docs)}개의 관련 문서를 찾았습니다.")

        if not retrieved_docs:
            return f"'{query}'에 해당하는 정보를 찾을 수 없습니다."

        result = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])
        print(f"[Retriever Tool] Returning retrieved content (first 300 chars):\n{result[:300]}...")
        return result

    except FileNotFoundError as e:
         print(f"[Retriever Tool] Error: {e}")
         return f"오류: 필요한 데이터 파일({e.filename})을 찾을 수 없습니다."
    except Exception as e:
        print(f"[Retriever Tool] Error during retrieval: {e}")
        traceback.print_exc()
        return f"정보 검색 중 오류가 발생했습니다: {str(e)}"


# --- 메인 실행 블록 ---
if __name__ == "__main__":
    print("[Retriever Server] Retriever MCP 서버 시작 중 (stdio 전송 방식, 로컬 임베딩 사용)...")
    # stdio 전송 방식을 사용하여 MCP 클라이언트와 통합
    mcp.run(transport="stdio")
    print("[Retriever Server] Retriever MCP 서버가 중지되었습니다.")