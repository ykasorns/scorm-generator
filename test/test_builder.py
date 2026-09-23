import zipfile, io
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
    zf = zipfile.ZipFile(io.BytesIO(z))
    names = set(zf.namelist())
    assert "index.html" in names
    assert "imsmanifest.xml" in names
    assert "assets/intro.mp4" in names

def test_build_scorm_12_zip():
    z = build_scorm_package(demo_project("1.2"), {"assets/cover.png": b"123"})
    zf = zipfile.ZipFile(io.BytesIO(z))
    names = set(zf.namelist())
    assert "assets/cover.png" in names

def test_index_html_contains_resume_scaffolding():
    z = build_scorm_package(demo_project("1.2"), {})
    zf = zipfile.ZipFile(io.BytesIO(z))
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
