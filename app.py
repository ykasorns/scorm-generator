import streamlit as st
import os
import zipfile
import io
import json
import base64
from datetime import datetime
from scorm.models import Project, ScormSettings, Module, TimelineItem
from scorm.builder import build_scorm_package
from scorm.persistence import save_project_zip, load_project_zip
from uuid import uuid4


st.set_page_config(page_title="SCORM Course Builder Pro", page_icon="🎓", layout="wide")

# ==========================================
# 🏗️ APP LOGIC
# ==========================================

if 'timeline' not in st.session_state:
    st.session_state['timeline'] = []
if 'settings' not in st.session_state:
    st.session_state['settings'] = {"title": "Security Awareness Training", "color": "#D2836C", "pass": 80, "edition": "1.2"}

st.session_state['settings'].setdefault("edition", "1.2")
st.session_state.setdefault('editing_index', None)

logo_file = None
st.session_state.setdefault("logo_file_obj", None)

class FakeUploadFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data
    def getvalue(self):
        return self._data

def move_item(index, direction):
    if direction == 'up' and index > 0:
        st.session_state['timeline'][index], st.session_state['timeline'][index-1] = st.session_state['timeline'][index-1], st.session_state['timeline'][index]
    elif direction == 'down' and index < len(st.session_state['timeline']) - 1:
        st.session_state['timeline'][index], st.session_state['timeline'][index+1] = st.session_state['timeline'][index+1], st.session_state['timeline'][index]

def delete_item(index):
    st.session_state['timeline'].pop(index)

def purge_edit_keys(index):
    """Drop any leftover widget state for an edit-form instance so re-entering
    edit mode on this item always starts from its real current values, not a
    previously cancelled draft."""
    prefix = f"edit_{index}_"
    for k in [k for k in st.session_state if k.startswith(prefix)]:
        del st.session_state[k]

def _commit_item(mode, item_index, new_item):
    if mode == "edit":
        st.session_state['timeline'][item_index] = new_item
        purge_edit_keys(item_index)
        st.session_state['editing_index'] = None
        st.success("Saved!")
    else:
        st.session_state['timeline'].append(new_item)
        st.success("Added!")
    st.rerun()

