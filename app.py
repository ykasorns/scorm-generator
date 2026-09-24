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
    st.session_state['settings'] = {"title": "Untitled Course", "color": "#D2836C", "pass": 80, "edition": "1.2"}

st.session_state['settings'].setdefault("edition", "1.2")
st.session_state.setdefault('editing_index', None)
st.session_state.setdefault('adding_new', False)
st.session_state.setdefault('add_form_gen', 0)
st.session_state.setdefault('edit_form_gen', 0)
st.session_state.setdefault('item_filter', "")
st.session_state.setdefault('item_page', 0)

ITEMS_PER_PAGE = 15
TITLE_TRUNCATE_CHARS = 80

def truncate_title(text, limit=TITLE_TRUNCATE_CHARS):
    text = text or ""
    return text if len(text) <= limit else text[:limit].rstrip() + "…"

logo_file = None
st.session_state.setdefault("logo_file_obj", None)
bg_image_file = None
st.session_state.setdefault("bg_image_file_obj", None)

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

def _commit_item(mode, item_index, new_item):
    if mode == "edit":
        st.session_state['timeline'][item_index] = new_item
        st.session_state['edit_form_gen'] += 1  # next edit (even of this same item) gets fresh widget keys
        st.session_state['editing_index'] = None
        st.success("Saved!")
    else:
        st.session_state['timeline'].append(new_item)
        st.session_state['add_form_gen'] += 1  # forces brand-new widget keys, so the form visibly resets
        st.success(f"Added! ({len(st.session_state['timeline'])} items in course so far)")
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
        if v_file:
            st.video(v_file)
        if st.button(submit_label, key=f"{key_prefix}_v_submit", type="primary"):
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
            c1, c2 = st.columns([0.08, 0.92], vertical_alignment="bottom")
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

        if st.button(submit_label, key=f"{key_prefix}_q_submit", type="primary"):
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
        if st.button(submit_label, key=f"{key_prefix}_p_submit", type="primary"):
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
        if i_file:
            st.image(i_file)
        if st.button(submit_label, key=f"{key_prefix}_i_submit", type="primary"):
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
        t_content = st.text_area("Content Body", value=prefill.get("content", ""), key=f"{key_prefix}_t_content", height=180)
        if t_title or t_content:
            with st.container(border=True):
                st.caption("Preview")
                if t_title:
                    st.markdown(f"#### {t_title}")
                st.write(t_content)
        if st.button(submit_label, key=f"{key_prefix}_t_submit", type="primary"):
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

        # file-based items -- pass the file-like object through as-is (not
        # .getvalue()) so a large video streams into the zip in chunks later
        # instead of being fully duplicated in memory here.
        if item["type"] in ["video", "pdf", "image"]:
            clean_name = f"assets/res_{idx}_{item['filename']}"
            assets_map[clean_name] = item["file"]
            data_obj["src"] = clean_name

        # optional subtitles (video only)
        if item["type"] == "video" and item.get("sub_file"):
            sub_name = f"assets/res_{idx}_{item['sub_filename']}"
            assets_map[sub_name] = item["sub_file"]
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

# ==========================================
# 🎨 THEME-AWARE STYLING
# ==========================================
_theme_color = st.session_state['settings'].get('color', '#D2836C')
st.markdown(f"""
<style>
    .block-container {{ padding-top: 2rem; }}
    div[data-testid="stButton"] > button[kind="primary"] {{
        background-color: {_theme_color};
        border-color: {_theme_color};
    }}
    div[data-testid="stButton"] > button[kind="primary"]:hover {{
        opacity: 0.88;
        border-color: {_theme_color};
    }}
    section[data-testid="stSidebar"] {{
        border-right: 1px solid rgba(49, 51, 63, 0.1);
    }}
    div[data-testid="stMetric"] {{
        background-color: rgba(49, 51, 63, 0.03);
        border-radius: 8px;
        padding: 12px 4px;
    }}
</style>
""", unsafe_allow_html=True)

TYPE_LABEL_MAP = {"video": "Video (MP4)", "quiz": "Quiz", "pdf": "PDF Document",
                   "image": "Image", "text": "Text Block"}
TYPE_ICON_MAP = {"video": "🎬", "quiz": "❓", "pdf": "📄", "image": "🖼️", "text": "📝"}

