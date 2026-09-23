import io, zipfile, json
from typing import Dict, Optional, Tuple
from .models import Project

PROJECT_JSON = "project.json"

def save_project_zip(project, assets_map, logo_tuple=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:

        # ✅ สำคัญมาก: บังคับ snake_case
        project_dict = project.model_dump(by_alias=False)

        zf.writestr(PROJECT_JSON, json.dumps(project_dict, ensure_ascii=False, indent=2))

        for path, data in assets_map.items():
            zf.writestr(path, data)

        if logo_tuple:
            lp, lb = logo_tuple
            zf.writestr(lp, lb)

    buf.seek(0)
    return buf.getvalue()


def load_project_zip(zip_bytes: bytes):
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        project_data = json.loads(zf.read(PROJECT_JSON).decode("utf-8"))

        project = Project.model_validate(project_data)  # ✅ validate dict ตรงๆ

        assets_map = {p: zf.read(p) for p in zf.namelist() if p.startswith("assets/")}

        logo_tuple = None
        for p in zf.namelist():
            if p.startswith("logo/"):
                logo_tuple = (p, zf.read(p))
                break

    return project, assets_map, logo_tuple
