"""
display_tools.py - Robust Display Control Tools for J.A.R.V.I.S MK2
With proper resource management and error handling
"""

import logging
import os
import asyncio
import threading
import atexit
import weakref
from datetime import datetime
from contextlib import contextmanager, asynccontextmanager
from functools import wraps
from typing import Optional, Any, Dict
from livekit.agents import function_tool

# Windows-specific imports with better error handling
try:
    import win32gui
    import win32con
    import win32com.client
    import ctypes
    from PIL import ImageGrab
    import screen_brightness_control as sbc
    import pythoncom  # Important for COM threading
    WINDOWS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Windows-specific imports failed: {e}")
    WINDOWS_AVAILABLE = False

# Configure logging
logger = logging.getLogger("jarvis.display_tools")
logger.setLevel(logging.INFO)

# Global resource manager
class ResourceManager:
    """Centralized resource management for COM objects and other resources"""
    
    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._cleanup_registered = False
        self._thread_local = threading.local()
        
    def get_lock(self, resource_name: str) -> asyncio.Lock:
        """Get or create a lock for a specific resource"""
        if resource_name not in self._locks:
            self._locks[resource_name] = asyncio.Lock()
        return self._locks[resource_name]
    
    def register_cleanup(self):
        """Register cleanup function to run at exit"""
        if not self._cleanup_registered:
            atexit.register(self.cleanup_all)
            self._cleanup_registered = True
    
    def cleanup_all(self):
        """Clean up all registered resources"""
        logger.info("Cleaning up all resources...")
        for name, resource in self._resources.items():
            try:
                if hasattr(resource, 'Release'):
                    resource.Release()
                elif hasattr(resource, 'close'):
                    resource.close()
                logger.debug(f"Cleaned up resource: {name}")
            except Exception as e:
                logger.warning(f"Error cleaning up resource {name}: {e}")
        
        # Clean up COM
        try:
            pythoncom.CoUninitialize()
        except:
            pass
    
    @contextmanager
    def com_context(self, apartment_type=pythoncom.COINIT_APARTMENTTHREADED):
        """Context manager for COM initialization/cleanup"""
        com_initialized = False
        try:
            # Initialize COM for this thread if not already done
            if not hasattr(self._thread_local, 'com_initialized'):
                try:
                    pythoncom.CoInitializeEx(apartment_type)
                    self._thread_local.com_initialized = True
                    com_initialized = True
                    logger.debug("COM initialized for thread")
                except pythoncom.com_error as e:
                    if e.hresult != -2147417850:  # RPC_E_CHANGED_MODE
                        raise
                    logger.debug("COM already initialized for thread")
            
            yield
            
        except Exception as e:
            logger.error(f"Error in COM context: {e}")
            raise
        finally:
            # Only uninitialize if we initialized it
            if com_initialized:
                try:
                    pythoncom.CoUninitialize()
                    delattr(self._thread_local, 'com_initialized')
                    logger.debug("COM uninitialized for thread")
                except:
                    pass

# Global instance
resource_manager = ResourceManager()
resource_manager.register_cleanup()

