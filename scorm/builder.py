import io, zipfile, json
from typing import Dict, Optional, Tuple
from uuid import uuid4

from .models import Project
from .validate import validate_assets_map
from .templates import HTML_TEMPLATE, MANIFEST_TEMPLATE_SCORM12, MANIFEST_TEMPLATE_SCORM2004


def _resource_files_xml(asset_paths):
    # keep it single-line-ish like your old manifest style
    return "".join([f'<file href="{p}"/>' for p in sorted(asset_paths)])


def _render_index_html(project: Project) -> str:
    """
    Render index.html using YOUR HTML_TEMPLATE placeholders:
      {course_title}, {theme_color}, {passing_score}, {logo_html}, {logo_html_large},
      {course_data_json}, {has_quiz}, {scorm_edition}
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

    # IMPORTANT: js_course_data must be JSON array of items like your old js_course_data
    course_data_json = json.dumps(js_course_data, ensure_ascii=False)
    scorm_edition = json.dumps(project.scorm.edition)

    # Use .format exactly like your original HTML_TEMPLATE
    return HTML_TEMPLATE.format(
        course_title=course_title,
        theme_color=theme_color,
        passing_score=passing_score,
        logo_html=logo_html,
        logo_html_large=logo_html_large,
        course_data_json=course_data_json,
        has_quiz=has_quiz,
        scorm_edition=scorm_edition
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
    assets: Dict[str, bytes],
    logo: Optional[Tuple[str, bytes]] = None,
) -> bytes:
    """
    build_zip(payload, assets, logo) -> bytes
    """
    assets = validate_assets_map(assets)

    # attach logo into zip assets and store path so HTML can reference it
    if logo:
        lp, lb = logo
        assets[lp] = lb
        project.ui_state["logo_meta"] = {"path": lp}

    asset_paths = list(assets.keys())

    index_html = _render_index_html(project)
    manifest_xml = _render_manifest(project, asset_paths)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", index_html)
        zf.writestr("imsmanifest.xml", manifest_xml)
        for p in sorted(assets.keys()):
            zf.writestr(p, assets[p])

    buf.seek(0)
    return buf.getvalue()
