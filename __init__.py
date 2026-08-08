from .terminal_log_node import TerminalLogNode

NODE_CLASS_MAPPINGS = {
    "TerminalLogNode": TerminalLogNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TerminalLogNode": "Rulman Terminal Log"
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
