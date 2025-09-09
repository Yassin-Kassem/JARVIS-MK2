# tools/tool_registry.py

from tools.tools import fetch_weather, search_web
from tools.system_tools import (
    set_system_volume, mute_system_audio, get_system_volume, unmute_system_audio
)
from tools.display_tools import (
    set_brightness, get_brightness, take_screenshot, get_screen_resolution,
    minimize_all_windows, switch_to_application
)

class ToolRegistry:
    def __init__(self):
        # All tools available in the system
        self.available_tools = {
            "weather": fetch_weather,
            "web_search": search_web,
            "set_volume": set_system_volume,
            "get_volume": get_system_volume,
            "mute_audio": mute_system_audio,
            "unmute_audio": unmute_system_audio,
            "set_brightness": set_brightness,
            "get_brightness": get_brightness,
            "screenshot": take_screenshot,
            "screen_resolution": get_screen_resolution,
            "minimize_windows": minimize_all_windows,
            "switch_app": switch_to_application,
        }

        # Default enabled tools
        self.enabled_tools = {
            "weather", "web_search", "set_volume", "get_volume", "mute_audio" ,"set_brightness", 
            "get_brightness", "screenshot", "screen_resolution", "minimize_windows", "switch_app"
        }

    def enable_tool(self, tool_name: str):
        if tool_name in self.available_tools:
            self.enabled_tools.add(tool_name)

    def disable_tool(self, tool_name: str):
        if tool_name in self.enabled_tools:
            self.enabled_tools.remove(tool_name)

    def get_active_tools(self):
        return [self.available_tools[t] for t in self.enabled_tools if t in self.available_tools]