def with_error_handling(func):
    """Decorator for consistent error handling and logging"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            logger.debug(f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
            result = await func(*args, **kwargs)
            logger.debug(f"Successfully executed {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            return f"Error in {func.__name__}: {str(e)}"
    return wrapper

def with_rate_limiting(min_interval: float = 0.1):
    """Decorator to rate limit function calls"""
    last_call_times = {}
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = func.__name__
            now = asyncio.get_event_loop().time()
            
            if func_name in last_call_times:
                time_since_last = now - last_call_times[func_name]
                if time_since_last < min_interval:
                    wait_time = min_interval - time_since_last
                    logger.debug(f"Rate limiting {func_name}, waiting {wait_time:.3f}s")
                    await asyncio.sleep(wait_time)
            
            last_call_times[func_name] = asyncio.get_event_loop().time()
            return await func(*args, **kwargs)
        return wrapper
    return decorator

@function_tool
@with_error_handling
@with_rate_limiting(0.2)
async def set_brightness(brightness: int) -> str:
    """
    Set screen brightness to specified level.
    
    Args:
        brightness: Brightness level from 0 to 100
        
    Returns:
        str: Success or error message
    """
    if not WINDOWS_AVAILABLE:
        return "Display controls not available on this system"
    
    async with resource_manager.get_lock("brightness"):
        try:
            brightness = max(0, min(100, brightness))
            
            # Use a more robust approach with retry logic
            for attempt in range(3):
                try:
                    sbc.set_brightness(brightness, display=0)
                    logger.info(f"Brightness set to {brightness}% for display 0")
                    return f"Screen brightness set to {brightness}%"
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        raise e
                    logger.warning(f"Brightness attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(0.5)
                    
        except Exception as e:
            logger.error(f"Error setting brightness: {e}")
            return f"Failed to set brightness: {str(e)}"

@function_tool
@with_error_handling
async def get_brightness() -> str:
    """
    Get current screen brightness level.
    
    Returns:
        str: Current brightness level
    """
    if not WINDOWS_AVAILABLE:
        return "Display controls not available on this system"
    
    async with resource_manager.get_lock("brightness"):
        try:
            brightness = sbc.get_brightness(display=0)
            current_level = brightness[0] if isinstance(brightness, list) else brightness
            logger.info(f"Current brightness: {current_level}%")
            return f"Current screen brightness is {current_level}%"
        except Exception as e:
            logger.error(f"Error getting brightness: {e}")
            return f"Failed to get brightness: {str(e)}"

@function_tool
@with_error_handling
@with_rate_limiting(1.0)  # Screenshots are more resource intensive
async def take_screenshot() -> str:
    """
    Take a screenshot of the current screen.
    
    Returns:
        str: Path to saved screenshot or error message
    """
    if not WINDOWS_AVAILABLE:
        return "Screenshot functionality not available on this system"
    
    async with resource_manager.get_lock("screenshot"):
        try:
            # Create screenshots directory if it doesn't exist
            os.makedirs("screenshots", exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshots/screenshot_{timestamp}.png"
            
            # Take screenshot in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            screenshot = await loop.run_in_executor(None, ImageGrab.grab)
            await loop.run_in_executor(None, screenshot.save, filename)
            
            logger.info(f"Screenshot saved: {filename}")
            return f"Screenshot saved successfully to {filename}"
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return f"Failed to take screenshot: {str(e)}"

@function_tool
@with_error_handling
async def get_screen_resolution() -> str:
    """
    Get current screen resolution.
    
    Returns:
        str: Current screen resolution
    """
    if not WINDOWS_AVAILABLE:
        return "Display information not available on this system"
    
    try:
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)
        
        logger.info(f"Screen resolution: {width}x{height}")
        return f"Current screen resolution is {width} x {height} pixels"
    except Exception as e:
        logger.error(f"Error getting screen resolution: {e}")
        return f"Failed to get screen resolution: {str(e)}"

@function_tool
@with_error_handling
@with_rate_limiting(0.5)
async def minimize_all_windows() -> str:
    """
    Minimize all open windows.
    
    Returns:
        str: Success or error message
    """
    if not WINDOWS_AVAILABLE:
        return "Window management not available on this system"
    
    async with resource_manager.get_lock("windows"):
        try:
            with resource_manager.com_context():
                shell = win32com.client.Dispatch("Shell.Application")
                shell.MinimizeAll()
                # Give time for windows to minimize
                await asyncio.sleep(0.5)
                logger.info("All windows minimized")
                return "All windows have been minimized"
        except Exception as e:
            logger.error(f"Error minimizing windows: {e}")
            return f"Failed to minimize windows: {str(e)}"

@function_tool
@with_error_handling
async def get_active_window() -> str:
    """
    Get information about the currently active window.
    
    Returns:
        str: Active window information
    """
    if not WINDOWS_AVAILABLE:
        return "Window information not available on this system"
    
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            window_text = win32gui.GetWindowText(hwnd)
            if window_text:
                logger.info(f"Active window: {window_text}")
                return f"Currently active window: {window_text}"
            else:
                return "No active window with title found"
        else:
            return "No active window found"
    except Exception as e:
        logger.error(f"Error getting active window: {e}")
        return f"Failed to get active window info: {str(e)}"

@function_tool
@with_error_handling
@with_rate_limiting(0.3)
async def switch_to_application(app_name: str) -> str:
    """
    Switch to/focus a specific application by name.
    
    Args:
        app_name: Name of the application to switch to
        
    Returns:
        str: Success or error message
    """
    if not WINDOWS_AVAILABLE:
        return "Application switching not available on this system"
    
    async with resource_manager.get_lock("windows"):
        try:
            def find_window_callback(hwnd, windows):
                try:
                    if win32gui.IsWindowVisible(hwnd):
                        window_text = win32gui.GetWindowText(hwnd)
                        if app_name.lower() in window_text.lower() and window_text:
                            windows.append((hwnd, window_text))
                except Exception:
                    pass  # Skip problematic windows
                return True
            
            windows = []
            win32gui.EnumWindows(find_window_callback, windows)
            
            if windows:
                hwnd, window_title = windows[0]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                await asyncio.sleep(0.1)  # Brief delay before setting foreground
                win32gui.SetForegroundWindow(hwnd)
                logger.info(f"Switched to application: {window_title}")
                return f"Switched to application: {window_title}"
            else:
                logger.warning(f"Application not found: {app_name}")
                return f"Could not find application containing '{app_name}'"
        except Exception as e:
            logger.error(f"Error switching to application: {e}")
            return f"Failed to switch to application: {str(e)}"

# Health check function
@function_tool
@with_error_handling
async def display_system_health() -> str:
    """
    Check the health of the display system and available functions.
    
    Returns:
        str: System health status
    """
    health_report = []
    
    # Check Windows availability
    health_report.append(f"Windows API Available: {WINDOWS_AVAILABLE}")
    
    # Check COM functionality
    try:
        with resource_manager.com_context():
            shell = win32com.client.Dispatch("Shell.Application")
            health_report.append("COM System: ✓ Working")
    except Exception as e:
        health_report.append(f"COM System: ✗ Error - {str(e)}")
    
    # Check brightness control
    try:
        current_brightness = sbc.get_brightness(display=0)
        health_report.append("Brightness Control: ✓ Working")
    except Exception as e:
        health_report.append(f"Brightness Control: ✗ Error - {str(e)}")
    
    # Check screenshot capability
    try:
        screenshot = ImageGrab.grab()
        health_report.append("Screenshot Capability: ✓ Working")
    except Exception as e:
        health_report.append(f"Screenshot Capability: ✗ Error - {str(e)}")
    
    return "\n".join(health_report)

# Simple test function with proper async handling
async def test_display_functions():
    """Test all display functions with proper error handling"""
    print("Testing display functions...")
    
    functions_to_test = [
        ("Health Check", display_system_health()),
        ("Get Brightness", get_brightness()),
        ("Set Brightness to 75%", set_brightness(75)),
        ("Get Screen Resolution", get_screen_resolution()),
        ("Get Active Window", get_active_window()),
        ("Take Screenshot", take_screenshot()),
    ]
    
    for name, coro in functions_to_test:
        try:
            print(f"\n{name}:")
            result = await coro
            print(f"  Result: {result}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Small delay between tests
        await asyncio.sleep(0.5)
    
    print("\nAll tests completed!")

# Legacy sync test function for backwards compatibility
def test_display_functions_sync():
    """Synchronous wrapper for the async test function"""
    print("Running display functions test...")
    try:
        asyncio.run(test_display_functions())
    except Exception as e:
        print(f"Test execution failed: {e}")

if __name__ == "__main__":
    # Run tests if executed directly
    test_display_functions_sync()