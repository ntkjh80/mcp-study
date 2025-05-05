# -*- coding: utf-8 -*-
# 필요한 라이브러리 임포트
from mcp.server.fastmcp import FastMCP          # MCP 서버 생성
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound # YouTube 자막 추출 및 예외 처리
import xml.etree.ElementTree as ET             # XML 파싱 (RSS 피드)
from datetime import datetime                  # 날짜 및 시간 처리 (필요 시)
import requests                                # 동기 HTTP 요청 (API 호출용 - 필요 시 사용)
import httpx                                   # 비동기 HTTP 요청 (API 호출용)
import re                                      # 정규 표현식 (URL 파싱 등)
from dotenv import load_dotenv                 # .env 파일 로드
import os                                      # 운영 체제 기능 (환경 변수 접근, 경로)
from typing import List, Dict, Any, Optional   # 타입 힌트
import traceback                               # 상세 오류 로깅 위해 추가

# .env 파일 로드 (스크립트 위치 기준 또는 프로젝트 루트 기준)
# __file__ 은 현재 실행 중인 스크립트 파일의 경로를 나타냅니다.
# os.path.dirname(__file__) 은 스크립트가 위치한 디렉토리 경로입니다.
# os.path.join(..., '..', '.env') 는 해당 디렉토리의 상위 디렉토리에 있는 .env 파일을 가리킵니다.
# 프로젝트 구조에 맞게 경로를 조정해야 할 수 있습니다.
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)
print(f"[YouTube Server] Attempting to load .env file from: {dotenv_path}")


# YouTube API 키 및 기본 URL 설정
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") # 환경 변수에서 API 키 가져오기
YOUTUBE_API_URL = 'https://www.googleapis.com/youtube/v3' # YouTube Data API v3 기본 URL

# API 키 존재 여부 확인 및 처리
if not YOUTUBE_API_KEY:
    warning_message = "Warning: YOUTUBE_API_KEY environment variable is not set. YouTube API dependent tools (search, channel info) will fail."
    print(f"\n{'*'*len(warning_message)}")
    print(warning_message)
    print(f"{'*'*len(warning_message)}\n")
    # 중요: API 키가 꼭 필요한 경우, 여기서 서버 실행을 중단시키는 것이 더 안전할 수 있습니다.
    # raise ValueError("YOUTUBE_API_KEY is required but not set. Server cannot start.") # 주석 처리됨

# === 서버 호스트 및 포트 변수 정의 ===
# 이 값들은 mcp_server.json의 "youtube_agent_server" 설정과 일치해야 합니다 (특히 port).
SERVER_HOST = "127.0.0.1" # 서버가 리스닝할 IP 주소 (127.0.0.1은 로컬에서만 접속 허용)
SERVER_PORT = 8010        # 서버가 리스닝할 포트 번호

# FastMCP 서버 인스턴스 생성
mcp = FastMCP(
    name="youtube_agent_server", # 서버 고유 이름 (mcp_server.json의 키와 일치 권장)
    instructions="Tool for searching YouTube videos, getting transcripts, and retrieving channel information.", # LLM을 위한 도구 설명
    host=SERVER_HOST,  # <--- 정의된 변수 사용
    port=SERVER_PORT,  # <--- 정의된 변수 사용
    settings={
        "initialization_timeout": 15.0, # 초기화 타임아웃 증가 (네트워크 상황 고려)
        "log_level": "info" # 로그 레벨 설정 (debug, info, warning, error)
    }
)

# --- 비동기 HTTP 클라이언트 (선택 사항, 성능 개선 가능성) ---
# 여러 API 호출이 빈번하다면 애플리케이션 레벨에서 비동기 클라이언트를 생성하여 재사용하는 것이 좋습니다.
# async_http_client = httpx.AsyncClient(timeout=10.0) # 예시: 타임아웃 10초 설정