def render_content_form(mode, key_prefix, content_type, prefill=None, item_index=None):
    """Renders the Add/Edit form for one content type. `mode` is "add" or
    "edit"; in edit mode `prefill` is the existing timeline item dict and
    `item_index` is its position (updated in place on submit instead of
    appended)."""
    prefill = prefill or {}
    submit_label = "💾 Save Changes" if mode == "edit" else f"Add {content_type.split(' ')[0]}"

    if content_type == "Video (MP4)":
        v_file = st.file_uploader("Upload Video", type=['mp4'], key=f"{key_prefix}_v_file")
        v_title = st.text_input("Chapter Title", value=prefill.get("title", ""), key=f"{key_prefix}_v_title")
        if prefill.get("filename"):
            st.caption(f"Current file: {prefill['filename']} (leave blank to keep it)")
        sub_file = st.file_uploader("Subtitles (.vtt, optional)", type=['vtt'], key=f"{key_prefix}_v_sub_file")
        if prefill.get("sub_filename"):
            st.caption(f"Current subtitles: {prefill['sub_filename']} (leave blank to keep them)")
        if st.button(submit_label, key=f"{key_prefix}_v_submit"):
            if v_title and (v_file or "file" in prefill):
                new_item = {"type": "video", "title": v_title,
                            "filename": v_file.name if v_file else prefill.get("filename")}
                if v_file:
                    new_item["file"] = v_file
                elif "file" in prefill:
                    new_item["file"] = prefill["file"]
                if sub_file:
                    new_item["sub_file"] = sub_file
                    new_item["sub_filename"] = sub_file.name
                elif "sub_file" in prefill:
                    new_item["sub_file"] = prefill["sub_file"]
                    new_item["sub_filename"] = prefill.get("sub_filename")
                _commit_item(mode, item_index, new_item)
            else:
                st.error("Add a title and a video file.")

    elif content_type == "Quiz":
        q_text = st.text_input("Question", value=prefill.get("question", ""), key=f"{key_prefix}_q_text")
        existing_type = prefill.get("quizType", "single")
        q_type = st.radio("Type", ["Single Choice", "Multiple Choice"],
                           index=0 if existing_type == "single" else 1, key=f"{key_prefix}_q_type")
        existing_options = prefill.get("options", [])
        default_n = len(existing_options) if existing_options else 4
        n_opts = st.number_input("Options Count", 2, 5, default_n, key=f"{key_prefix}_q_n")
        existing_correct = set(prefill.get("correct", []))
        st.caption("Check the box next to each correct answer.")
        options = []
        correct = []
        for i in range(int(n_opts)):
            c1, c2 = st.columns([0.15, 0.85], vertical_alignment="bottom")
            default_opt = existing_options[i] if i < len(existing_options) else ""
            with c2:
                opt = st.text_input(f"Option {i+1}", value=default_opt, key=f"{key_prefix}_q_o_{i}")
            options.append(opt)
            with c1:
                is_correct = st.checkbox(
                    f"Correct — Option {i+1}", value=(i in existing_correct),
                    key=f"{key_prefix}_q_c_{i}", label_visibility="collapsed",
                    help=f"Mark Option {i+1} as correct",
                )
            if is_correct:
                correct.append(i)

        if st.button(submit_label, key=f"{key_prefix}_q_submit"):
            is_single = q_type == "Single Choice"
            if q_text and correct:
                if is_single and len(correct) > 1:
                    st.error("Single Choice can only have 1 correct answer.")
                else:
                    new_item = {"type": "quiz", "question": q_text,
                                "quizType": "single" if is_single else "multiple",
                                "options": options, "correct": correct}
                    _commit_item(mode, item_index, new_item)
            else:
                st.error("Enter a question and mark at least one correct answer.")

    elif content_type == "PDF Document":
        p_file = st.file_uploader("Upload PDF", type=['pdf'], key=f"{key_prefix}_p_file")
        p_title = st.text_input("Document Title", value=prefill.get("title", ""), key=f"{key_prefix}_p_title")
        if prefill.get("filename"):
            st.caption(f"Current file: {prefill['filename']} (leave blank to keep it)")
        if st.button(submit_label, key=f"{key_prefix}_p_submit"):
            if p_title and (p_file or "file" in prefill):
                new_item = {"type": "pdf", "title": p_title,
                            "filename": p_file.name if p_file else prefill.get("filename")}
                if p_file:
                    new_item["file"] = p_file
                elif "file" in prefill:
                    new_item["file"] = prefill["file"]
                _commit_item(mode, item_index, new_item)
            else:
                st.error("Add a title and a PDF file.")

    elif content_type == "Image":
        i_file = st.file_uploader("Upload Image", type=['png', 'jpg'], key=f"{key_prefix}_i_file")
        i_title = st.text_input("Caption/Title", value=prefill.get("title", ""), key=f"{key_prefix}_i_title")
        if prefill.get("filename"):
            st.caption(f"Current file: {prefill['filename']} (leave blank to keep it)")
        if st.button(submit_label, key=f"{key_prefix}_i_submit"):
            if i_file or "file" in prefill:
                new_item = {"type": "image", "title": i_title,
                            "filename": i_file.name if i_file else prefill.get("filename")}
                if i_file:
                    new_item["file"] = i_file
                elif "file" in prefill:
                    new_item["file"] = prefill["file"]
                _commit_item(mode, item_index, new_item)
            else:
                st.error("Add an image file.")

    elif content_type == "Text Block":
        t_title = st.text_input("Header", value=prefill.get("title", ""), key=f"{key_prefix}_t_title")
        t_content = st.text_area("Content Body", value=prefill.get("content", ""), key=f"{key_prefix}_t_content")
        if st.button(submit_label, key=f"{key_prefix}_t_submit"):
            if t_content:
                new_item = {"type": "text", "title": t_title, "content": t_content}
                _commit_item(mode, item_index, new_item)
            else:
                st.error("Add some content.")

def build_assets_and_course_data(timeline):
    assets_map = {}
    js_course_data = []

    for idx, item in enumerate(timeline):
        data_obj = {"type": item["type"]}

        # title/content
        if "title" in item:
            data_obj["title"] = item["title"]
        if "content" in item:
            data_obj["content"] = item["content"]

        # file-based items
        if item["type"] in ["video", "pdf", "image"]:
            clean_name = f"assets/res_{idx}_{item['filename']}"
            assets_map[clean_name] = item["file"].getvalue()
            data_obj["src"] = clean_name

        # optional subtitles (video only)
        if item["type"] == "video" and item.get("sub_file"):
            sub_name = f"assets/res_{idx}_{item['sub_filename']}"
            assets_map[sub_name] = item["sub_file"].getvalue()
            data_obj["subtitleSrc"] = sub_name

        # quiz
        if item["type"] == "quiz":
            data_obj.update({
                "question": item["question"],
                "quizType": item["quizType"],
                "options": item["options"],
                "correct": item["correct"]
            })

        js_course_data.append(data_obj)

    return assets_map, js_course_data

st.title("🎓 SCORM Course Builder Pro")

