# Hand-maintained SCORM runtime template (SCORM 1.2 + 2004 support).
# Originally generated from scorm2.py, but has since diverged with manual
# fixes (sidebar nav, SCORM 2004 API support). Do NOT regenerate this file
# via extract_from_scorm2.py -- that would silently overwrite those fixes
# with the stale scorm2.py copy. See extract_from_scorm2.py's --force guard.

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{course_title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
        
        * {{ box-sizing: border-box; }}
        
        body {{ 
            font-family: 'Inter', sans-serif; 
            background-color: #f4f6f8; 
            margin: 0; 
            display: flex; 
            min-height: 100vh; 
            height: auto;
            overflow-y: auto; 
        }}
        
        /* SIDEBAR */
        .sidebar {{
            width: 300px;
            background-color: #ffffff;
            border-right: 1px solid #e0e0e0;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
            transition: transform 0.3s ease;
            position: relative;
        }}
        .sidebar.collapsed {{
            transform: translateX(-300px);
            position: absolute;
            height: 100%;
        }}
        .mobile-menu-btn {{
            display: none;
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: white;
            margin-right: 15px;
        }}
        .sidebar-header {{
            padding: 25px 20px;
            font-weight: 700;
            font-size: 14px;
            color: #444;
            letter-spacing: 1px;
            border-bottom: 1px solid #f0f0f0;
            text-transform: uppercase;
        }}
        .menu-list {{ list-style: none; padding: 0; margin: 0; overflow-y: auto; flex: 1; }}
        .menu-item {{
            padding: 15px 20px;
            border-bottom: 1px solid #f9f9f9;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: 0.2s;
            color: #666;
            font-size: 14px;
        }}
        .menu-item:hover {{ background-color: #f8f9fa; }}
        .menu-item.active {{
            background-color: #e3f2fd;
            color: {theme_color};
            font-weight: 600;
            border-left: 4px solid {theme_color};
        }}
        .status-icon {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 2px solid #ddd;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            color: white;
        }}
        .menu-item.completed .status-icon {{ background-color: #28a745; border-color: #28a745; }}
        .menu-item.locked {{ opacity: 0.5; cursor: not-allowed; }}
        .menu-item.locked:hover {{ background-color: transparent; }}

        /* MAIN CONTENT */
        .main-wrapper {{ flex: 1; display: flex; flex-direction: column; min-height: 100vh; overflow: hidden; }}
        .header {{ 
            background-color: {theme_color}; 
            color: white; 
            height: 64px; 
            padding: 0 20px; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.08); 
            flex-shrink: 0; 
        }}
        .header-left {{ display: flex; align-items: center; }}
        .header h1 {{ margin: 0; font-size: 18px; font-weight: 600; }}
        .header-right img {{ height: 35px; width: auto; max-width: 150px; object-fit: contain; background: rgba(255,255,255,0.95); padding: 5px; border-radius: 4px; }}
        
        @media (max-width: 768px) {{
            .sidebar {{
                position: absolute;
                height: 100%;
                box-shadow: 2px 0 10px rgba(0,0,0,0.1);
                transform: translateX(-100%);
            }}
            .sidebar.active {{
                transform: translateX(0);
            }}
            .mobile-menu-btn {{ display: block; }}
            .card {{ padding: 20px; }}
            .header h1 {{ font-size: 16px; }}
        }}


        .content-area {{ 
            flex: 1; 
            padding: 20px; 
            overflow: hidden; /* Prevent double scrollbars */
            display: flex; 
            flex-direction: column;
            justify-content: center; 
            align-items: center; 
            background-color: #f4f6f8;
            min-height: 0;
        }}
        .content-area.final-card-mode {{
            overflow-y: auto;
            justify-content: center;
            align-items: center;
        }}
        .card {{ 
            background: white; 
            width: 90%; 
            max-width: 1000px;
            height: 100%;
            max-height: 100%;
            display: flex;
            flex-direction: column;
            margin: 0;
            padding: 30px; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.05); 
            overflow: hidden; /* No scroll */
            align-self: center;
        }}
        .card.final-card {{
            height: auto;
            max-height: none;
            overflow: visible;
            padding: 24px;
        }}


        /* Responsive Media Elements */
        video, .content-img, .pdf-frame {{ 
            max-width: 100%; 
            max-height: 100%; /* Scale to fit available space */
            width: auto;
            height: auto;
            object-fit: contain;
            flex: 1;
            min-height: 0;
        }}
        .content-img {{ border: none; background: transparent; }}
        .pdf-frame {{ border: 1px solid #ddd; background: white; }}
        
        /* Custom Video Player (CSS Grid for precise control) */
        .video-container {{
            width: 100%;
            flex: 1;
            min-height: 0;
            max-height: 60vh;
            background: transparent;
            border-radius: 8px;
            overflow: hidden;
            display: grid;
            grid-template-rows: 1fr auto; /* video area + controls bar */
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}
        
        /* Image Container (same Grid approach as video) */
        .image-container {{
            width: 100%;
            flex: 1;
            min-height: 0;
            max-height: 60vh;
            background: transparent;
            border-radius: 8px;
            overflow: hidden;
            display: grid;
            grid-template-rows: auto 1fr auto; /* title + image + nav */
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}
        
        /* PDF Container (same Grid approach) */
        .pdf-container {{
            width: 100%;
            flex: 1;
            min-height: 0;
            max-height: 60vh;
            background: transparent;
            border-radius: 8px;
            overflow: hidden;
            display: grid;
            grid-template-rows: auto 1fr auto; /* title + pdf + nav */
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}
        
        .final-screen {{
            width: 100%;
            flex: 1;
            min-height: 0;
            height: 100%;
            background: transparent;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 30px;
        }}
        
        .media-wrapper {{
            grid-row: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            width: 100%;
            position: relative;
            background: transparent;
            padding: 0;
            margin: 0;
            min-height: 0;
        }}
        
        .result-content {{ 
            display: flex;
            flex-direction: column;
            gap: 24px;
            padding: 40px 32px;
            background: white;
            width: 100%;
            max-width: 780px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.06);
            text-align: center;
        }}
        .result-header {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            flex-shrink: 0;
        }}
        .result-body {{
            min-height: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            gap: 20px;
            text-align: center;
        }}
        .result-actions {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            flex-shrink: 0;
            flex-wrap: wrap;
        }}
        video {{
            max-width: 100%;
            max-height: 100%;
            width: auto;
            height: auto;
            object-fit: contain;
            display: block;
            outline: none;
            margin: 0 auto;
            padding: 0;
        }}
        .custom-controls {{
            grid-row: 2;
            display: flex;
            align-items: center;
            background: #111;
            padding: 12px 15px;
            color: white;
            gap: 15px;
            flex-shrink: 0;
            margin: 0;
        }}
        .control-btn {{
            background: none;
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            padding: 0;
            width: 30px; 
            text-align: center;
            transition: color 0.2s;
        }}
        .control-btn:hover {{ color: {theme_color}; }}
        .seek-bar {{
            flex: 1;
            cursor: pointer;
            height: 5px;
            accent-color: {theme_color};
        }}
        .time-display {{
            font-size: 13px;
            font-family: 'Courier New', monospace;
            min-width: 90px;
            text-align: center;
            color: #ddd;
        }}
        
        /* NAV BAR */
        .nav-bar {{ 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-top: auto; 
            padding-top: 20px; 
            border-top: 1px solid #eee; 
            width: 100%; 
            flex-shrink: 0;
        }}
        .nav-center {{ 
            flex: 1; 
            text-align: center; 
            padding: 0 15px; 
            font-weight: 500; 
            color: #666; 
        }}

        @media (max-width: 600px) {{
            .nav-bar {{
                flex-wrap: wrap;
                gap: 10px;
                justify-content: center;
            }}
            .nav-center {{
                order: -1; 
                width: 100%;
                flex: none;
                margin-bottom: 10px;
            }}
            .btn {{
                flex: 1;
                text-align: center;
                white-space: nowrap;
            }}
        }}
        .btn {{ background-color: {theme_color}; color: white; border: none; padding: 12px 28px; border-radius: 4px; cursor: pointer; font-size: 1rem; font-weight: 500; transition: opacity 0.2s; }}
        .btn:hover {{ opacity: 0.9; }}
        .btn:disabled {{ background-color: #ccc; cursor: not-allowed; opacity: 1; }}
        .btn-prev {{ background-color: #6c757d; visibility: hidden; }}
        .btn-next {{ background-color: {theme_color}; }}
 
        
        .quiz-options label {{ display: block; padding: 15px; border: 1px solid #eee; margin-bottom: 10px; border-radius: 6px; cursor: pointer; transition: 0.2s; position: relative; padding-right: 40px; }}
        .quiz-options label:hover {{ background-color: #f8f9fa; border-color: {theme_color}; }}
        .quiz-options label.correct {{ border-color: #28a745; background: #eaf7ed; }}
        .quiz-options label.incorrect {{ border-color: #dc3545; background: #fbe9ea; }}
        .quiz-options label.correct::after, .quiz-options label.incorrect::after {{
            content: attr(data-mark);
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            font-weight: 700;
        }}
        .quiz-options label.correct::after {{ color: #28a745; }}
        .quiz-options label.incorrect::after {{ color: #dc3545; }}

        /* Security */
        video::-internal-media-controls-download-button {{ display:none; }}
        video::-webkit-media-controls-enclosure {{ overflow:hidden; }}
        
        /* Certificate Styles */
        .certificate-box {{
            padding: 30px;
            border: 4px double #e0e0e0;
            border-radius: 12px;
            text-align: center;
            background: white;
            margin: 10px auto;
            width: 100%;
            max-width: 700px;
            /* Remove fixed heights allowing content to flow naturally */
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}


        /* Print Styles - A4 Landscape Certificate */
        @media print {{
            @page {{ 
                size: 297mm 210mm; 
                margin: 0mm; 
            }}
            
            html, body {{
                width: 297mm !important;
                height: 210mm !important;
                margin: 0 !important;
                padding: 0 !important;
                box-sizing: border-box !important;
                overflow: hidden !important;
            }}
            body {{
                border: 8px solid {theme_color} !important;
                box-sizing: border-box !important;
            }}
            
            * {{ 
                -webkit-print-color-adjust: exact !important; 
                print-color-adjust: exact !important; 
            }}
            
            /* Hide UI elements */
            .sidebar, .header, .nav-bar, .btn, .result-header {{ 
                display: none !important; 
            }}
            
            /* Reset all containers to full page */
            .main-wrapper, .content-area, .card {{
                display: flex !important;
                width: 100% !important;
                height: 100% !important;
                max-width: none !important;
                max-height: none !important;
                padding: 0 !important;
                margin: 0 !important;
                background: white !important;
                box-shadow: none !important;
                border: none !important;
                overflow: visible !important;
                align-items: center;
                justify-content: center;
            }}
            
            #app-content {{
                width: 100% !important;
                height: 100% !important;
                display: flex !important;
                overflow: visible !important;
                position: relative !important;
            }}
            
            /* Center certificate on page */
            .final-screen {{
                width: 100% !important;
                height: 100% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                background: white !important;
                padding: 0 !important;
                position: relative !important;
            }}
            
            .result-content {{
                width: 100% !important;
                height: 100% !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                padding: 0 !important;
                overflow: visible !important;
                box-shadow: none !important;
                position: relative !important;
            }}
            
            /* Certificate box styled for print */
            .certificate-box {{
                position: absolute !important;
                inset: 0 !important;
                width: 100% !important;
                height: 100% !important;
                max-width: none !important;
                max-height: none !important;
                margin: 0 !important;
                padding: 40px 60px !important;
                border: none !important;
                border-radius: 0 !important;
                box-sizing: border-box !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                justify-content: center !important;
                background: white !important;
                page-break-inside: avoid !important;
                transform: scale(0.94);
                transform-origin: center;
            }}
            
            /* Scale up fonts for print */
            .certificate-box h3 {{
                font-size: 2rem !important;
            }}
            
            .certificate-box h2 {{
                font-size: 1.8rem !important;
            }}
            
            .certificate-box div[style*="font-size:2.5rem"] {{
                font-size: 4rem !important;
            }}
        }}
    </style>
    <script>
        var scorm = null;
        var scormProtocol = null; // "1.2" or "2004" -- whichever API was actually found
        var scormTerminated = false;
        var scormEdition = {scorm_edition};

        function findAPIInWindow(win, propName) {{
            var attempts = 0;
            while (win[propName] == null && win.parent != null && win.parent != win && attempts < 500) {{
                win = win.parent;
                attempts++;
            }}
            return win[propName];
        }}
        function findAPI(propName) {{
            // Most LMSs load the SCO in an iframe (parent chain), but this player also
            // supports launching in a new window (ScormSettings.launchInNewWindow), where
            // the API instead lives on window.opener.
            var api = findAPIInWindow(window, propName);
            if (!api && window.opener != null) {{
                api = findAPIInWindow(window.opener, propName);
            }}
            return api;
        }}
        function initSCORM() {{
            var api2004 = findAPI("API_1484_11");
            var api12 = findAPI("API");
            if (scormEdition === "2004" && api2004) {{ scorm = api2004; scormProtocol = "2004"; }}
            else if (scormEdition !== "2004" && api12) {{ scorm = api12; scormProtocol = "1.2"; }}
            else if (api2004) {{ scorm = api2004; scormProtocol = "2004"; }}
            else if (api12) {{ scorm = api12; scormProtocol = "1.2"; }}
            if (!scorm) return;

            if (scormProtocol === "2004") {{
                scorm.Initialize("");
                var status = scorm.GetValue("cmi.completion_status");
                if (status === "not attempted" || status === "unknown" || status === "") {{
                    scorm.SetValue("cmi.completion_status", "incomplete");
                    scorm.Commit("");
                }}
            }} else {{
                scorm.LMSInitialize("");
                var status12 = scorm.LMSGetValue("cmi.core.lesson_status");
                if (status12 == "not attempted") {{
                    scorm.LMSSetValue("cmi.core.lesson_status", "incomplete");
                    scorm.LMSCommit("");
                }}
            }}
        }}

        function toggleSidebar() {{
            var sb = document.getElementById('sidebar');
            if (window.innerWidth <= 768) {{
                sb.classList.toggle('active');
            }} else {{
                sb.classList.toggle('collapsed');
            }}
        }}
        function sendScore(score, status) {{
            if (!scorm || scormTerminated) return;
            if (scormProtocol === "2004") {{
                var success = (status === "passed") ? "passed" : (status === "failed") ? "failed" : "unknown";
                scorm.SetValue("cmi.completion_status", "completed");
                scorm.SetValue("cmi.success_status", success);
                scorm.SetValue("cmi.score.raw", score);
                scorm.SetValue("cmi.score.min", "0");
                scorm.SetValue("cmi.score.max", "100");
                scorm.SetValue("cmi.score.scaled", String(score / 100));
                scorm.Commit("");
                scorm.Terminate("");
            }} else {{
                scorm.LMSSetValue("cmi.core.score.raw", score);
                scorm.LMSSetValue("cmi.core.lesson_status", status);
                scorm.LMSCommit("");
                scorm.LMSFinish("");
            }}
            scormTerminated = true;
        }}

        var courseData = {course_data_json}; 
        var passingScore = {passing_score}; 
        var hasQuiz = {has_quiz};
        var currentStep = 0;
        var totalScore = 0;
        var maxScore = 0;
        var progressStatus = new Array(courseData.length).fill(false);
        var quizResults = new Array(courseData.length).fill(0);
        var quizRevealDone = false;

        window.onload = function() {{
            initSCORM();
            calculateMaxScore();
            renderSidebar();
            renderStep();
            document.addEventListener('contextmenu', event => event.preventDefault());
        }};

        function calculateMaxScore() {{
            courseData.forEach(item => {{ if(item.type === 'quiz') maxScore += 10; }});
        }}

        function renderSidebar() {{
            var list = document.getElementById('menu-list');
            list.innerHTML = '';
            courseData.forEach((item, index) => {{
                var label = item.title || item.question || ('Item ' + (index + 1));
                var unlocked = progressStatus[index] || index === currentStep || (index > 0 && progressStatus[index-1]);
                var li = document.createElement('li');
                li.className = 'menu-item' + (unlocked ? '' : ' locked');
                if (index === currentStep) li.classList.add('active');
                if (progressStatus[index]) li.classList.add('completed');
                var iconHTML = progressStatus[index] ? '✔' : (unlocked ? '' : '🔒');
                li.innerHTML = `<span>${{label}}</span> <div class="status-icon">${{iconHTML}}</div>`;
                li.onclick = function() {{
                    if (unlocked) {{
                        currentStep = index; renderSidebar(); renderStep();
                    }}
                }};
                list.appendChild(li);
            }});
        }}

        function markCurrentStepComplete() {{
            progressStatus[currentStep] = true;
            renderSidebar();
        }}

        function renderStep() {{
            var container = document.getElementById('app-content');
            var cardEl = document.querySelector('.card');
            var contentAreaEl = document.querySelector('.content-area');
            if (cardEl) cardEl.classList.remove('final-card');
            if (contentAreaEl) contentAreaEl.classList.remove('final-card-mode');
            var item = courseData[currentStep];
            if (!item) {{ showFinalResult(container); return; }}
            renderSidebar();

            var titleHTML = `<h2 style="margin-top:0; color:#333; margin-bottom:20px; flex-shrink:0;">${{item.title || 'Quiz'}}</h2>`;
            
            var prevBtnStyle = (currentStep > 0) ? 'visibility:visible;' : 'visibility:hidden;';
            var navBarStart = `<div class="nav-bar"><button class="btn btn-prev" style="${{prevBtnStyle}}" onclick="prevStep()">⬅ Previous</button><div class="nav-center" id="msg">`;
            var navBarEnd = `</div>`;
            // Default next button (active)
            var navBarNext = `<button id="btn-next" class="btn btn-next" onclick="nextStep()">Next Lesson ➜</button>${{navBarEnd}}`;

            var contentHTML = "";

            if (item.type === 'video') {{
                // Video: Next button disabled initially
                var navBarNextVideo = `<button id="btn-next" class="btn btn-next" disabled onclick="nextStep()">Next Lesson ➜</button>${{navBarEnd}}`;
                
                contentHTML = `
                    ${{titleHTML}}
                    <div class="video-container">
                        <div class="media-wrapper">
                            <video id="player" controlsList="nodownload" autoplay>
                                <source src="${{item.src}}" type="video/mp4">
                            </video>
                        </div>
                        <div class="custom-controls">
                            <button class="control-btn" id="playPauseBtn" onclick="togglePlay()">⏸</button>
                            <span class="time-display"><span id="currentTime">0:00</span> / <span id="duration">0:00</span></span>
                            <input type="range" class="seek-bar" id="seekBar" value="0" min="0" step="0.1" oninput="seekVideo(this.value)">
                        </div>
                    </div>
                    ${{navBarStart}}</div>
                    ${{navBarNextVideo}}
                `;
                container.innerHTML = contentHTML;
                
                var vid = document.getElementById('player');
                var btn = document.getElementById('playPauseBtn');
                var seekBar = document.getElementById('seekBar');
                var curTimeTxt = document.getElementById('currentTime');
                var durTimeTxt = document.getElementById('duration');
                var nextBtn = document.getElementById('btn-next');

                // Toggle Play/Pause
                window.togglePlay = function() {{
                    if (vid.paused) {{ vid.play(); btn.innerText = "⏸"; }} 
                    else {{ vid.pause(); btn.innerText = "▶"; }}
                }};

                // Seek Video
                window.seekVideo = function(val) {{ vid.currentTime = val; }};

                // Format Time Helper
                function formatTime(s) {{
                    var m = Math.floor(s / 60);
                    var sec = Math.floor(s % 60);
                    return m + ":" + (sec < 10 ? "0" + sec : sec);
                }}

                vid.onloadedmetadata = function() {{
                    seekBar.max = vid.duration;
                    durTimeTxt.innerText = formatTime(vid.duration);
                }};

                vid.ontimeupdate = function() {{
                    seekBar.value = vid.currentTime;
                    curTimeTxt.innerText = formatTime(vid.currentTime);
                }};

                vid.onended = function() {{
                    btn.innerText = "↺";
                    document.getElementById('msg').innerHTML = "<span style='color:#28a745; font-weight:bold;'>✅ Completed!</span>";
                    nextBtn.disabled = false;
                    nextBtn.style.backgroundColor = '#28a745'; 
                    markCurrentStepComplete();
                }};

            }} else if (item.type === 'quiz') {{
                quizRevealDone = false;
                var inputType = (item.quizType === 'single') ? 'radio' : 'checkbox';
                contentHTML = `
                    <div style="font-size:1.4rem; font-weight:600; margin-bottom:25px;">📝 Q: ${{item.question}}</div>
                    <div class="quiz-options">`;
                item.options.forEach((opt, index) => {{
                    contentHTML += `<label class="quiz-option" data-index="${{index}}" data-mark=""><input type="${{inputType}}" name="answer" value="${{index}}" style="margin-right:15px;">${{opt}}</label>`;
                }});
                contentHTML += `</div>${{navBarStart}}</div><div><button id="btn-next" class="btn btn-next" style="display:block !important;" onclick="checkAndNextStep()">Check Answer ➜</button></div>${{navBarEnd}}`;
                container.innerHTML = contentHTML;

            }} else if (item.type === 'pdf') {{
                contentHTML = `
                    <div class="pdf-container">
                        ${{titleHTML}}
                        <div style="grid-row: 2; overflow: hidden; min-height: 0;">
                            <iframe src="${{item.src}}#toolbar=0" class="pdf-frame" style="width: 100%; height: 100%; border: 1px solid #ddd;"></iframe>
                        </div>
                        <div style="grid-row: 3;">
                            ${{navBarStart}}</div><button class="btn" onclick="manualComplete()">Mark as Read & Next ➜</button>${{navBarEnd}}
                        </div>
                    </div>
                `;
                container.innerHTML = contentHTML;
            }} else if (item.type === 'image') {{
                contentHTML = `
                    <div class="image-container">
                        ${{titleHTML}}
                        <div style="grid-row: 2; display: flex; align-items: center; justify-content: center; overflow: hidden; min-height: 0;">
                            <img src="${{item.src}}" class="content-img" oncontextmenu="return false;" draggable="false">
                        </div>
                        <div style="grid-row: 3;">
                            ${{navBarStart}}</div><button class="btn" onclick="manualComplete()">Mark as Read & Next ➜</button>${{navBarEnd}}
                        </div>
                    </div>
                `;
                container.innerHTML = contentHTML;
            }} else if (item.type === 'text') {{
                contentHTML = `${{titleHTML}}
                    <div style="flex: 1; min-height: 0; max-height: 60vh; overflow-y: auto; margin-bottom: 20px;">
                        <div style="line-height:1.6; font-size:1.1rem; white-space: pre-wrap;">${{item.content}}</div>
                    </div>
                    ${{navBarStart}}</div><button class="btn" onclick="manualComplete()">Mark as Read & Next ➜</button>${{navBarEnd}}`;
                container.innerHTML = contentHTML;
            }}
        }}

        function manualComplete() {{ markCurrentStepComplete(); nextStep(); }}

        function checkAndNextStep() {{
            var item = courseData[currentStep];
            var inputs = document.querySelectorAll('input[name="answer"]:checked');
            var userAnswers = Array.from(inputs).map(i => parseInt(i.value));
            
            if (userAnswers.length === 0) {{ alert("Please select an answer."); return; }}
            
            // Evaluate
            var isCorrect = false;
            var sortedUser = userAnswers.slice().sort();
            var sortedCorrect = item.correct.slice().sort();
            if (item.quizType === 'single') {{ isCorrect = (sortedUser[0] === sortedCorrect[0]); }} 
            else {{ isCorrect = JSON.stringify(sortedUser) === JSON.stringify(sortedCorrect); }}
            
            // Store result only once
            if (!quizRevealDone) {{
                quizResults[currentStep] = isCorrect ? 1 : 0;
                markCurrentStepComplete();
            }}

            // Reveal styling first, then move on next click
            if (!quizRevealDone) {{
                var labels = document.querySelectorAll('.quiz-option');
                labels.forEach(lbl => {{
                    var idx = parseInt(lbl.getAttribute('data-index'));
                    lbl.classList.remove('correct', 'incorrect');
                    if (sortedCorrect.includes(idx)) {{
                        lbl.classList.add('correct');
                        lbl.setAttribute('data-mark', '✔');
                    }} else {{
                        lbl.classList.add('incorrect');
                        lbl.setAttribute('data-mark', '✖');
                    }}
                }});
                document.querySelectorAll('input[name="answer"]').forEach(inp => inp.disabled = true);
                var msgEl = document.getElementById('msg');
                if (msgEl) msgEl.innerHTML = isCorrect ? "<span style='color:#28a745; font-weight:bold;'>✅ Correct</span>" : "<span style='color:#dc3545; font-weight:bold;'>❌ Incorrect</span>";
                var btn = document.getElementById('btn-next');
                if (btn) btn.textContent = "Next ➜";
                quizRevealDone = true;
                return;
            }}

            nextStep();
        }}
        
        function nextStep() {{ currentStep++; renderStep(); }}
        function prevStep() {{ if (currentStep > 0) {{ currentStep--; renderStep(); }} }}

        function showFinalResult(container) {{
            renderSidebar();
            var cardEl = document.querySelector('.card');
            var contentAreaEl = document.querySelector('.content-area');
            if (cardEl) cardEl.classList.add('final-card');
            if (contentAreaEl) contentAreaEl.classList.add('final-card-mode');
            
            // Calculate score (even if no quiz, defaults 100% or logic adjustment)
            var totalQuizzes = courseData.filter(i => i.type === 'quiz').length;
            var correctCount = quizResults.reduce((a, b) => a + (b || 0), 0);
            var score = 100; // Default for no-quiz courses
            if (totalQuizzes > 0) {{ score = Math.round((correctCount / totalQuizzes) * 100); }}

            var passed = score >= passingScore;
            
            var resultHTML = `
                <div class="final-screen">
                    <div class="result-content">
                        <div class="result-header">
                            <h2 style="margin:0;">${{totalQuizzes > 0 ? (passed ? "Congratulations!" : "Course Completed") : "Course Completed"}}</h2>
                            <div style="font-size:1rem; color:#555;">
                                ${{totalQuizzes > 0 ? (passed ? "You have successfully completed the course." : "You have finished the course.") : "You have successfully completed the course."}}
                            </div>
                        </div>
                        <div class="result-body">
            `;

            var actionHTML = '';

            // Only show certificate/score if there are quizzes
            if (totalQuizzes > 0) {{
                if (passed) {{
                    resultHTML += `
                            <div class="certificate-box" style="flex-shrink:0; max-height: none; overflow: visible;">
                                <h3 style="margin:0 0 8px 0; font-size:1.3rem; text-transform:uppercase; letter-spacing:1px; color:#333;">Certificate of Completion</h3>
                                <p style="color:#666; font-size:0.85rem; margin:5px 0;">This certifies that you have completed</p>
                                <h2 style="color:{theme_color}; margin:10px 0; font-size:1.2rem; line-height:1.2;">{course_title}</h2>
                                
                                <div style="margin: 8px 0; border-top:1px solid #eee; border-bottom:1px solid #eee; padding:10px 0;">
                                    <div style="font-size:2.5rem; font-weight:800; color:{theme_color}; line-height:1;">${{score}}%</div>
                                    <div style="font-size:1rem; color:#28a745; font-weight:bold; margin-top:3px;">✅ Passed</div>
                                </div>
                                <div style="font-size:0.75rem; color:#999; margin-top:8px;">Date: ${{(new Date()).toLocaleDateString()}}</div>
                            </div>
                    `;
                    actionHTML = `<button class="btn" onclick="window.print()">🖨 Print Certificate</button>`;
                    sendScore(score, "passed");
                }} else {{
                    resultHTML += `
                            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; flex:1; text-align:center;">
                                <div style="font-size:5rem; font-weight:bold; color:#dc3545; line-height:1;">${{score}}%</div>
                                <div style="color:#666; margin-top:10px; font-size:1.1rem;">(Passing Score: ${{passingScore}}%)</div>
                                <div style="font-size:1.2rem; margin:30px 0; color:#444;">Please review the material and try again.</div>
                            </div>
                    `;
                    actionHTML = `<button class="btn" onclick="location.reload()">↺ Retry Course</button>`;
                    sendScore(score, "failed");
                }}
            }} else {{
                // No quizzes - just show completion message with certificate (no score)
                resultHTML += `
                        <div class="certificate-box" style="flex-shrink:0; max-height: none; overflow: visible;">
                            <h3 style="margin:0 0 8px 0; font-size:1.3rem; text-transform:uppercase; letter-spacing:1px; color:#333;">Certificate of Completion</h3>
                            <p style="color:#666; font-size:0.85rem; margin:5px 0;">This certifies that you have completed</p>
                            <h2 style="color:{theme_color}; margin:10px 0; font-size:1.2rem; line-height:1.2;">{course_title}</h2>
                            <div style="font-size:0.75rem; color:#999; margin-top:15px;">Date: ${{(new Date()).toLocaleDateString()}}</div>
                        </div>
                `;
                actionHTML = `<button class="btn" onclick="window.print()">🖨 Print Certificate</button>`;
                sendScore(100, "completed");
            }}

            resultHTML += `
                        </div>
                        <div class="result-actions">${{actionHTML}}</div>
                    </div>
                </div>
            `;
            container.innerHTML = resultHTML;
        }}
    </script>
</head>
<body>
    <div class="sidebar" id="sidebar"><div class="sidebar-header">TABLE OF CONTENTS</div><ul class="menu-list" id="menu-list"></ul></div>
    <div class="main-wrapper">
        <div class="header">
            <div class="header-left">
                <button class="mobile-menu-btn" onclick="toggleSidebar()">☰</button>
                <h1>{course_title}</h1>
            </div>
            <div class="header-right">{logo_html}</div>
        </div>
        <div class="content-area"><div class="card"><div id="app-content">Loading Course...</div></div></div>
    </div>
</body>
</html>
'''

MANIFEST_TEMPLATE_SCORM12 = '''<?xml version="1.0" standalone="no" ?><manifest identifier="Man_{id}" version="1.0" xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2" xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd http://www.imsproject.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd"><metadata><schema>ADL SCORM</schema><schemaversion>1.2</schemaversion></metadata><organizations default="Org_{id}"><organization identifier="Org_{id}"><title>{title}</title><item identifier="Item_{id}" identifierref="Res_{id}"><title>{title}</title></item></organization></organizations><resources><resource identifier="Res_{id}" type="webcontent" href="index.html" adlcp:scormtype="sco"><file href="index.html"/>{resource_files}</resource></resources></manifest>'''

MANIFEST_TEMPLATE_SCORM2004 = '''<?xml version="1.0" standalone="no" ?><manifest identifier="Man_{id}" version="1.0" xmlns="http://www.imsglobal.org/xsd/imscp_v1p1" xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3"
    xmlns:adlseq="http://www.adlnet.org/xsd/adlseq_v1p3"
    xmlns:adlnav="http://www.adlnet.org/xsd/adlnav_v1p3"
    xmlns:imsss="http://www.imsglobal.org/xsd/imsss" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.imsglobal.org/xsd/imscp_v1p1 imscp_v1p1.xsd http://www.adlnet.org/xsd/adlcp_v1p3 adlcp_v1p3.xsd http://www.imsglobal.org/xsd/imsss imsss_v1p0.xsd"><metadata><schema>ADL SCORM</schema><schemaversion>1.2</schemaversion></metadata><organizations default="Org_{id}"><organization identifier="Org_{id}"><title>{title}</title><item identifier="Item_{id}" identifierref="Res_{id}"><title>{title}</title></item></organization></organizations><resources><resource identifier="Res_{id}" type="webcontent" href="index.html" adlcp:scormType="sco"><file href="index.html"/>{resource_files}</resource></resources></manifest>'''
