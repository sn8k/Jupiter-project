"""Dynamic analysis tracer."""
import sys
import json
import atexit
import os
import time
from collections import defaultdict

class Tracer:
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.calls = defaultdict(int)
        self.times = defaultdict(float)
        self.call_graph = defaultdict(lambda: defaultdict(int))
        self.active_frames = {}

    def _get_func_key(self, frame):
        code = frame.f_code
        filename = code.co_filename
        
        # Check if file is within root
        if not filename.startswith(self.root):
            return None

        # Get relative path
        try:
            rel_path = os.path.relpath(filename, self.root)
        except ValueError:
            return None
            
        if rel_path.startswith(".."):
             return None

        func_name = code.co_name
        return f"{rel_path}::{func_name}"

    def trace_func(self, frame, event, arg):
        if event == 'call':
            key = self._get_func_key(frame)
            if key:
                self.calls[key] += 1
                self.active_frames[frame] = time.perf_counter()
                
                # Track caller -> callee
                if frame.f_back:
                    caller_key = self._get_func_key(frame.f_back)
                    if caller_key:
                        self.call_graph[caller_key][key] += 1
            return self.trace_func

        elif event == 'return':
            key = self._get_func_key(frame)
            if key and frame in self.active_frames:
                start_time = self.active_frames.pop(frame)
                duration = time.perf_counter() - start_time
                self.times[key] += duration
            return self.trace_func
            
        return self.trace_func

def main():
    # Usage: python -m jupiter.core.tracer <output_file> <root_dir> <script> [args...]
    if len(sys.argv) < 4:
        print("Usage: python -m jupiter.core.tracer <output_file> <root_dir> <script> [args...]", file=sys.stderr)
        sys.exit(1)

    output_file = sys.argv[1]
    root_dir = sys.argv[2]
    script_path = sys.argv[3]
    script_args = sys.argv[3:]

    tracer = Tracer(root_dir)
    sys.settrace(tracer.trace_func)
    
    def save_results():
        try:
            # Convert defaultdicts to dicts for JSON serialization
            results = {
                "calls": dict(tracer.calls),
                "times": dict(tracer.times),
                "call_graph": {k: dict(v) for k, v in tracer.call_graph.items()}
            }
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            print(f"Error saving trace results: {e}", file=sys.stderr)
    
    atexit.register(save_results)

    # Prepare environment for the script
    sys.argv = script_args
    sys.path.insert(0, os.path.dirname(os.path.abspath(script_path)))
    
    try:
        # We use runpy or exec. Exec is simpler for a script file.
        with open(script_path, 'rb') as f:
            code = compile(f.read(), script_path, 'exec')
            
        # Execute in a new namespace
        globs = {
            '__name__': '__main__',
            '__file__': script_path,
            '__doc__': None,
            '__package__': None,
        }
        exec(code, globs)
    except SystemExit:
        pass
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
