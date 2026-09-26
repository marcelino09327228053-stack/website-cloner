import subprocess, time
from pathlib import Path
project = Path(r'I:\website cloner')
chrome = Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe')
url = 'http' + ':' + '//' + '127.0.0.1:8010'
subprocess.Popen(['python','-m','uvicorn','main:app','--host','127.0.0.1','--port','8010'], cwd=str(project))
time.sleep(2)
subprocess.Popen([str(chrome), url])