# ==========================================
# 🧭 SIDEBAR -- compact navigator, not a workbench
# ==========================================
with st.sidebar:
    s = st.session_state['settings']
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;padding:4px 0 16px 0;">
            <div style="width:30px;height:30px;border-radius:7px;background:{s['color']};
                        border:1px solid rgba(0,0,0,0.12);flex-shrink:0;"></div>
            <div style="overflow:hidden;">
                <div style="font-weight:700;font-size:0.95rem;white-space:nowrap;
                            overflow:hidden;text-overflow:ellipsis;">{s['title'] or 'Untitled Course'}</div>
                <div style="font-size:0.75rem;color:#888;">SCORM {s['edition']} · {len(st.session_state['timeline'])} items</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    editing_index = st.session_state.get('editing_index')
    adding_new = st.session_state.get('adding_new', False)

    if st.button("➕ Add New Content", use_container_width=True, type="primary",
                 disabled=(editing_index is not None)):
        st.session_state['adding_new'] = True
        st.rerun()

    st.divider()

    with st.expander("⚙️ Course Settings"):
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
        bg_image_file = st.file_uploader("Background Image (optional, PNG/JPG)", type=['png', 'jpg'], key="bg_image_uploader")
        st.session_state["bg_image_file_obj"] = bg_image_file
        if bg_image_file:
            st.caption("Scales to fill the screen on any device (desktop or mobile) and crops to center — no need to upload multiple sizes.")

    with st.expander("📁 Project File"):
        st.caption("Load")
        uploaded_zip = st.file_uploader("Load project.zip", type=["zip"], key="project_zip_uploader", label_visibility="collapsed")

        if uploaded_zip and not st.session_state.get("_just_loaded", False):
            project, assets_map, logo, bg_image = load_project_zip(uploaded_zip)

            st.session_state["project_obj"] = project
            st.session_state["assets_map"] = assets_map
            st.session_state["logo_tuple"] = logo
            st.session_state["bg_image_tuple"] = bg_image

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

        st.caption("Save")
        if not st.session_state['timeline']:
            st.button("💾 Save Project", use_container_width=True, disabled=True,
                      help="Add at least one content item first.")
        elif st.button("💾 Save Project", use_container_width=True):
            assets_map, js_course_data = build_assets_and_course_data(st.session_state["timeline"])

            logo_tuple = None
            logo_file_obj = st.session_state.get("logo_file_obj")
            if logo_file_obj:
                logo_tuple = (f"logo/{logo_file_obj.name}", logo_file_obj.getvalue())

            bg_image_tuple = None
            bg_image_file_obj = st.session_state.get("bg_image_file_obj")
            if bg_image_file_obj:
                bg_image_tuple = (f"background/{bg_image_file_obj.name}", bg_image_file_obj.getvalue())

            edition = st.session_state["settings"].get("edition", "1.2")

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

            project_zip_file = save_project_zip(project, assets_map, logo_tuple, bg_image_tuple)

            st.download_button(
                "⬇️ Download project.zip",
                # st.download_button doesn't accept tempfile.SpooledTemporaryFile
                # directly (it doesn't subclass io.IOBase, so Streamlit's type
                # check rejects it) -- .read() here is the one unavoidable final
                # materialization, right at the browser-serving boundary; every
                # step upstream (zip writing, asset streaming) still avoided it.
                data=project_zip_file.read(),
                file_name="project.zip",
                mime="application/zip",
                use_container_width=True
            )

    st.divider()
    if st.button("🗑️ Clear All Content", use_container_width=True):
        st.session_state['timeline'] = []
        st.session_state['adding_new'] = False
        st.session_state['editing_index'] = None
        st.rerun()

# ==========================================
# 🖥️ MAIN AREA -- the actual workspace
# ==========================================
st.title(f"🎓 {st.session_state['settings']['title'] or 'SCORM Course Builder Pro'}")

editing_index = st.session_state.get('editing_index')
adding_new = st.session_state.get('adding_new', False)

if editing_index is not None and 0 <= editing_index < len(st.session_state['timeline']):
    # ---------- EDIT VIEW ----------
    edit_item = st.session_state['timeline'][editing_index]
    ct_label = TYPE_LABEL_MAP.get(edit_item["type"], "Text Block")
    st.subheader(f"✏️ Editing item #{editing_index + 1} — {ct_label}")
    if st.button("← Back to Timeline"):
        st.session_state['edit_form_gen'] += 1
        st.session_state['editing_index'] = None
        st.rerun()
    with st.container(border=True):
        # Widget keys are suffixed with edit_form_gen (bumped on every entry/exit
        # of edit mode) rather than relying on deleting old session_state keys --
        # Streamlit/React can keep a text input's on-screen value across a rerun
        # even after its backing key is deleted, since the DOM node isn't
        # necessarily remounted. A brand-new key guarantees a fresh widget.
        render_content_form("edit", f"edit_{editing_index}_{st.session_state['edit_form_gen']}", ct_label,
                             prefill=edit_item, item_index=editing_index)

elif adding_new:
    # ---------- ADD VIEW ----------
    st.subheader("➕ Add New Content")
    if st.button("← Back to Timeline"):
        st.session_state['adding_new'] = False
        st.rerun()
    with st.container(border=True):
        # Deliberately NOT suffixed with add_form_gen -- this key must survive
        # a successful add so the type selector stays put (letting you add
        # several items of the same type in a row) instead of snapping back
        # to the first option.
        content_type = st.selectbox("Content Type", ["Video (MP4)", "Quiz", "PDF Document", "Image", "Text Block"], key="content_type_select")
        # See the edit-view comment above re: why this is generation-suffixed
        # rather than a fixed "add" prefix.
        render_content_form("add", f"add{st.session_state['add_form_gen']}", content_type)

