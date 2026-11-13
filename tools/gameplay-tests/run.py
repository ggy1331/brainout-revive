import os,sys,threading,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
LAB=ROOT/'build/gameplay-lab'
sys.path.insert(0,str(ROOT/'tools/mock-backend'))
from backend import App,Handler,Storage,ThreadingHTTPServer
from services import game,hub
hub.PORT=0
http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
endpoint='127.0.0.1:'+str(http.server_port)
java=ROOT.parent/'tools/jdk-17.0.21+9/bin/java.exe'
app=App('http://'+endpoint,Storage(LAB/'profile'),java=str(java),server_dir=str(ROOT/'bin/server'),logs_dir=str(LAB/'logs'))
app.hub_port=http.server_port;app.hub=hub.Hub(app,'GameplayLab','gameplay-lab-local-key');http.app=app
threading.Thread(target=http.serve_forever,daemon=True).start()
env=dict(os.environ,DESKTOP_PROFILE_NAME='GameplayLab',BRAINOUT_HUB_ENDPOINT=endpoint,BRAINOUT_OWNER_KEY='gameplay-lab-local-key',GAMEPLAY_LAB=str(LAB))
try:
 with (LAB/'client.log').open('w',encoding='utf8') as log:
  proc=subprocess.Popen([str(java),'-cp',str(LAB)+';brainout-desktop.jar','GameplaySmoke','--unsafe','--auto-continue','--name','GameplayLab','--env','http://'+endpoint+'/environment'],cwd=ROOT/'bin/client',env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
  print('Test client',proc.pid,flush=True)
  try:proc.wait(timeout=155)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait();raise
finally:
 game._master(app).shutdown();http.shutdown()
text=(LAB/'client.log').read_text(errors='replace')
print('\n'.join(l for l in text.splitlines() if 'PASS' in l or 'FAIL' in l or 'Exception' in l or 'Error' in l),flush=True)
assert 'GAMEPLAY_SMOKE_PASS' in text
