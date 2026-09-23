import zipfile
from scorm.models import Project, Module, TimelineItem, ScormSettings
from scorm.builder import build_scorm_package, _compute_course_fingerprint

def demo_project(edition="2004", js_course_data=None):
    return Project(
        title="Demo",
        description="Test",
        language="en",
        version="1.0.0",
        scorm=ScormSettings(edition=edition),
        structure=[
            Module(id="m1", title="Module 1",
                   items=[TimelineItem(id="p1", type="page", title="Welcome", content="Hello")])
        ],
        ui_state={"theme": "dark", "js_course_data": js_course_data or []}  # A: store everything
    )

def test_build_scorm_2004_zip():
    z = build_scorm_package(demo_project("2004"), {"assets/intro.mp4": b"123"})
    zf = zipfile.ZipFile(z)
    names = set(zf.namelist())
    assert "index.html" in names
    assert "imsmanifest.xml" in names
    assert "assets/intro.mp4" in names

def test_build_scorm_12_zip():
    z = build_scorm_package(demo_project("1.2"), {"assets/cover.png": b"123"})
    zf = zipfile.ZipFile(z)
    names = set(zf.namelist())
    assert "assets/cover.png" in names

def test_index_html_contains_resume_scaffolding():
    z = build_scorm_package(demo_project("1.2"), {})
    zf = zipfile.ZipFile(z)
    html = zf.read("index.html").decode("utf-8")
    assert "courseFingerprint" in html
    assert "cmi.suspend_data" in html
    assert "persistProgress" in html
    assert "restoreProgress" in html

def test_fingerprint_ignores_text_but_catches_shape():
    a = [{"type": "quiz", "question": "Q1?", "options": ["a", "b"]}]
    b = [{"type": "quiz", "question": "A totally different question?", "options": ["a", "b"]}]
    c = [{"type": "quiz", "question": "Q1?", "options": ["a", "b", "c"]}]
    assert _compute_course_fingerprint(a) == _compute_course_fingerprint(b)
    assert _compute_course_fingerprint(a) != _compute_course_fingerprint(c)

def test_suspend_data_budget_warning_fires_for_large_courses():
    big_course = [{"type": "text", "title": f"Item {i}"} for i in range(2000)]
    warnings = []
    build_scorm_package(demo_project("1.2", js_course_data=big_course), {}, warn=warnings.append)
    assert len(warnings) == 1
    assert "suspend_data" in warnings[0]

def test_suspend_data_budget_warning_silent_for_small_courses():
    small_course = [{"type": "text", "title": f"Item {i}"} for i in range(10)]
    warnings = []
    build_scorm_package(demo_project("1.2", js_course_data=small_course), {}, warn=warnings.append)
    assert warnings == []

def test_suspend_data_budget_warning_respects_guard_toggle():
    big_course = [{"type": "text", "title": f"Item {i}"} for i in range(2000)]
    project = demo_project("1.2", js_course_data=big_course)
    project.scorm.suspendDataLimitGuard = False
    warnings = []
    build_scorm_package(project, {}, warn=warnings.append)
    assert warnings == []

class _ChunkOnlyReader:
    """
    File-like stub standing in for a large Streamlit UploadedFile. Raises if
    anything ever asks it to read the whole thing in one call (size=-1 or no
    size), proving the builder streams assets in bounded chunks rather than
    materializing them as a single bytes blob.
    """
    def __init__(self, total_size: int, chunk_size: int = 1024 * 1024):
        self._remaining = total_size
        self._chunk_size = chunk_size

    def seek(self, pos):
        assert pos == 0

    def read(self, size=-1):
        if size is None or size < 0:
            raise AssertionError("asset was read in one unbounded call, not streamed in chunks")
        if size > self._chunk_size * 2:
            raise AssertionError(f"read() requested {size} bytes, larger than expected chunk size")
        n = min(size, self._remaining)
        self._remaining -= n
        return b"\x00" * n

def test_large_video_asset_is_streamed_not_fully_buffered():
    fake_video = _ChunkOnlyReader(total_size=5 * 1024 * 1024)  # 5MB, several chunks at 1MB/read
    z = build_scorm_package(demo_project("1.2"), {"assets/big.mp4": fake_video})
    zf = zipfile.ZipFile(z)
    info = zf.getinfo("assets/big.mp4")
    assert info.file_size == 5 * 1024 * 1024
