import subprocess, time
from pathlib import Path
project = Path(r'I:\website cloner')
chrome = Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
url = 'http' + ':' + '//' + '127.0.0.1:8021'
python = project / '.venv' / 'Scripts' / 'python.exe'
subprocess.Popen([str(python),'-m','uvicorn','main:app','--host','127.0.0.1','--port','8021'], cwd=str(project), creationflags=subprocess.CREATE_NO_WINDOW)
time.sleep(2)
subprocess.Popen([str(chrome), url])