### === 유틸리티 함수 ===
def _extract_video_id(url: str) -> Optional[str]:
    """
    다양한 형태의 YouTube URL에서 비디오 ID(11자리)를 추출합니다.
    지원 형식:
    - https://www.youtube.com/watch?v=4... (v=VIDEO_ID)
    - https://www.youtube.com/watch?v=5
    - https://www.youtube.com/watch?v=6
    - youtu.be/VIDEO_ID
    - /embed/VIDEO_ID
    - /v/VIDEO_ID
    """
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:\?|&|\/|$)", # v=VIDEO_ID or /VIDEO_ID (query/path end)
        r"youtu\.be\/([0-9A-Za-z_-]{11})(?:\?|$)",    # youtu.be/VIDEO_ID
        r"\/(?:embed|v)\/([0-9A-Za-z_-]{11})(?:\?|$)" # /embed/VIDEO_ID or /v/VIDEO_ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1) # 첫 번째 매칭 그룹 (비디오 ID) 반환
    return None # 매칭되는 패턴이 없으면 None 반환

### === 도구 1: YouTube 자막 추출 ===
@mcp.tool()
# 비동기 함수로 유지 (내부에서 동기 라이브러리 호출 시에도 서버 전체 비동기 유지)
async def get_youtube_transcript(url: str) -> str:
    """
    주어진 YouTube 동영상 URL에서 자막(transcript) 텍스트를 추출합니다.
    한국어 또는 영어 자막을 우선적으로 가져오며, 자동 생성된 자막도 포함하여 검색합니다.
    자막이 없거나 비활성화된 경우 설명적인 오류 메시지를 반환합니다.

    Args:
        url (str): 자막을 추출할 YouTube 동영상 URL.

    Returns:
        str: 추출된 자막 텍스트. 자막이 없거나 오류 발생 시 설명적인 메시지 반환.
    """
    print(f"[YouTube Tool] Calling get_youtube_transcript for URL: {url}")

    video_id = _extract_video_id(url)
    if not video_id:
        error_msg = f"오류: 유효하지 않은 YouTube URL('{url}')이거나 비디오 ID를 추출할 수 없습니다."
        print(error_msg)
        return error_msg

    print(f"Extracted Video ID: {video_id}")
    preferred_languages = ["ko", "en"]

    try:
        # 비동기 환경에서 동기 라이브러리 호출 (run_in_executor 사용 권장되나, 간단히 직접 호출)
        # 주의: CPU-bound 작업이 길 경우 이벤트 루프를 블록할 수 있음.
        # transcript_list = await asyncio.to_thread(YouTubeTranscriptApi.list_transcripts, video_id) # Python 3.9+

        # 간단한 직접 호출 (IO-bound 작업이 짧다고 가정)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = None
        found_lang = None

        # 1. 수동 생성된 선호 언어 자막 찾기
        for lang in preferred_languages:
            try:
                transcript = transcript_list.find_transcript([lang])
                found_lang = f"{lang} (manual)"
                break
            except NoTranscriptFound:
                continue

        # 2. 자동 생성된 선호 언어 자막 찾기
        if not transcript:
            for lang in preferred_languages:
                try:
                    transcript = transcript_list.find_generated_transcript([lang])
                    found_lang = f"{lang} (auto-generated)"
                    break
                except NoTranscriptFound:
                    continue

        # 3. 사용 가능한 첫 번째 자막 가져오기 (선호 언어 없을 시)
        if not transcript:
             # 사용 가능한 모든 자막 목록 (수동 + 자동)
             available_transcripts = list(transcript_list)
             if available_transcripts:
                 first_available = available_transcripts[0]
                 transcript = first_available # 첫 번째 사용 가능한 자막 객체
                 found_lang = f"{transcript.language} ({'manual' if not transcript.is_generated else 'auto-generated'})"
                 print(f"Preferred language transcript not found. Using first available: {found_lang}")
             else:
                 # 사용 가능한 자막이 전혀 없음
                 raise NoTranscriptFound(f"No manual or auto-generated transcripts found for video {video_id}.")

        # 자막 객체에서 텍스트 데이터 가져오기 (fetch는 동기 메서드)
        # transcript_data = await asyncio.to_thread(transcript.fetch) # Python 3.9+
        transcript_data = transcript.fetch() # 간단한 직접 호출

        print(f"Successfully fetched transcript for video '{video_id}' (Language: {found_lang}).")
        transcript_text = " ".join([entry["text"] for entry in transcript_data])
        return transcript_text

    except TranscriptsDisabled:
        error_message = f"오류: 비디오 ID '{video_id}'의 자막 기능이 비활성화되어 있습니다."
        print(error_message)
        return error_message
    except NoTranscriptFound as e:
        error_message = f"오류: 비디오 ID '{video_id}'에 대해 사용 가능한 자막을 찾을 수 없습니다. ({e})"
        print(error_message)
        return error_message
    except Exception as e:
        error_message = f"오류: 비디오 ID '{video_id}'의 자막을 가져오는 중 예상치 못한 오류 발생: {type(e).__name__} - {e}"
        print(error_message)
        traceback.print_exc() # 상세 오류 로그 추가
        return error_message