with st.sidebar:
    st.markdown("## Project ZIP")
    uploaded_zip = st.file_uploader("Load project.zip", type=["zip"], key="project_zip_uploader")

    if uploaded_zip and not st.session_state.get("_just_loaded", False):
        project, assets_map, logo = load_project_zip(uploaded_zip.read())

        st.session_state["project_obj"] = project
        st.session_state["assets_map"] = assets_map
        st.session_state["logo_tuple"] = logo

        st.session_state["settings"] = project.ui_state.get("settings", st.session_state.get("settings", {}))
        st.session_state["timeline"]  = project.ui_state.get("timeline", st.session_state.get("timeline", []))

        # ✅ Reconstruct file objects from zip assets
        for idx, item in enumerate(st.session_state["timeline"]):
            if item.get("type") in ["video", "pdf", "image"] and "file" not in item:
                asset_path = f"assets/res_{idx}_{item['filename']}"
                if asset_path in assets_map:
                    item["file"] = FakeUploadFile(item["filename"], assets_map[asset_path])
            if item.get("type") == "video" and item.get("sub_filename") and "sub_file" not in item:
                sub_asset_path = f"assets/res_{idx}_{item['sub_filename']}"
                if sub_asset_path in assets_map:
                    item["sub_file"] = FakeUploadFile(item["sub_filename"], assets_map[sub_asset_path])

        st.session_state["_just_loaded"] = True
        st.success("Project loaded ✅")
        st.rerun()

    st.divider()

    st.header("📂 Project Management")
    col_save, col_load = st.columns(2)
    with col_save:
        if st.button("💾 Save Project", use_container_width=True):
        # 1) Convert timeline -> assets_map + js_course_data
            assets_map, js_course_data = build_assets_and_course_data(st.session_state["timeline"])

        # 2) logo tuple
            logo_tuple = None
            logo_file_obj = st.session_state.get("logo_file_obj")
            if logo_file_obj:
                logo_tuple = (f"logo/{logo_file_obj.name}", logo_file_obj.getvalue())

        # 3) edition
            edition = st.session_state["settings"].get("edition", "1.2")

        # 4) Build Project object for persistence
            project = Project(
                title=st.session_state["settings"]["title"],
                description="",
                language="en",
                version="1.0.0",
                scorm=ScormSettings(
                    edition=edition,
                    masteryScore=int(st.session_state["settings"]["pass"])
                ),
                structure=[
                    Module(
                        id="m1",
                        title="Course",
                        items=[
                            TimelineItem(
                                id=f"i{idx}",
                                type="page",
                                title=(it.get("title") or it.get("question") or f"Item {idx+1}")
                            )
                            for idx, it in enumerate(st.session_state["timeline"])
                        ]
                    )
                ],
                ui_state={
                    "settings": st.session_state["settings"],
                    "timeline": [{k: v for k, v in it.items() if k not in ("file", "sub_file")} for it in st.session_state["timeline"]],
                    "js_course_data": js_course_data,
                }
            )

            # 5) Save -> bytes
            project_zip_bytes = save_project_zip(project, assets_map, logo_tuple)

            # 6) Download button
            st.download_button(
                "⬇️ Download project.zip",
                data=project_zip_bytes,
                file_name="project.zip",
                mime="application/zip",
                use_container_width=True
            )

    st.divider()
    st.header("🛠️ Content Creator")
    
    with st.expander("⚙️ Course Settings", expanded=True):
        st.session_state['settings']['title'] = st.text_input("Course Title", st.session_state['settings']['title'], max_chars=60)
        st.session_state['settings']['color'] = st.color_picker("Theme Color", st.session_state['settings']['color'])
        st.session_state['settings']['pass'] = st.number_input("Passing Score (%)", 0, 100, st.session_state['settings']['pass'])
        st.session_state['settings']['edition'] = st.selectbox(
            "SCORM Edition",
            ["1.2", "2004"],
            index=0 if st.session_state['settings'].get("edition", "1.2") == "1.2" else 1
        )
        logo_file = st.file_uploader("Logo (PNG/JPG)", type=['png', 'jpg'], key="logo_uploader")
        st.session_state["logo_file_obj"] = logo_file

    st.divider()
    
    editing_index = st.session_state.get('editing_index')
    type_label_map = {"video": "Video (MP4)", "quiz": "Quiz", "pdf": "PDF Document",
                       "image": "Image", "text": "Text Block"}

    if editing_index is not None and 0 <= editing_index < len(st.session_state['timeline']):
        edit_item = st.session_state['timeline'][editing_index]
        ct_label = type_label_map.get(edit_item["type"], "Text Block")
        st.info(f"✏️ Editing item #{editing_index + 1} ({ct_label})")
        if st.button("✖ Cancel Edit"):
            purge_edit_keys(editing_index)
            st.session_state['editing_index'] = None
            st.rerun()
        render_content_form("edit", f"edit_{editing_index}", ct_label,
                             prefill=edit_item, item_index=editing_index)
    else:
        content_type = st.selectbox("Content Type", ["Video (MP4)", "Quiz", "PDF Document", "Image", "Text Block"])
        render_content_form("add", "add", content_type)

    st.divider()
    if st.button("🗑️ Clear All", type="primary"):
        st.session_state['timeline'] = []
        st.rerun()

