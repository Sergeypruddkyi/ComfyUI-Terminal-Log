import sys
import threading
import re
import logging

# Regex to remove ANSI color/formatting codes if requested
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class RawLogBuffer:
    """
    Stores exact raw output stream from sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__, and Python logging.
    100% exact replica of terminal stream.
    """
    def __init__(self, max_chars=100000):
        self.buffer = ""
        self.max_chars = max_chars
        self.lock = threading.Lock()

    def write(self, text):
        if not text:
            return
        with self.lock:
            self.buffer += text
            if len(self.buffer) > self.max_chars:
                self.buffer = self.buffer[-self.max_chars:]

    def get_logs(self, strip_ansi=False):
        with self.lock:
            content = self.buffer

        if strip_ansi:
            content = ANSI_ESCAPE.sub('', content)

        return content

global_raw_buffer = RawLogBuffer(max_chars=100000)

class OutputTee:
    def __init__(self, original_stream):
        self.original_stream = original_stream

    def write(self, text):
        try:
            global_raw_buffer.write(text)
        except Exception:
            pass
        if self.original_stream and hasattr(self.original_stream, 'write'):
            return self.original_stream.write(text)

    def flush(self):
        if self.original_stream and hasattr(self.original_stream, 'flush'):
            return self.original_stream.flush()

    def isatty(self):
        if self.original_stream and hasattr(self.original_stream, 'isatty'):
            return self.original_stream.isatty()
        return False

# Custom Handler to capture Python logging records (e.g. logging.info, ComfyUI logger)
class LogBufferLoggingHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            if msg:
                # Add [INFO], [WARNING], [ERROR] header if missing
                if not msg.startswith("[") and not msg.startswith("\x1b"):
                    msg = f"[{record.levelname}] {msg}"
                global_raw_buffer.write(msg + "\n")
        except Exception:
            pass

# 1. Attach logging handler to capture all Python logging (got prompt, Prompt executed, etc.)
try:
    logging_handler = LogBufferLoggingHandler()
    logging_handler.setFormatter(logging.Formatter('%(message)s'))
    
    root_logger = logging.getLogger()
    if not any(isinstance(h, LogBufferLoggingHandler) for h in root_logger.handlers):
        root_logger.addHandler(logging_handler)

    # Attach handler and wrap stream handlers on all registered loggers
    for lg in list(logging.Logger.manager.loggerDict.values()):
        if isinstance(lg, logging.Logger):
            if not any(isinstance(h, LogBufferLoggingHandler) for h in lg.handlers):
                lg.addHandler(logging_handler)
            for h in list(lg.handlers):
                if isinstance(h, logging.StreamHandler) and not isinstance(h.stream, OutputTee):
                    h.stream = OutputTee(h.stream)
except Exception as e:
    pass

# 2. Intercept sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__
if not getattr(sys.stdout, '_is_captured_by_terminal_node', False):
    orig_out = sys.stdout
    sys.stdout = OutputTee(orig_out)
    sys.stdout._is_captured_by_terminal_node = True

if not getattr(sys.stderr, '_is_captured_by_terminal_node', False):
    orig_err = sys.stderr
    sys.stderr = OutputTee(orig_err)
    sys.stderr._is_captured_by_terminal_node = True

if hasattr(sys, '__stdout__') and sys.__stdout__ and not getattr(sys.__stdout__, '_is_captured_by_terminal_node', False):
    orig_sys_out = sys.__stdout__
    sys.__stdout__ = OutputTee(orig_sys_out)
    sys.__stdout__._is_captured_by_terminal_node = True

if hasattr(sys, '__stderr__') and sys.__stderr__ and not getattr(sys.__stderr__, '_is_captured_by_terminal_node', False):
    orig_sys_err = sys.__stderr__
    sys.__stderr__ = OutputTee(orig_sys_err)
    sys.__stderr__._is_captured_by_terminal_node = True


# Register HTTP endpoint for live streaming to node UI
try:
    from server import PromptServer
    from aiohttp import web

    @PromptServer.instance.routes.get("/rulman/terminal_logs")
    async def get_terminal_logs_endpoint(request):
        try:
            clean_ansi = request.query.get("clean_ansi", "false").lower() == "true"
            logs = global_raw_buffer.get_logs(strip_ansi=clean_ansi)
            return web.json_response({"logs": logs})
        except Exception as e:
            return web.json_response({"logs": f"Error retrieving logs: {str(e)}"}, status=500)
except Exception as e:
    print(f"[Rulman Terminal Log] Route registration notice: {e}")


class TerminalLogNode:
    """
    100% Raw Stream Terminal Log Node for ComfyUI.
    Captures stdout, stderr, __stdout__, __stderr__ and Python logging handlers.
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "font_size": ("INT", {
                    "default": 13,
                    "min": 9,
                    "max": 28,
                    "step": 1,
                    "display": "number"
                }),
                "clean_ansi_colors": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("terminal_text",)
    OUTPUT_NODE = True
    FUNCTION = "get_logs"
    CATEGORY = "Rulman Nodes/Terminal"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def get_logs(self, font_size, clean_ansi_colors):
        logs = global_raw_buffer.get_logs(strip_ansi=clean_ansi_colors)
        if not logs:
            logs = "[Rulman Terminal Log: Waiting for terminal activity...]"

        return {"ui": {"text": [logs]}, "result": (logs,)}
