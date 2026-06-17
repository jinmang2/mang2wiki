from mang2wiki.models import Status


def test_in_progress_display_value():
    assert Status.IN_PROGRESS.value == "검토 대기 중"


def test_coerce_legacy_and_new():
    assert Status.coerce("분석 중") is Status.IN_PROGRESS       # legacy Notion 표기
    assert Status.coerce("검토 대기 중") is Status.IN_PROGRESS   # 새 표기
    assert Status.coerce("in progress") is Status.IN_PROGRESS
    assert Status.coerce("doing") is Status.IN_PROGRESS


def test_coerce_unchanged_values():
    assert Status.coerce("시작 전") is Status.TODO
    assert Status.coerce("완료") is Status.DONE
    assert Status.coerce(None) is Status.TODO
    assert Status.coerce("아무거나") is Status.TODO