# --- MAIN PREVIEW ---
st.subheader(f"📜 Timeline ({len(st.session_state['timeline'])} items)")

editing_index = st.session_state.get('editing_index')

if not st.session_state['timeline']:
    st.info("No content yet.")
else:
    for i, item in enumerate(st.session_state['timeline']):
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([0.5, 0.1, 0.1, 0.1, 0.1])
            icon = {"video":"🎬", "quiz":"❓", "pdf":"📄", "image":"🖼️", "text":"📝"}.get(item['type'], "blob")
            title = item.get('title') or item.get('question') or "Untitled"

            locked = editing_index is not None
            is_being_edited = (editing_index == i)

            # --- ✅ FIX RE-UPLOAD LOGIC (NO RERUN) ---
            file_status = ""
            if item['type'] in ['video', 'pdf', 'image'] and 'file' not in item:
                file_status = "⚠️ (Re-upload needed)"

            label = f"**{i+1}. {icon} {title}** {file_status}"
            if is_being_edited:
                label += " — ✏️ editing below"
            col1.markdown(label)

            if file_status and not is_being_edited:
                re_file = col1.file_uploader(f"Upload {item['filename']}", type=['mp4', 'pdf', 'png', 'jpg'], key=f"reup_{i}", disabled=locked)
                if re_file:
                    st.session_state['timeline'][i]['file'] = re_file
                    st.success("✅ Saved! (Click any button to refresh UI)")
            # -------------------------------------------

            if col2.button("✏️", key=f"edit_{i}", disabled=locked):
                purge_edit_keys(i)
                st.session_state['editing_index'] = i
                st.rerun()
            if col3.button("⬆️", key=f"up_{i}", disabled=(i==0) or locked): move_item(i, 'up'); st.rerun()
            if col4.button("⬇️", key=f"down_{i}", disabled=(i==len(st.session_state['timeline'])-1) or locked): move_item(i, 'down'); st.rerun()
            if col5.button("🗑️", key=f"del_{i}", disabled=locked): delete_item(i); st.rerun()
            st.divider()

# --- EXPORT (NEW BUILDER) ---
files_missing = any(
    item['type'] in ['video', 'pdf', 'image'] and 'file' not in item
    for item in st.session_state['timeline']
)

if files_missing:
    st.warning("⚠️ Please re-upload missing files before exporting.")
else:
    if st.button("🚀 Export SCORM Package (.zip)", type="primary", use_container_width=True):
        with st.spinner("Packaging with new builder..."):

            # 1) Convert timeline -> assets_map + js_course_data
            assets_map, js_course_data = build_assets_and_course_data(st.session_state["timeline"])

            # 2) logo -> store in /logo
            logo_tuple = None
            if logo_file:
                logo_tuple = (f"logo/{logo_file.name}", logo_file.getvalue())

            # 3) edition (from settings)
            edition = st.session_state["settings"].get("edition", "1.2")

            # 4) Build Project object (A = store everything)
            project = Project(
                title=st.session_state["settings"]["title"],
                description="",
                language="en",
                version="1.0.0",
                scorm=ScormSettings(
                    edition=edition,
                    masteryScore=int(st.session_state["settings"]["pass"])
                ),
                structure=[
                    Module(
                        id="m1",
                        title="Course",
                        items=[
                            TimelineItem(
                                id=f"i{idx}",
                                type="page",
                                title=(it.get("title") or it.get("question") or f"Item {idx+1}")
                            )
                            for idx, it in enumerate(st.session_state["timeline"])
                        ]
                    )
                ],
                ui_state={
                    "settings": st.session_state["settings"],
                    "timeline": [{k: v for k, v in it.items() if k not in ("file", "sub_file")} for it in st.session_state["timeline"]],
                    "js_course_data": js_course_data,  # ✅ ให้ builder ใช้ render HTML
                }
            )

            # 5) Build SCORM package ZIP using new builder
            zip_bytes = build_scorm_package(project, assets_map, logo=logo_tuple, warn=st.warning)

            st.success("Export Successful! ✅")
            st.download_button(
                "⬇️ Download ZIP",
                data=zip_bytes,
                file_name=f"Course_{uuid4().hex[:8]}.zip",
                mime="application/zip"
            )
