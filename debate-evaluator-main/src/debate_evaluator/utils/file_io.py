"""파일 입출력 유틸리티"""

from pathlib import Path
from typing import Union


def read_transcript(file_path: Union[str, Path]) -> str:
    """토론 스크립트 파일 읽기

    Args:
        file_path: 파일 경로

    Returns:
        파일 내용 문자열

    Raises:
        FileNotFoundError: 파일이 존재하지 않음
        ValueError: 파일이 비어있음
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    content = path.read_text(encoding="utf-8").strip()

    if not content:
        raise ValueError(f"파일이 비어있습니다: {path}")

    return content


def write_output(file_path: Union[str, Path], content: str) -> Path:
    """결과 파일 저장

    Args:
        file_path: 저장할 파일 경로
        content: 저장할 내용

    Returns:
        저장된 파일의 Path 객체
    """
    path = Path(file_path)

    # 상위 디렉토리가 없으면 생성
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(content, encoding="utf-8")

    return path