else:
    # ---------- DASHBOARD VIEW ----------
    timeline = st.session_state['timeline']
    type_counts = {}
    for item in timeline:
        type_counts[item['type']] = type_counts.get(item['type'], 0) + 1

    m_cols = st.columns(6)
    m_cols[0].metric("Total Items", len(timeline))
    for col, t in zip(m_cols[1:], ["video", "quiz", "pdf", "image", "text"]):
        col.metric(f"{TYPE_ICON_MAP[t]} {t.title()}", type_counts.get(t, 0))

    st.divider()
    st.subheader(f"📜 Timeline ({len(timeline)} items)")

    if not timeline:
        st.info("No content yet. Click **➕ Add New Content** in the sidebar to get started.")
    else:
        def item_label(item):
            return item.get('title') or item.get('question') or "Untitled"

        if len(timeline) > ITEMS_PER_PAGE:
            st.text_input("🔍 Filter items by title/question", key='item_filter')

        filter_text = st.session_state['item_filter'].strip().lower()
        is_filtering = bool(filter_text)

        all_indexed = list(enumerate(timeline))
        if is_filtering:
            visible = [(i, item) for i, item in all_indexed if filter_text in item_label(item).lower()]
            st.caption("⚠️ Reordering is disabled while a filter is active (neighbors in the filtered view aren't real neighbors).")
        else:
            visible = all_indexed

        total_pages = max(1, (len(visible) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        st.session_state['item_page'] = min(st.session_state['item_page'], total_pages - 1)
        page = st.session_state['item_page']

        if total_pages > 1:
            pcol1, pcol2, pcol3 = st.columns([0.15, 0.7, 0.15])
            if pcol1.button("⬅ Prev page", disabled=(page == 0)):
                st.session_state['item_page'] -= 1
                st.rerun()
            pcol2.markdown(f"<div style='text-align:center;'>Page {page + 1} of {total_pages} ({len(visible)} matching item{'s' if len(visible) != 1 else ''})</div>", unsafe_allow_html=True)
            if pcol3.button("Next page ➡", disabled=(page >= total_pages - 1)):
                st.session_state['item_page'] += 1
                st.rerun()

        page_slice = visible[page * ITEMS_PER_PAGE : (page + 1) * ITEMS_PER_PAGE]

        if is_filtering and not page_slice:
            st.info("No items match that filter.")

        for i, item in page_slice:
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([0.5, 0.1, 0.1, 0.1, 0.1])
                icon = TYPE_ICON_MAP.get(item['type'], "❔")
                title = truncate_title(item_label(item))

                reorder_disabled = is_filtering

                file_status = ""
                if item['type'] in ['video', 'pdf', 'image'] and 'file' not in item:
                    file_status = "⚠️ (Re-upload needed)"

                label = f"**{i+1}. {icon} {title}** {file_status}"
                col1.markdown(label)

                if file_status:
                    re_file = col1.file_uploader(f"Upload {item['filename']}", type=['mp4', 'pdf', 'png', 'jpg'], key=f"reup_{i}")
                    if re_file:
                        st.session_state['timeline'][i]['file'] = re_file
                        st.success("✅ Saved! (Click any button to refresh UI)")

                if col2.button("✏️", key=f"edit_{i}"):
                    st.session_state['edit_form_gen'] += 1
                    st.session_state['editing_index'] = i
                    st.rerun()
                if col3.button("⬆️", key=f"up_{i}", disabled=(i==0) or reorder_disabled): move_item(i, 'up'); st.rerun()
                if col4.button("⬇️", key=f"down_{i}", disabled=(i==len(timeline)-1) or reorder_disabled): move_item(i, 'down'); st.rerun()
                if col5.button("🗑️", key=f"del_{i}"): delete_item(i); st.rerun()

    st.divider()

    # --- EXPORT (NEW BUILDER) ---
    files_missing = any(
        item['type'] in ['video', 'pdf', 'image'] and 'file' not in item
        for item in st.session_state['timeline']
    )

    if not st.session_state['timeline']:
        pass
    elif files_missing:
        st.warning("⚠️ Please re-upload missing files before exporting.")
    else:
        if st.button("🚀 Export SCORM Package (.zip)", type="primary", use_container_width=True):
            with st.spinner("Packaging with new builder..."):

                assets_map, js_course_data = build_assets_and_course_data(st.session_state["timeline"])

                logo_tuple = None
                if logo_file:
                    logo_tuple = (f"logo/{logo_file.name}", logo_file.getvalue())

                bg_image_tuple = None
                if bg_image_file:
                    bg_image_tuple = (f"background/{bg_image_file.name}", bg_image_file.getvalue())

                edition = st.session_state["settings"].get("edition", "1.2")

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

                zip_file = build_scorm_package(project, assets_map, logo=logo_tuple, bg_image=bg_image_tuple, warn=st.warning)

                st.success("Export Successful! ✅")
                st.download_button(
                    "⬇️ Download ZIP",
                    # see the Save Project download_button above for why .read() is needed here
                    data=zip_file.read(),
                    file_name=f"Course_{uuid4().hex[:8]}.zip",
                    mime="application/zip"
                )
