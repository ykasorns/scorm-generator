import zipfile, io
from scorm.models import Project, Module, TimelineItem, ScormSettings
from scorm.builder import build_scorm_package

def demo_project(edition="2004"):
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
        ui_state={"theme":"dark"}  # A: store everything
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
