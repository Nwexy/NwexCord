import subprocess
import os
import re
import time
import threading
import tempfile
from Tools.System.manager import SystemManager


class LiveStreamManager:
    """Manager for Flask-based Live Screen streaming with Cloudflare Tunnels."""
    
    _flask_thread = None
    _cf_process = None
    _is_running = False
    _public_url = None
    _audio_enabled = False  # Disabled by default until user clicks Join
    _audio_buffer = []  # Thread-safe buffer of audio chunks
    _audio_lock = None  # Threading lock for buffer access
    _audio_capture_thread = None
    _audio_sample_rate = 44100
    _audio_channels = 2
    
    _current_monitor = 0
    _current_res = "720p"
    
    @staticmethod
    def _init_audio_lock():
        import threading
        if LiveStreamManager._audio_lock is None:
            LiveStreamManager._audio_lock = threading.Lock()
    
    @staticmethod
    def _make_wav_chunk(pcm_data, sample_rate, channels):
        """Create a complete small WAV file from PCM data."""
        import struct
        bits = 16
        data_size = len(pcm_data)
        byte_rate = sample_rate * channels * (bits // 8)
        block_align = channels * (bits // 8)
        
        header = b'RIFF'
        header += struct.pack('<L', 36 + data_size)
        header += b'WAVE'
        header += b'fmt '
        header += struct.pack('<L', 16)
        header += struct.pack('<H', 1)  # PCM
        header += struct.pack('<H', channels)
        header += struct.pack('<L', sample_rate)
        header += struct.pack('<L', byte_rate)
        header += struct.pack('<H', block_align)
        header += struct.pack('<H', bits)
        header += b'data'
        header += struct.pack('<L', data_size)
        return header + pcm_data

    @staticmethod
    def _audio_capture_loop():
        """Background thread: captures system audio into buffer chunks."""
        import pyaudiowpatch as pyaudio
        import numpy as np
        
        LiveStreamManager._init_audio_lock()
        p = pyaudio.PyAudio()
        
        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            if not default_speakers["isLoopbackDevice"]:
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        default_speakers = loopback
                        break
            
            rate = int(default_speakers["defaultSampleRate"])
            channels = default_speakers["maxInputChannels"]
            LiveStreamManager._audio_sample_rate = rate
            LiveStreamManager._audio_channels = channels
            
            # Capture in ~0.5 second segments
            chunk_size = rate // 2  # 0.5s worth of samples
            
            stream = p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                frames_per_buffer=1024,
                input=True,
                input_device_index=default_speakers["index"],
            )
            
            accumulated = b''
            bytes_per_chunk = chunk_size * channels * 2  # 16-bit = 2 bytes
            
            last_chunk_hash = None
            
            while LiveStreamManager._is_running:
                if not LiveStreamManager._audio_enabled:
                    # When disabled, just drain the buffer to prevent buildup
                    try:
                        stream.read(1024, exception_on_overflow=False)
                    except:
                        pass
                    time.sleep(0.05)
                    continue
                
                try:
                    data = stream.read(1024, exception_on_overflow=False)
                except Exception:
                    break
                
                accumulated += data
                
                if len(accumulated) >= bytes_per_chunk:
                    chunk_pcm = accumulated[:bytes_per_chunk]
                    accumulated = accumulated[bytes_per_chunk:]
                    
                    # Silence & duplicate detection
                    audio_arr = np.frombuffer(chunk_pcm, dtype=np.int16)
                    energy = np.sqrt(np.mean(audio_arr.astype(np.float32)**2))
                    
                    # Higher threshold to filter out feedback artifacts
                    if energy < 80:
                        continue  # Skip silent chunks
                    
                    # Skip exact duplicate chunks (loopback glitch)
                    chunk_hash = hash(chunk_pcm[:2048])  # Hash first portion for speed
                    if chunk_hash == last_chunk_hash:
                        continue
                    last_chunk_hash = chunk_hash
                    
                    # Create a complete WAV file for this chunk
                    wav_chunk = LiveStreamManager._make_wav_chunk(chunk_pcm, rate, channels)
                    
                    with LiveStreamManager._audio_lock:
                        LiveStreamManager._audio_buffer.append(wav_chunk)
                        # Keep max 10 chunks in buffer (~5 seconds)
                        if len(LiveStreamManager._audio_buffer) > 10:
                            LiveStreamManager._audio_buffer = LiveStreamManager._audio_buffer[-10:]
                            
        except Exception as e:
            print(f"Audio capture error: {e}")
        finally:
            p.terminate()
    
    @staticmethod
    def _start_audio_capture():
        """Start the background audio capture thread."""
        import threading
        LiveStreamManager._init_audio_lock()
        if LiveStreamManager._audio_capture_thread and LiveStreamManager._audio_capture_thread.is_alive():
            return
        LiveStreamManager._audio_buffer = []
        LiveStreamManager._audio_capture_thread = threading.Thread(
            target=LiveStreamManager._audio_capture_loop, daemon=True
        )
        LiveStreamManager._audio_capture_thread.start()

    @staticmethod
    def _gen_frames():
        from PIL import ImageGrab
        while LiveStreamManager._is_running:
            try:
                monitors = SystemManager.get_monitors()
                if not monitors:
                    img = ImageGrab.grab(all_screens=True)
                else:
                    idx = LiveStreamManager._current_monitor
                    if idx >= len(monitors) or idx < 0:
                        idx = 0
                    if LiveStreamManager._current_monitor == -1: # All monitors
                        img = ImageGrab.grab(all_screens=True)
                    else:
                        img = ImageGrab.grab(all_screens=True, bbox=monitors[idx])
                
                res = LiveStreamManager._current_res
                if res == "1080p":
                    img.thumbnail((1920, 1080))
                    qual = 70
                elif res == "720p":
                    img.thumbnail((1280, 720))
                    qual = 60
                elif res == "480p":
                    img.thumbnail((854, 480))
                    qual = 40
                else:  # Original
                    qual = 80
                    
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=qual)
                frame = buf.getvalue()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.05) # Max ~20 FPS
            except Exception:
                time.sleep(0.5)

    @staticmethod
    def _run_flask():
        from flask import Flask, Response, request, jsonify
        app = Flask(__name__)
        # Suppress Flask logging
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        @app.route('/')
        def index():
            monitors = SystemManager.get_monitors()
            monitor_opts = f'<option value="-1" {"selected" if LiveStreamManager._current_monitor == -1 else ""}>All Monitors</option>'
            for i in range(len(monitors)):
                sel = "selected" if LiveStreamManager._current_monitor == i else ""
                monitor_opts += f'<option value="{i}" {sel}>Monitor {i+1}</option>'
                
            res_opts = ""
            for r in ["1080p", "720p", "480p", "Original"]:
                sel = "selected" if LiveStreamManager._current_res == r else ""
                res_opts += f'<option value="{r}" {sel}>{r}</option>'


            return f'''
            <html>
              <head>
                <title>NwexCord Live Stream</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                  body {{ background-color: #0e0e10; color: #fff; text-align: center; margin: 0; padding: 0; overflow: hidden; font-family: 'Segoe UI', sans-serif; height: 100vh; width: 100vw; }}
                  #controls {{ position: absolute; top: 15px; left: 15px; background: rgba(20,20,25,0.9); padding: 15px; border-radius: 12px; z-index: 999; display: flex; gap: 12px; border: 1px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.5); transition: opacity 0.3s; opacity: 0.8; }}
                  #controls:hover {{ opacity: 1; }}
                  select, button {{ background: #2f3136; color: white; border: 1px solid #4f545c; padding: 8px 12px; border-radius: 6px; outline: none; cursor: pointer; font-weight: 500; transition: 0.2s; }}
                  select:hover, button:hover {{ background: #4f545c; border-color: #7289da; }}
                  #audio_toggle {{ background: #43b581; color: white; border: none; min-width: 160px; }}
                  #audio_toggle.active {{ background: #ed4245; }}
                  img {{ width: 100vw; height: 100vh; object-fit: contain; display: block; }}
                  .status-dot {{ display: inline-block; width: 8px; height: 8px; background: #43b581; border-radius: 50%; margin-right: 5px; }}
                </style>
              </head>
              <body>
                <div id="controls">
                  <div style="display: flex; flex-direction: column; gap: 8px; align-items: flex-start;">
                    <div style="font-size: 0.8em; color: #aaa; margin-bottom: 2px;"><span class="status-dot"></span>LIVE SCREEN</div>
                    <div style="display: flex; gap: 10px;">
                      <select id="monitor" onchange="updateSettings()">{monitor_opts}</select>
                      <select id="res" onchange="updateSettings()">{res_opts}</select>
                    </div>
                    <div style="display: flex; gap: 10px; width: 100%;">
                      <button id="audio_toggle" onclick="toggleAudio()">🔊 Join Live Audio</button>
                      <button onclick="location.reload()">🔄 Refresh</button>
                    </div>
                  </div>
                </div>
                
                <img id="stream_img" src="/stream" />
                
                <script>
                  let controls = document.getElementById("controls");
                  let hideTimeout;
                  let audioActive = false;
                  let audioCtx = null;
                  let pollTimer = null;
                  let chunkIndex = 0;

                  document.addEventListener("mousemove", () => {{
                    controls.style.opacity = "1";
                    clearTimeout(hideTimeout);
                    hideTimeout = setTimeout(() => controls.style.opacity = "0.2", 3000);
                  }});
                  
                  function updateSettings() {{
                    const mon = document.getElementById("monitor").value;
                    const res = document.getElementById("res").value;
                    fetch("/config", {{
                      method: "POST",
                      headers: {{"Content-Type": "application/json"}},
                      body: JSON.stringify({{monitor: mon, resolution: res}})
                    }});
                  }}
                  
                  async function fetchAndPlayChunk() {{
                    if (!audioActive) return;
                    try {{
                      const resp = await fetch("/audio_chunk?after=" + chunkIndex);
                      const data = await resp.json();
                      
                      if (data.chunks && data.chunks.length > 0) {{
                        for (const chunkB64 of data.chunks) {{
                          try {{
                            const raw = atob(chunkB64);
                            const arr = new Uint8Array(raw.length);
                            for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
                            
                            const audioBuffer = await audioCtx.decodeAudioData(arr.buffer.slice(0));
                            const source = audioCtx.createBufferSource();
                            source.buffer = audioBuffer;
                            source.connect(audioCtx.destination);
                            source.start(0);
                          }} catch(e) {{
                            console.warn("Chunk decode error:", e);
                          }}
                        }}
                        chunkIndex = data.next_index;
                      }}
                    }} catch(e) {{
                      console.warn("Audio poll error:", e);
                    }}
                    
                    if (audioActive) {{
                      pollTimer = setTimeout(fetchAndPlayChunk, 500);
                    }}
                  }}
                  
                  async function toggleAudio() {{
                    const btn = document.getElementById("audio_toggle");
                    
                    if (!audioActive) {{
                      // Enable audio
                      btn.innerText = "⏳ Connecting...";
                      
                      // Tell server to start capturing
                      await fetch("/audio_toggle", {{method: "POST", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{enable: true}})}});
                      
                      // Create AudioContext (requires user gesture)
                      if (!audioCtx) {{
                        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                      }}
                      if (audioCtx.state === "suspended") {{
                        await audioCtx.resume();
                      }}
                      
                      audioActive = true;
                      chunkIndex = 0;
                      btn.innerText = "🔇 Stop Listening";
                      btn.classList.add("active");
                      
                      // Start polling for audio chunks
                      fetchAndPlayChunk();
                      
                    }} else {{
                      // Disable audio
                      audioActive = false;
                      if (pollTimer) clearTimeout(pollTimer);
                      pollTimer = null;
                      
                      // Tell server to stop capturing
                      await fetch("/audio_toggle", {{method: "POST", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{enable: false}})}});
                      
                      btn.innerText = "🔊 Join Live Audio";
                      btn.classList.remove("active");
                    }}
                  }}
                </script>
              </body>
            </html>
            '''

        @app.route('/stream')
        def stream():
            return Response(LiveStreamManager._gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @app.route('/audio_chunk')
        def audio_chunk():
            """Return buffered audio chunks as JSON with base64-encoded WAV files."""
            import base64
            after = int(request.args.get('after', 0))
            LiveStreamManager._init_audio_lock()
            
            with LiveStreamManager._audio_lock:
                buf = LiveStreamManager._audio_buffer
                total = len(buf)
                
                if after >= total:
                    return jsonify({"chunks": [], "next_index": total})
                
                # Return new chunks since 'after'
                new_chunks = buf[after:]
                encoded = [base64.b64encode(c).decode('ascii') for c in new_chunks]
                return jsonify({"chunks": encoded, "next_index": total})
        
        @app.route('/audio_toggle', methods=['POST'])
        def audio_toggle():
            """Enable or disable audio capture."""
            data = request.json or {}
            enable = data.get('enable', False)
            LiveStreamManager._audio_enabled = enable
            LiveStreamManager._init_audio_lock()
            if enable:
                # Clear old buffer and restart capture if needed
                with LiveStreamManager._audio_lock:
                    LiveStreamManager._audio_buffer = []
                LiveStreamManager._start_audio_capture()
            else:
                with LiveStreamManager._audio_lock:
                    LiveStreamManager._audio_buffer = []
            return jsonify({"status": "ok", "audio_enabled": LiveStreamManager._audio_enabled})
            
        @app.route('/config', methods=['POST'])
        def config():
            data = request.json
            if 'monitor' in data: LiveStreamManager._current_monitor = int(data['monitor'])
            if 'resolution' in data: LiveStreamManager._current_res = data['resolution']
            return jsonify({"status": "ok"})
            
        try:
            app.run(host='127.0.0.1', port=8080, threaded=True, use_reloader=False)
        except Exception as e:
            print(f"Flask execution failed: {e}")

    @staticmethod
    def start_stream():
        if LiveStreamManager._is_running:
            return True, LiveStreamManager._public_url
            
        try:
            # 1. Start Flask in background thread
            LiveStreamManager._is_running = True
            from werkzeug.serving import make_server
            import threading
            
            LiveStreamManager._flask_thread = threading.Thread(target=LiveStreamManager._run_flask, daemon=True)
            LiveStreamManager._flask_thread.start()
            
            # Start audio capture thread
            LiveStreamManager._start_audio_capture()
            
            # 2. Setup Cloudflared
            if not os.path.exists("cloudflared.exe"):
                # start.bat should have downloaded this. If not, fail cleanly.
                return False, "cloudflared.exe not found! Start the bot via start.bat to install it automatically."
                
            # 3. Start Cloudflared
            LiveStreamManager._cf_process = subprocess.Popen(
                ["cloudflared.exe", "tunnel", "--url", "http://localhost:8080"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            start_time = time.time()
            url = None
            
            # Read stderr to extract the trycloudflare url
            while time.time() - start_time < 15:
                # Use non-blocking read or a small timeout if needed, butreadline is fine here for startup
                line = LiveStreamManager._cf_process.stderr.readline()
                if not line:
                    break
                match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
                if match:
                    url = match.group(1)
                    break
                    
            if url:
                LiveStreamManager._public_url = url
                return True, url
            else:
                LiveStreamManager.stop_stream()
                return False, "Failed to get Cloudflare Tunnel URL within 15 seconds."
                
        except Exception as e:
            LiveStreamManager.stop_stream()
            err_msg = str(e)
            if "WinError 193" in err_msg or "not a valid Win32 application" in err_msg:
                err_msg = "Corrupted cloudflared.exe detected! To fix this, delete the 'cloudflared.exe' file in the NwexCord folder and run start.bat again to download a fresh copy."
            return False, err_msg

    @staticmethod
    def stop_stream():
        LiveStreamManager._is_running = False
        if LiveStreamManager._cf_process:
            LiveStreamManager._cf_process.terminate()
            try:
                LiveStreamManager._cf_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                LiveStreamManager._cf_process.kill()
            LiveStreamManager._cf_process = None
            
        # Stopping flask completely requires advanced werkzeug server keeping track. 
        # But we made the thread daemon, and we shut down the stream generating loop.
        # It's fine to leave Flask hanging in daemon, or we could just kill the process instead, but daemon is fine.
        LiveStreamManager._public_url = None
        return True, "Live stream stopped successfully."


