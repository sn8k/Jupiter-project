"""Tests for dynamic analysis integration."""

import sys
import os
import time
from unittest.mock import MagicMock
from jupiter.core.tracer import Tracer

def test_tracer_logic():
    """Test the tracer logic in isolation."""
    root_path = os.path.abspath("/root")
    tracer = Tracer(root_path)
    
    # Mock a frame
    mock_code = MagicMock()
    mock_code.co_filename = os.path.join(root_path, "script.py")
    mock_code.co_name = "my_func"
    
    mock_frame = MagicMock()
    mock_frame.f_code = mock_code
    mock_frame.f_back = None
    
    # Simulate call
    tracer.trace_func(mock_frame, "call", None)
    
    assert tracer.calls["script.py::my_func"] == 1
    assert mock_frame in tracer.active_frames

    # Simulate return
    time.sleep(0.001) # Ensure some time passes
    tracer.trace_func(mock_frame, "return", None)
    
    assert "script.py::my_func" in tracer.times
    assert tracer.times["script.py::my_func"] > 0

def test_tracer_call_graph():
    """Test call graph construction."""
    root_path = os.path.abspath("/root")
    tracer = Tracer(root_path)
    
    # Caller frame
    caller_code = MagicMock()
    caller_code.co_filename = os.path.join(root_path, "main.py")
    caller_code.co_name = "main"
    caller_frame = MagicMock()
    caller_frame.f_code = caller_code
    caller_frame.f_back = None
    
    # Callee frame
    callee_code = MagicMock()
    callee_code.co_filename = os.path.join(root_path, "utils.py")
    callee_code.co_name = "helper"
    callee_frame = MagicMock()
    callee_frame.f_code = callee_code
    callee_frame.f_back = caller_frame
    
    # Simulate call to callee
    tracer.trace_func(callee_frame, "call", None)
    
    assert tracer.call_graph["main.py::main"]["utils.py::helper"] == 1
