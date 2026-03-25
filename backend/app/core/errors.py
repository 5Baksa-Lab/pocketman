"""
공통 에러 코드 및 예외 클래스
"""
from fastapi import HTTPException


class PocketmanError(HTTPException):
    pass


class FaceNotDetectedError(PocketmanError):
    def __init__(self):
        super().__init__(status_code=422, detail={
            "error_code": "FACE_NOT_DETECTED",
            "message": "얼굴을 감지할 수 없습니다. 정면 얼굴 사진을 사용해주세요.",
        })


class MultipleFacesError(PocketmanError):
    def __init__(self):
        super().__init__(status_code=422, detail={
            "error_code": "MULTIPLE_FACES",
            "message": "얼굴이 2개 이상 감지됩니다. 1인 사진을 사용해주세요.",
        })


class LowQualityError(PocketmanError):
    def __init__(self):
        super().__init__(status_code=422, detail={
            "error_code": "LOW_QUALITY",
            "message": "이미지 품질이 낮습니다. 더 선명한 사진을 사용해주세요.",
        })


class VectorSearchError(PocketmanError):
    def __init__(self, detail: str = "벡터 검색 중 오류가 발생했습니다."):
        super().__init__(status_code=500, detail={
            "error_code": "VECTOR_SEARCH_ERROR",
            "message": detail,
        })


class NotFoundError(PocketmanError):
    def __init__(self, message: str = "요청한 리소스를 찾을 수 없습니다.", error_code: str = "NOT_FOUND"):
        super().__init__(status_code=404, detail={
            "error_code": error_code,
            "message": message,
        })


class InvalidRequestError(PocketmanError):
    def __init__(self, message: str = "잘못된 요청입니다.", error_code: str = "INVALID_REQUEST"):
        super().__init__(status_code=400, detail={
            "error_code": error_code,
            "message": message,
        })


class UnauthorizedError(PocketmanError):
    def __init__(self, message: str = "인증이 필요합니다.", error_code: str = "UNAUTHORIZED"):
        super().__init__(status_code=401, detail={
            "error_code": error_code,
            "message": message,
        })


class ForbiddenError(PocketmanError):
    def __init__(self, message: str = "접근 권한이 없습니다.", error_code: str = "FORBIDDEN"):
        super().__init__(status_code=403, detail={
            "error_code": error_code,
            "message": message,
        })


class ConflictError(PocketmanError):
    def __init__(self, message: str = "이미 존재하는 리소스입니다.", error_code: str = "CONFLICT"):
        super().__init__(status_code=409, detail={
            "error_code": error_code,
            "message": message,
        })
