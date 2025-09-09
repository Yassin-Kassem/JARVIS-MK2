"""
system_tools.py - Simple and Reliable System Control Tools for J.A.R.V.I.S MK2

Simplified audio control functions that focus on reliability over complexity.

Dependencies:
  pip install pycaw comtypes

Usage:
  from system_tools import set_system_volume, get_system_volume, mute_system_audio, unmute_system_audio
"""

import logging
import asyncio
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL, CoInitialize, CoUninitialize
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Configure logging
logger = logging.getLogger("jarvis.system_tools")
logger.setLevel(logging.INFO)

# LiveKit function tool decorator
try:
    from livekit.agents import function_tool
except ImportError:
    # Fallback stub for offline testing
    def function_tool():
        def _decor(fn):
            return fn
        return _decor


def _get_volume_interface():
    """Get the audio volume interface with proper COM initialization"""
    try:
        # Initialize COM
        CoInitialize()
        
        # Get the default audio device
        devices = AudioUtilities.GetSpeakers()
        if not devices:
            raise RuntimeError("No audio output devices found")
        
        # Get the volume interface
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        return volume
        
    except Exception as e:
        logger.error(f"Failed to get volume interface: {e}")
        raise RuntimeError(f"Audio interface error: {e}")


def _cleanup_com():
    """Clean up COM resources"""
    try:
        CoUninitialize()
    except Exception as e:
        logger.warning(f"COM cleanup warning: {e}")


def _set_volume_sync(level: int) -> str:
    """Synchronous volume setting function to run in thread"""
    try:
        # Clamp level to valid range
        level = max(0, min(level, 100))
        scalar = float(level) / 100.0
        
        # Get volume interface and set volume
        volume = _get_volume_interface()
        volume.SetMasterVolumeLevelScalar(scalar, None)
        
        # Clean up
        _cleanup_com()
        
        logger.info(f"Volume set to {level}%")
        return f"System volume set to {level}%"
        
    except Exception as e:
        _cleanup_com()
        error_msg = f"Unable to set volume: {str(e)}"
        logger.error(error_msg)
        return error_msg


def _get_volume_sync() -> str:
    """Synchronous volume getting function to run in thread"""
    try:
        # Get volume interface and current volume
        volume = _get_volume_interface()
        scalar = volume.GetMasterVolumeLevelScalar()
        pct = int(round(scalar * 100))
        
        # Clean up
        _cleanup_com()
        
        logger.info(f"Current volume: {pct}%")
        return f"System volume is {pct}%"
        
    except Exception as e:
        _cleanup_com()
        error_msg = f"Unable to get volume: {str(e)}"
        logger.error(error_msg)
        return error_msg


def _mute_audio_sync() -> str:
    """Synchronous audio muting function to run in thread"""
    try:
        # Get volume interface and mute
        volume = _get_volume_interface()
        volume.SetMute(1, None)
        
        # Clean up
        _cleanup_com()
        
        logger.info("System audio muted")
        return "System audio muted"
        
    except Exception as e:
        _cleanup_com()
        error_msg = f"Unable to mute audio: {str(e)}"
        logger.error(error_msg)
        return error_msg


def _unmute_audio_sync() -> str:
    """Synchronous audio unmuting function to run in thread"""
    try:
        # Get volume interface and unmute
        volume = _get_volume_interface()
        volume.SetMute(0, None)
        
        # Clean up
        _cleanup_com()
        
        logger.info("System audio unmuted")
        return "System audio unmuted"
        
    except Exception as e:
        _cleanup_com()
        error_msg = f"Unable to unmute audio: {str(e)}"
        logger.error(error_msg)
        return error_msg


@function_tool()
async def set_system_volume(level: int) -> str:
    """
    Set system volume level (0-100).
    
    Args:
        level: Volume level from 0 (silent) to 100 (maximum)
    
    Returns:
        str: Confirmation message
    """
    # Run the blocking COM operation in a thread pool
    return await asyncio.to_thread(_set_volume_sync, level)


@function_tool()
async def get_system_volume() -> str:
    """
    Get current system volume level.
    
    Returns:
        str: Current volume level message
    """
    # Run the blocking COM operation in a thread pool
    return await asyncio.to_thread(_get_volume_sync)


@function_tool()
async def mute_system_audio() -> str:
    """
    Mute system audio.
    
    Returns:
        str: Confirmation message
    """
    # Run the blocking COM operation in a thread pool
    return await asyncio.to_thread(_mute_audio_sync)


@function_tool()
async def unmute_system_audio() -> str:
    """
    Unmute system audio.
    
    Returns:
        str: Confirmation message
    """
    # Run the blocking COM operation in a thread pool
    return await asyncio.to_thread(_unmute_audio_sync)


# Simple test function
async def test_audio_functions():
    """Test all audio functions to verify they work"""
    print("Testing audio functions...")
    
    try:
        # Test get volume
        result = await get_system_volume()
        print(f"Get volume: {result}")
        
        # Test set volume
        result = await set_system_volume(50)
        print(f"Set volume to 50%: {result}")
        
        # Test mute
        result = await mute_system_audio()
        print(f"Mute: {result}")
        
        # Test unmute
        result = await unmute_system_audio()
        print(f"Unmute: {result}")
        
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_audio_functions())
