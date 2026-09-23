from pathlib import Path
import re
import sys

def extract_triple_quote(src: str, varname: str) -> str:
    m = re.search(rf"{varname}\s*=\s*\"\"\"(.*?)\"\"\"", src, re.S)
    if not m:
        raise ValueError(f"Cannot find {varname} in file")
    return m.group(1)

def scorm12_to_scorm2004(manifest_12: str) -> str:
    """
    quick conversion for production-ish usage:
    - switches namespaces to SCORM 2004
    - changes adlcp:scormtype -> adlcp:scormType
    This won't capture all advanced sequencing rules, but works for most single-SCO packages.
    """
    m = manifest_12

    # Replace SCORM 1.2 namespaces with SCORM 2004 namespaces
    m = re.sub(r'xmlns="http://www\.imsproject\.org/xsd/imscp_rootv1p1p2"',
               'xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"', m)

    m = re.sub(r'xmlns:adlcp="http://www\.adlnet\.org/xsd/adlcp_rootv1p2"',
               'xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3"', m)

    # Inject common SCORM2004 namespaces if missing
    if "xmlns:imsss" not in m:
        m = m.replace(
            'xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3"',
            'xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3"\n'
            '    xmlns:adlseq="http://www.adlnet.org/xsd/adlseq_v1p3"\n'
            '    xmlns:adlnav="http://www.adlnet.org/xsd/adlnav_v1p3"\n'
            '    xmlns:imsss="http://www.imsglobal.org/xsd/imsss"'
        )

    # schemaLocation: replace with SCORM2004-ish
    m = re.sub(
        r'xsi:schemaLocation="[^"]+"',
        'xsi:schemaLocation="http://www.imsglobal.org/xsd/imscp_v1p1 imscp_v1p1.xsd '
        'http://www.adlnet.org/xsd/adlcp_v1p3 adlcp_v1p3.xsd '
        'http://www.imsglobal.org/xsd/imsss imsss_v1p0.xsd"',
        m
    )

    # scormtype attr casing
    m = m.replace("adlcp:scormtype", "adlcp:scormType")

    # manifest version
    m = re.sub(r'version="1\.2"', 'version="1.0"', m)

    return m

def main():
    if "--force" not in sys.argv:
        raise SystemExit(
            "scorm/templates.py is now hand-maintained (SCORM 1.2 + 2004 "
            "runtime fixes live there, not in scorm2.py). Regenerating it "
            "from scorm2.py would silently overwrite those fixes. "
            "Re-run with --force if you really intend to discard them."
        )

    # adjust path if needed
    src_path = Path("scorm2.py")
    if not src_path.exists():
        raise SystemExit("scorm2.py not found in project root")

    src = src_path.read_text(encoding="utf-8")

    html = extract_triple_quote(src, "HTML_TEMPLATE")
    manifest_12 = extract_triple_quote(src, "MANIFEST_TEMPLATE")
    manifest_2004 = scorm12_to_scorm2004(manifest_12)

    out = Path("scorm/templates.py")
    out.parent.mkdir(parents=True, exist_ok=True)

    out.write_text(
        "# Auto-generated from scorm2.py\n\n"
        "HTML_TEMPLATE = '''" + html.replace("'''", "''\\'") + "'''\n\n"
        "MANIFEST_TEMPLATE_SCORM12 = '''" + manifest_12.replace("'''", "''\\'") + "'''\n\n"
        "MANIFEST_TEMPLATE_SCORM2004 = '''" + manifest_2004.replace("'''", "''\\'") + "'''\n",
        encoding="utf-8"
    )

    print("✅ Generated scorm/templates.py from scorm2.py")

if __name__ == "__main__":
    main()
