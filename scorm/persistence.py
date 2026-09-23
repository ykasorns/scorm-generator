import io, zipfile, json, tempfile
from typing import Dict, Optional, Tuple, Union, BinaryIO
from .models import Project
from .zipio import write_asset, AssetData

PROJECT_JSON = "project.json"

# Zips smaller than this stay fully in memory (fast); larger ones spill to a
# temp file on disk automatically, so a 300-600MB course doesn't require
# holding the whole compressed archive in RAM at once.
SPOOL_THRESHOLD_BYTES = 50 * 1024 * 1024


def save_project_zip(project, assets_map: Dict[str, AssetData], logo_tuple=None, bg_image_tuple=None):
    tmp = tempfile.SpooledTemporaryFile(max_size=SPOOL_THRESHOLD_BYTES)
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:

        # ✅ สำคัญมาก: บังคับ snake_case
        project_dict = project.model_dump(by_alias=False)

        zf.writestr(PROJECT_JSON, json.dumps(project_dict, ensure_ascii=False, indent=2))

        for path, data in assets_map.items():
            write_asset(zf, path, data)

        if logo_tuple:
            lp, lb = logo_tuple
            write_asset(zf, lp, lb)

        if bg_image_tuple:
            bp, bb = bg_image_tuple
            write_asset(zf, bp, bb)

    tmp.seek(0)
    return tmp


def load_project_zip(source: Union[bytes, BinaryIO]):
    with zipfile.ZipFile(source, "r") as zf:
        project_data = json.loads(zf.read(PROJECT_JSON).decode("utf-8"))

        project = Project.model_validate(project_data)  # ✅ validate dict ตรงๆ

        assets_map = {p: zf.read(p) for p in zf.namelist() if p.startswith("assets/")}

        logo_tuple = None
        bg_image_tuple = None
        for p in zf.namelist():
            if p.startswith("logo/") and logo_tuple is None:
                logo_tuple = (p, zf.read(p))
            elif p.startswith("background/") and bg_image_tuple is None:
                bg_image_tuple = (p, zf.read(p))

    return project, assets_map, logo_tuple, bg_image_tuple
