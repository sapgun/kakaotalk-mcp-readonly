# KakaoTalk MCP (read-only fork)

> Fork of [kronenz/kakaotalk-mcp](https://github.com/kronenz/kakaotalk-mcp) (MIT). **Read-only by default**: MCP send tools are disabled and all send functions are blocked unless `KAKAO_ALLOW_SEND=1` is set for a single approved message via `kakao_ro.py send`. Adds chat-list OCR, clipboard/focus restore, new-message state, robust room open, and the `kakao_ro.py` CLI. Unofficial and not affiliated with Kakao; use at your own risk (see Kakao's operating policy).

# KakaoTalk MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Windows](https://img.shields.io/badge/platform-Windows-0078d4.svg)](https://www.microsoft.com/windows)

카카오톡 PC를 Win32 API로 제어하는 [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) 서버입니다.

Claude Desktop, Claude Code 등 MCP 클라이언트에서 카카오톡 메시지를 보내고, 읽고, 채팅방을 관리할 수 있습니다.

## 주요 기능

### 기본 도구

| 도구 | 설명 |
|------|------|
| `kakao_health_check` | 카카오톡 PC 실행 상태 확인 |
| `kakao_list_open_rooms` | 열려있는 채팅방 목록 조회 |
| `kakao_open_room` | 채팅방 검색 및 열기 |
| `kakao_send_message` | 채팅방에 메시지 전송 |
| `kakao_send_bulk` | 여러 채팅방에 동일 메시지 일괄 전송 |
| `kakao_send_mention` | @멘션과 함께 메시지 전송 |
| `kakao_read_messages` | 채팅방 메시지 읽기 |
| `kakao_extract_links` | 채팅방에서 공유된 URL 추출 |
| `kakao_send_image` | 채팅방에 이미지 파일 전송 |
| `kakao_download_images` | 카카오톡 캐시에서 최근 이미지 다운로드 |

### 모니터링 도구

| 도구 | 설명 |
|------|------|
| `kakao_start_monitor` | 채팅방 키워드 모니터링 시작 |
| `kakao_stop_monitor` | 모니터링 중지 |
| `kakao_get_monitor_events` | 감지된 키워드 이벤트 조회 |

## 요구사항

- **Windows 10/11** (Win32 API 기반이므로 Windows 전용)
- **카카오톡 PC** 설치 및 로그인 상태
- **Python 3.10** 이상

## 설치

### uvx (권장)

별도 설치 없이 바로 실행:

```bash
uvx kakaotalk-mcp
```

### pip

```bash
pip install kakaotalk-mcp
```

### 소스에서 설치

```bash
git clone https://github.com/kronenz/kakaotalk-mcp.git
cd kakaotalk-mcp
pip install -e .
```

## 설정

### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json` 파일에 추가:

**uvx 사용 시:**

```json
{
  "mcpServers": {
    "kakao": {
      "command": "uvx",
      "args": ["kakaotalk-mcp"]
    }
  }
}
```

**pip 설치 후:**

```json
{
  "mcpServers": {
    "kakao": {
      "command": "kakaotalk-mcp"
    }
  }
}
```

**소스에서 직접 실행:**

```json
{
  "mcpServers": {
    "kakao": {
      "command": "python",
      "args": ["C:/경로/kakaotalk-mcp/src/kakao_mcp/server.py"],
      "env": {
        "PYTHONPATH": "C:/경로/kakaotalk-mcp/src"
      }
    }
  }
}
```

### Claude Code

Claude Code 설정에서 MCP 서버 추가:

```bash
claude mcp add kakao -- uvx kakaotalk-mcp
```

또는 `.claude/settings.json`에 직접 추가:

```json
{
  "mcpServers": {
    "kakao": {
      "command": "uvx",
      "args": ["kakaotalk-mcp"]
    }
  }
}
```

## 사용 예시

Claude에게 자연어로 요청하면 됩니다:

- "카카오톡 실행 중인지 확인해줘"
- "열린 채팅방 목록 보여줘"
- "홍길동 채팅방 열어줘"
- "홍길동에게 '회의 10분 후에 시작합니다' 보내줘"
- "홍길동에게 @멘션으로 '확인 부탁드립니다' 보내줘"
- "홍길동 채팅방 최근 대화 읽어줘"
- "홍길동 채팅방에서 공유된 링크 추출해줘"
- "이 이미지를 홍길동에게 보내줘: C:\Users\사용자\Pictures\photo.jpg"
- "최근 카카오톡 이미지 다운로드해줘"
- "홍길동, 김철수, 이영희에게 '내일 회의 참석 부탁드립니다' 보내줘"
- "공학자들 채팅방에서 '회의', '점심' 키워드를 모니터링하고 감지되면 답장해줘"
- "모니터링 중지해줘"

## 제한사항 및 주의사항

- **Windows 전용**: Win32 API를 사용하므로 macOS/Linux에서는 동작하지 않습니다.
- **포그라운드 필요**: 메시지 읽기(`kakao_read_messages`), 채팅방 열기(`kakao_open_room`), 멘션 전송(`kakao_send_mention`) 시 카카오톡 창이 잠시 최전면으로 올라옵니다.
- **멘션(@) 기능**: `kakao_send_mention`은 키보드 시뮬레이션으로 @멘션 팝업을 활성화합니다. 한글 2벌식 자판 입력을 사용하므로 시스템 키보드 레이아웃이 한글이어야 합니다.
- **클립보드 사용**: 메시지 읽기/전송 시 시스템 클립보드를 사용합니다. 작업 중 클립보드 내용이 변경될 수 있습니다.
- **채팅방 이름 정확히 입력**: `kakao_send_message`, `kakao_read_messages`는 채팅방 창 제목이 정확히 일치해야 합니다. 먼저 `kakao_list_open_rooms`로 정확한 이름을 확인하세요.
- **이미지 전송**: `kakao_send_image`는 파일을 클립보드에 복사한 후 Ctrl+V로 붙여넣는 방식입니다. 전송 확인 다이얼로그가 자동으로 처리됩니다. JPG, PNG, GIF, BMP, WebP 형식을 지원합니다.
- **이미지 다운로드**: 카카오톡 로컬 캐시에서 가져오며, 채팅방별 구분 없이 최근 캐시된 이미지가 다운로드됩니다.
- **모니터링 기능**: `kakao_start_monitor`는 백그라운드에서 채팅방을 주기적으로 폴링합니다. 폴링 시마다 카카오톡 창이 잠시 최전면으로 올라오며, 최소 폴링 간격은 3초입니다.

## 로드맵

### v0.2.0 — 서버 사이드 자동 응답 (예정)

클라이언트 폴링 방식의 토큰 비효율 문제를 해결하기 위해, MCP 서버 내부에서 채팅 감지 + AI 답장 생성 + 전송을 처리하는 기능을 추가할 예정입니다.

| 도구 | 설명 |
|------|------|
| `kakao_start_auto_reply` | AI 자동 응답 모니터링 시작 (서버 사이드) |
| `kakao_stop_auto_reply` | 자동 응답 중지 |
| `kakao_get_auto_reply_log` | 자동 응답 이력 조회 |

**핵심 개선:**
- 새 메시지 감지는 서버 내부 hash 비교로 처리 (토큰 0)
- AI 답장이 필요할 때만 Claude API를 최소 컨텍스트(최근 10개 메시지)로 호출
- 클라이언트 폴링 대비 **토큰 ~99% 절감**

## 프로젝트 구조

```
kakaotalk-mcp/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
├── requirements.txt
├── src/
│   └── kakao_mcp/
│       ├── __init__.py
│       ├── __main__.py      # python -m kakao_mcp 지원
│       ├── server.py        # MCP 서버 + 13개 도구 정의
│       ├── controller.py    # Win32 API 래퍼
│       ├── parser.py        # 클립보드 텍스트 파싱
│       └── config.py        # 상수 및 설정
└── tests/
    ├── test_parser.py       # 파서 단위 테스트
    └── test_controller.py   # 컨트롤러 mock 테스트
```

## 라이선스

[MIT License](LICENSE)

## Read-only fork additions

Send tools are not registered and controller send functions raise unless `KAKAO_ALLOW_SEND=1`.

CLI (JSON output):

    uv run --quiet python kakao_ro.py list-rooms      # main-window chat list via Windows OCR (best effort)
    uv run --quiet python kakao_ro.py read "<room>" -n 30 [--close]
    uv run --quiet python kakao_ro.py read-new "<room>" [--first 20] [--close]
    uv run --quiet python kakao_ro.py open "<room>"
    uv run --quiet python kakao_ro.py open-windows
    uv run --quiet python kakao_ro.py reset-state ["<room>"]

Reads restore the clipboard and the previously focused window. Seen-message state:
`%LOCALAPPDATA%\kakao-mcp-readonly\state.json`.