### === 도구 2: YouTube 동영상 검색 ===
@mcp.tool()
async def search_youtube_videos(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    주어진 검색어로 YouTube 동영상을 검색하고 관련 세부 정보 목록을 반환합니다.
    YouTube Data API를 사용합니다. API 키가 설정되어 있어야 합니다.

    Args:
        query (str): 검색할 키워드 또는 문구.
        max_results (int): 가져올 최대 검색 결과 수 (기본값 5, 유효 범위 1-20).

    Returns:
        List[Dict[str, Any]]: 검색된 동영상 정보 딕셔너리의 리스트.
                               오류 발생 또는 결과 없을 시 빈 리스트 반환.
    """
    print(f"[YouTube Tool] Calling search_youtube_videos: Query='{query}', MaxResults={max_results}")

    if not YOUTUBE_API_KEY:
        print("Error: YOUTUBE_API_KEY is not set. Cannot perform Youtube.")
        return []

    safe_max_results = max(1, min(max_results, 20))
    print(f"Adjusted MaxResults: {safe_max_results}")

    video_results = []

    try:
        # httpx 클라이언트를 매번 생성하거나, 위에서 생성한 async_http_client 재사용
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. YouTube Data API 검색 (Search: list)
            search_params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': safe_max_results,
                'key': YOUTUBE_API_KEY
            }
            search_url = f"{YOUTUBE_API_URL}/search"
            print(f"Calling Youtube API: {search_url} with query '{query}'")
            search_response = await client.get(search_url, params=search_params)
            search_response.raise_for_status()
            search_data = search_response.json()

            video_ids = [
                item['id']['videoId']
                for item in search_data.get('items', [])
                if item.get('id', {}).get('kind') == 'youtube#video' and 'videoId' in item.get('id', {})
            ]

            if not video_ids:
                print("No videos found for the query.")
                return []

            print(f"Found video IDs: {', '.join(video_ids)}")

            # 2. 동영상 세부 정보 조회 (Videos: list)
            video_details_params = {
                'part': 'snippet,statistics',
                'id': ','.join(video_ids),
                'key': YOUTUBE_API_KEY
            }
            video_details_url = f"{YOUTUBE_API_URL}/videos"
            print(f"Calling YouTube Videos API for details: {video_details_url}")
            details_response = await client.get(video_details_url, params=video_details_params)
            details_response.raise_for_status()
            details_data = details_response.json()

            # 3. 결과 가공
            for item in details_data.get('items', []):
                snippet = item.get('snippet', {})
                statistics = item.get('statistics', {})
                thumbnails = snippet.get('thumbnails', {})
                thumbnail_url = thumbnails.get('high', {}).get('url') or \
                                thumbnails.get('medium', {}).get('url') or \
                                thumbnails.get('default', {}).get('url', '')
                view_count_str = statistics.get('viewCount')
                like_count_str = statistics.get('likeCount')
                video_id = item.get('id', '')
                standard_video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""

                video_card = {
                    "title": snippet.get('title', 'N/A'),
                    "publishedDate": snippet.get('publishedAt', ''),
                    "channelName": snippet.get('channelTitle', 'N/A'),
                    "channelId": snippet.get('channelId', ''),
                    "thumbnailUrl": thumbnail_url,
                    "viewCount": int(view_count_str) if view_count_str is not None else 0,
                    "likeCount": int(like_count_str) if like_count_str is not None else 0,
                    "url": standard_video_url
                }
                video_results.append(video_card)

        if not video_results:
            print("Could not fetch details for the found video IDs.")
            return []

        print(f"Returning details for {len(video_results)} videos.")
        return video_results

    except httpx.HTTPStatusError as e:
        print(f"Error: YouTube API request failed with status {e.response.status_code} - {e.response.text}")
        return []
    except httpx.RequestError as e:
        print(f"Error: YouTube API request failed due to network issue - {e}")
        return []
    except Exception as e:
        print(f"Error: An unexpected error occurred during video search - {type(e).__name__}: {e}")
        traceback.print_exc()
        return []


### === 도구 3: 채널 정보 및 최근 동영상 조회 ===
@mcp.tool()
async def get_channel_info(video_url: str) -> Optional[Dict[str, Any]]:
    """
    주어진 YouTube 동영상 URL로부터 해당 채널의 정보와 최근 동영상 목록(최대 5개)을 가져옵니다.
    YouTube Data API (Channels, PlaylistItems)를 사용합니다. (API 키 필요)

    Args:
        video_url (str): 채널 정보를 조회할 기준이 되는 YouTube 동영상 URL.

    Returns:
        Optional[Dict[str, Any]]: 채널 정보 및 최근 동영상 목록 포함 딕셔너리. 오류 시 None.
    """
    print(f"[YouTube Tool] Calling get_channel_info for Video URL: {video_url}")

    if not YOUTUBE_API_KEY:
        print("Error: YOUTUBE_API_KEY is not set. Cannot get channel info.")
        return None

    video_id = _extract_video_id(video_url)
    if not video_id:
        print(f"Error: Invalid YouTube video URL provided: {video_url}")
        return None

    print(f"Extracted video ID: {video_id}")

    # 내부 함수: 채널 업로드 재생목록 ID로 최근 동영상 가져오기 (API 방식)
    async def fetch_recent_videos_api(uploads_playlist_id: str, client: httpx.AsyncClient, max_videos: int = 5) -> List[Dict[str, str]]:
         print(f"Fetching recent videos via API for playlist ID: {uploads_playlist_id}")
         videos = []
         playlist_items_params = {
             'part': 'snippet',
             'playlistId': uploads_playlist_id,
             'maxResults': max(1, min(max_videos, 50)),
             'key': YOUTUBE_API_KEY
         }
         playlist_items_url = f"{YOUTUBE_API_URL}/playlistItems"
         try:
             response = await client.get(playlist_items_url, params=playlist_items_params)
             response.raise_for_status()
             data = response.json()
             for item in data.get('items', []):
                 snippet = item.get('snippet', {})
                 res_video_id = snippet.get('resourceId', {}).get('videoId')
                 if not res_video_id: continue
                 video_info = {
                     'title': snippet.get('title', 'N/A'),
                     'link': f"https://www.youtube.com/watch?v={res_video_id}",
                     'publishedDate': snippet.get('publishedAt', ''),
                     'videoId': res_video_id
                 }
                 videos.append(video_info)
                 if len(videos) >= max_videos: break
             print(f"Fetched {len(videos)} recent videos via API.")
             return videos
         except httpx.HTTPStatusError as e:
             print(f"Error: Failed to fetch playlist items ({playlist_items_url}) - HTTP Status {e.response.status_code}")
             return []
         except httpx.RequestError as e:
             print(f"Error: Network error fetching playlist items ({playlist_items_url}) - {e}")
             return []
         except Exception as e:
             print(f"Error: Unexpected error fetching recent videos via API - {type(e).__name__}: {e}")
             traceback.print_exc()
             return []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. 비디오 정보 조회 (채널 ID 획득용)
            video_params = {'part': 'snippet', 'id': video_id, 'key': YOUTUBE_API_KEY}
            video_api_url = f"{YOUTUBE_API_URL}/videos"
            print(f"Calling Videos API to get channel ID: {video_api_url}")
            video_response = await client.get(video_api_url, params=video_params)
            video_response.raise_for_status()
            video_data = video_response.json()
            if not video_data.get('items'):
                print(f"Error: No video found with ID '{video_id}'")
                return None
            video_info = video_data['items'][0]
            channel_id = video_info.get('snippet', {}).get('channelId')
            if not channel_id:
                 print("Error: Could not find channel ID in video snippet.")
                 return None
            print(f"Obtained Channel ID: {channel_id}")

            # 2. 채널 상세 정보 조회 (Channels: list)
            channel_params = {
                'part': 'snippet,statistics,contentDetails',
                'id': channel_id,
                'key': YOUTUBE_API_KEY
            }
            channel_api_url = f"{YOUTUBE_API_URL}/channels"
            print(f"Calling Channels API for details: {channel_api_url}")
            channel_response = await client.get(channel_api_url, params=channel_params)
            channel_response.raise_for_status()
            channel_data_items = channel_response.json().get('items')
            if not channel_data_items:
                 print(f"Error: No channel found with ID '{channel_id}'")
                 return None
            channel_data = channel_data_items[0]

            # 3. 채널 정보 추출
            channel_snippet = channel_data.get('snippet', {})
            channel_statistics = channel_data.get('statistics', {})
            channel_content_details = channel_data.get('contentDetails', {})
            standard_channel_url = f"https://www.youtube.com/channel/{channel_id}"
            subscriber_count_str = channel_statistics.get('subscriberCount')
            is_subscriber_hidden = channel_statistics.get('hiddenSubscriberCount', False)
            subscriber_display = "비공개" if is_subscriber_hidden else (subscriber_count_str or '0')

            channel_info_result = {
                'channelTitle': channel_snippet.get('title', 'N/A'),
                'channelDescription': channel_snippet.get('description', ''),
                'channelUrl': standard_channel_url,
                'subscriberCount': subscriber_display,
                'viewCount': channel_statistics.get('viewCount', '0'),
                'videoCount': channel_statistics.get('videoCount', '0'),
                'publishedAt': channel_snippet.get('publishedAt', ''),
                'videos': [] # 초기화
            }

            # 4. 최근 동영상 목록 가져오기 (API 방식)
            uploads_playlist_id = channel_content_details.get('relatedPlaylists', {}).get('uploads')
            if uploads_playlist_id:
                 print(f"Found uploads playlist ID: {uploads_playlist_id}. Fetching via API...")
                 channel_info_result['videos'] = await fetch_recent_videos_api(uploads_playlist_id, client, max_videos=5)
            else:
                 print("Warning: Uploads playlist ID not found for channel. Cannot fetch recent videos.")

            print(f"Successfully retrieved channel info for '{channel_info_result['channelTitle']}'")
            return channel_info_result

    except httpx.HTTPStatusError as e:
        print(f"Error: YouTube API request failed with status {e.response.status_code} - {e.response.text}")
        return None
    except httpx.RequestError as e:
        print(f"Error: YouTube API request failed due to network issue - {e}")
        return None
    except Exception as e:
        print(f"Error: An unexpected error occurred while getting channel info - {type(e).__name__}: {e}")
        traceback.print_exc()
        return None


# --- 스크립트가 직접 실행될 때 서버 시작 ---
if __name__ == "__main__":
    print("[YouTube Server] Starting YouTube MCP server using SSE transport...")
    print(f"[YouTube Server] Process ID: {os.getpid()}")

    # === 수정된 부분: 정의된 변수 사용 ===
    print(f"[YouTube Server] Listening on http://{SERVER_HOST}:{SERVER_PORT}")

    if not YOUTUBE_API_KEY: print("[YouTube Server] Warning: API Key not set!")

    try:
        # MCP 서버 실행 (uvicorn 기반으로 실행될 수 있음)
        mcp.run(
            transport="sse",
            # uvicorn_kwargs={"log_level": "info", "reload": True} # 개발 시 자동 리로드 옵션 추가 가능
        )
    except KeyboardInterrupt:
         print("\n[YouTube Server] Received KeyboardInterrupt. Shutting down...")
    except Exception as e:
        # 서버 실행 중 예외 발생 시 로깅
        print(f"[YouTube Server] Error during server run: {type(e).__name__} - {e}")
        traceback.print_exc() # 상세 스택 트레이스 출력
    finally:
        # 서버 종료 시 메시지 출력
        # 참고: mcp.run() 이 정상 종료되거나 예외로 빠져나온 후에 실행됩니다.
        print("[YouTube Server] YouTube MCP server stopped.")