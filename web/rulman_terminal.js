import { app } from "/scripts/app.js";

// ANSI escape code to HTML converter for full terminal color rendering
function ansiToHtml(text) {
    if (text === null || text === undefined) return "";
    
    let strText = "";
    if (typeof text === "string") {
        strText = text;
    } else if (Array.isArray(text)) {
        strText = text.join("\n");
    } else if (typeof text === "object") {
        try { strText = JSON.stringify(text); } catch(e) { strText = String(text); }
    } else {
        strText = String(text);
    }

    let html = strText
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    const colors = {
        '30': 'color: #484f58',
        '31': 'color: #ff7b72; font-weight: bold;',
        '32': 'color: #56d364; font-weight: bold;',
        '33': 'color: #e3b341; font-weight: bold;',
        '34': 'color: #79c0ff',
        '35': 'color: #d2a8ff',
        '36': 'color: #39c5cf',
        '37': 'color: #e6edf3',
        '90': 'color: #8b949e',
        '91': 'color: #ffa198; font-weight: bold;',
        '92': 'color: #7ee787; font-weight: bold;',
        '93': 'color: #f2cc60; font-weight: bold;',
        '94': 'color: #a5d6ff',
        '95': 'color: #d2a8ff',
        '96': 'color: #56d4dd',
        '97': 'color: #ffffff',
        '1':  'font-weight: bold;',
        '2':  'opacity: 0.7;'
    };

    let openSpans = 0;
    html = html.replace(/\x1b\[([0-9;]*)m/g, (match, p1) => {
        if (!p1 || p1 === '0' || p1 === '00') {
            let res = '</span>'.repeat(openSpans);
            openSpans = 0;
            return res;
        }
        const codes = p1.split(';');
        let styles = [];
        for (let code of codes) {
            if (colors[code]) {
                styles.push(colors[code]);
            }
        }
        if (styles.length > 0) {
            openSpans++;
            return `<span style="${styles.join('; ')}">`;
        }
        return '';
    });

    html += '</span>'.repeat(openSpans);

    html = html
        .replace(/\[INFO\]/g, '<span style="color: #3fb950; font-weight: bold;">[INFO]</span>')
        .replace(/\[WARNING\]/g, '<span style="color: #d29922; font-weight: bold;">[WARNING]</span>')
        .replace(/\[ERROR\]/g, '<span style="color: #f85149; font-weight: bold;">[ERROR]</span>')
        .replace(/\[START\]/g, '<span style="color: #58a6ff; font-weight: bold;">[START]</span>')
        .replace(/\[DONE\]/g, '<span style="color: #56d364; font-weight: bold;">[DONE]</span>');

    return html;
}

app.registerExtension({
    name: "Rulman.TerminalLog",
    async nodeCreated(node) {
        if (node.comfyClass === "TerminalLogNode") {
            const container = document.createElement("div");
            container.style.width = "100%";
            container.style.height = "340px";
            container.style.backgroundColor = "#0c0c0c";
            container.style.color = "#cccccc";
            container.style.fontFamily = "'Cascadia Code', 'Consolas', 'Courier New', monospace";
            container.style.fontSize = "13px";
            container.style.lineHeight = "1.35";
            container.style.padding = "8px";
            container.style.boxSizing = "border-box";
            container.style.overflowY = "auto";
            container.style.whiteSpace = "pre-wrap";
            container.style.wordBreak = "break-all";
            container.style.borderRadius = "6px";
            container.style.border = "1px solid #222222";
            container.style.boxShadow = "inset 0 0 12px rgba(0,0,0,0.8)";
            container.innerHTML = '<span style="color: #56d364;">[INFO]</span> Подключение к живой консоли Rulman...';

            const domWidget = node.addDOMWidget("terminal_view", "custom_log_view", container, {
                getValue() { return container.innerText; },
                setValue(v) { 
                    if (v !== undefined && v !== null) {
                        container.innerHTML = ansiToHtml(v);
                    }
                }
            });

            node.setSize([620, 500]);

            let lastRawLogs = "";

            const intervalId = setInterval(async () => {
                if (!app.graph || !app.graph.getNodeById(node.id)) {
                    clearInterval(intervalId);
                    return;
                }

                const fontSizeWidget = node.widgets?.find(w => w.name === "font_size");
                if (fontSizeWidget && fontSizeWidget.value) {
                    container.style.fontSize = `${fontSizeWidget.value}px`;
                }

                let cleanAnsi = false;
                const ansiWidget = node.widgets?.find(w => w.name === "clean_ansi_colors");
                if (ansiWidget) cleanAnsi = ansiWidget.value;

                try {
                    const response = await fetch(`/rulman/terminal_logs?clean_ansi=${cleanAnsi}&t=${Date.now()}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.logs && data.logs !== lastRawLogs) {
                            lastRawLogs = data.logs;
                            container.innerHTML = ansiToHtml(data.logs);
                            
                            setTimeout(() => {
                                container.scrollTop = container.scrollHeight + 10000;
                            }, 20);
                        }
                    }
                } catch (err) {
                    // Silent retry
                }
            }, 300);
        }
    }
});
