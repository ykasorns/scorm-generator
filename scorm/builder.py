import hashlib, tempfile, zipfile, json
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple
from uuid import uuid4

from .models import Project
from .validate import validate_assets_map
from .templates import HTML_TEMPLATE, MANIFEST_TEMPLATE_SCORM12, MANIFEST_TEMPLATE_SCORM2004
from .zipio import write_asset, AssetData

# Zips smaller than this stay fully in memory (fast); larger ones spill to a
# temp file on disk automatically, so a 300-600MB course doesn't require
# holding the whole compressed archive in RAM at once.
SPOOL_THRESHOLD_BYTES = 50 * 1024 * 1024

_FONTS_DIR = Path(__file__).parent / "assets" / "fonts"


def _bundled_font_assets() -> Dict[str, bytes]:
    """
    Self-hosted Thai-supporting webfont (Sarabun, OFL-licensed -- see
    scorm/assets/fonts/OFL.txt), shipped inside every export at fonts/*.woff2
    so the course renders correctly on an intranet with no internet egress
    and displays Thai script, which the CDN-hosted "Inter" font this replaced
    could not.
    """
    return {
        f"fonts/{p.name}": p.read_bytes()
        for p in sorted(_FONTS_DIR.glob("*.woff2"))
    }

# Worst-case cmi.suspend_data resume-payload length for an N-item course
# (see scorm/templates.py's persistProgress(): "v|fp|cs|ps|qr", ps/qr are one
# char per item). Must stay well under SCORM 1.2's 4096-char cap.
SUSPEND_DATA_PER_ITEM_CHARS = 2
SUSPEND_DATA_FIXED_OVERHEAD_CHARS = 19
SUSPEND_DATA_WARN_THRESHOLD_CHARS = 3500


def _resource_files_xml(asset_paths):
    # keep it single-line-ish like your old manifest style
    return "".join([f'<file href="{p}"/>' for p in sorted(asset_paths)])


def _compute_course_fingerprint(js_course_data) -> str:
    """
    Structural fingerprint used by the exported player to detect when a
    learner's resume payload no longer matches the course (items added,
    removed, or reordered). Deliberately excludes title/question/option TEXT
    so routine copy edits don't reset in-flight learners -- only shape
    (item count, per-item type, and quiz option-count) is hashed.
    """
    parts = []
    for item in js_course_data:
        item_type = item.get("type", "")
        if item_type == "quiz":
            parts.append(f"{item_type}:{len(item.get('options', []))}")
        else:
            parts.append(item_type)
    shape = ",".join(parts)
    return hashlib.sha256(shape.encode("utf-8")).hexdigest()[:8]


def _render_index_html(project: Project) -> str:
    """
    Render index.html using YOUR HTML_TEMPLATE placeholders:
      {course_title}, {theme_color}, {passing_score}, {logo_html}, {logo_html_large},
      {course_data_json}, {has_quiz}, {scorm_edition}, {course_fingerprint}, {bg_image_css}
    """
    settings = project.ui_state.get("settings", {})
    js_course_data = project.ui_state.get("js_course_data", [])

    course_title = project.title
    theme_color = settings.get("color", "#D2836C")
    passing_score = settings.get("pass", project.scorm.masteryScore)

    has_quiz = "true" if any(x.get("type") == "quiz" for x in js_course_data) else "false"

    # logo support
    logo_html = ""
    logo_html_large = ""

    logo_meta = project.ui_state.get("logo_meta")
    if logo_meta and logo_meta.get("path"):
        # same as your old app.py
        lp = logo_meta["path"]
        logo_html = f'<img src="{lp}">'
        logo_html_large = (
            f'<div style="background-color:{theme_color} !important; -webkit-print-color-adjust: exact; '
            f'padding:20px; border-radius:10px; display:inline-block; margin-bottom:20px;">'
            f'<img src="{lp}" style="height:60px; display:block;"></div>'
        )

    # background image support -- background-size:cover + background-position:center
    # is what makes ONE uploaded image work across any screen size: the browser scales
    # it to always fill the element, cropping overflow instead of stretching it, and
    # keeps the center anchored so cropping doesn't cut out the important part.
    # background-attachment is deliberately left at the default ("scroll"), not "fixed"
    # -- "fixed" backgrounds are unreliable/janky on iOS Safari.
    bg_image_css = ""
    bg_image_meta = project.ui_state.get("bg_image_meta")
    if bg_image_meta and bg_image_meta.get("path"):
        bp = bg_image_meta["path"]
        bg_image_css = (
            f"background-image: url('{bp}'); background-size: cover; "
            f"background-position: center; background-repeat: no-repeat;"
        )

    # IMPORTANT: js_course_data must be JSON array of items like your old js_course_data
    course_data_json = json.dumps(js_course_data, ensure_ascii=False)
    scorm_edition = json.dumps(project.scorm.edition)
    course_fingerprint = json.dumps(_compute_course_fingerprint(js_course_data))

    # Use .format exactly like your original HTML_TEMPLATE
    return HTML_TEMPLATE.format(
        course_title=course_title,
        theme_color=theme_color,
        passing_score=passing_score,
        logo_html=logo_html,
        logo_html_large=logo_html_large,
        course_data_json=course_data_json,
        has_quiz=has_quiz,
        scorm_edition=scorm_edition,
        course_fingerprint=course_fingerprint,
        bg_image_css=bg_image_css
    )


