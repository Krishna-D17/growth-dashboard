import subprocess, json

cmd = ["powershell", "-Command", "Get-CimInstance Win32_Process | Select-Object ProcessId, Name, CommandLine | ConvertTo-Json"]
res = subprocess.run(cmd, capture_output=True, text=True)
try:
    procs = json.loads(res.stdout)
    for p in procs:
        cmdline = p.get("CommandLine") or ""
        if "SocialScope" in cmdline or "growth dashboard" in cmdline:
            print(f"PID: {p.get('ProcessId')}, Name: {p.get('Name')}, Cmd: {cmdline}")
except Exception as e:
    print(f"Error parsing JSON: {e}")
    print(res.stdout[:1000])