def _render_manifest(project: Project, asset_paths):
    """
    Render manifest for SCORM 1.2 or 2004.
    We support both placeholder styles:
      - style A: {id}, {title}, {resource_files}
      - style B: {course_title}, {resource_files}, {mastery_score}
    """
    rf = _resource_files_xml(asset_paths)
    unique_id = uuid4().hex[:14]

    template = MANIFEST_TEMPLATE_SCORM12 if project.scorm.edition == "1.2" else MANIFEST_TEMPLATE_SCORM2004

    # Try old style first (matches your original app.py)
    try:
        return template.format(
            id=unique_id,
            title=project.title,
            resource_files=rf
        )
    except KeyError:
        # fallback style (matches earlier generic builder)
        return template.format(
            course_title=project.title,
            resource_files=rf,
            mastery_score=project.scorm.masteryScore
        )


def build_scorm_package(
    project: Project,
    assets: Dict[str, AssetData],
    logo: Optional[Tuple[str, bytes]] = None,
    bg_image: Optional[Tuple[str, bytes]] = None,
    warn: Optional[Callable[[str], None]] = None,
):
    """
    build_zip(payload, assets, logo) -> a seekable, seeked-to-0 binary file
    object containing the SCORM zip (a tempfile.SpooledTemporaryFile).

    Returns a file object rather than raw bytes, and `assets` values may be
    file-like objects (e.g. a Streamlit UploadedFile) rather than bytes --
    both let a 300-600MB video stream through in chunks instead of being
    fully materialized in memory, which the old bytes-in/bytes-out signature
    could not avoid. Callers can pass the result straight to
    st.download_button(data=...) or read/seek it like any other file object.

    `warn`, if given, is called with a human-readable message if
    ScormSettings.suspendDataLimitGuard is on and the course is large enough
    that the resume-progress payload (see scorm/templates.py's
    persistProgress()) could approach SCORM 1.2's 4096-char suspend_data cap.
    This module has no UI dependency, so the caller decides how to surface it
    (e.g. app.py rendering it via st.warning).
    """
    assets = validate_assets_map(assets)
    assets.update(_bundled_font_assets())

    # attach logo into zip assets and store path so HTML can reference it
    if logo:
        lp, lb = logo
        assets[lp] = lb
        project.ui_state["logo_meta"] = {"path": lp}

    # attach background image into zip assets and store path so HTML can reference it
    if bg_image:
        bp, bb = bg_image
        assets[bp] = bb
        project.ui_state["bg_image_meta"] = {"path": bp}

    if warn and project.scorm.suspendDataLimitGuard:
        item_count = len(project.ui_state.get("js_course_data", []))
        estimated_chars = SUSPEND_DATA_PER_ITEM_CHARS * item_count + SUSPEND_DATA_FIXED_OVERHEAD_CHARS
        if estimated_chars > SUSPEND_DATA_WARN_THRESHOLD_CHARS:
            warn(
                f"This course has {item_count} items; the estimated resume-progress "
                f"payload (~{estimated_chars} chars) is approaching the SCORM 1.2 "
                f"suspend_data limit (4096 chars). Consider splitting into multiple "
                f"SCOs/courses."
            )

    asset_paths = list(assets.keys())

    index_html = _render_index_html(project)
    manifest_xml = _render_manifest(project, asset_paths)

    tmp = tempfile.SpooledTemporaryFile(max_size=SPOOL_THRESHOLD_BYTES)
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", index_html)
        zf.writestr("imsmanifest.xml", manifest_xml)
        for p in sorted(assets.keys()):
            write_asset(zf, p, assets[p])

    tmp.seek(0)
    return tmp
