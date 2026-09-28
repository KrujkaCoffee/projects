import subprocess

args = [
'C:\\Users\\A.A.Fedorov\\MES\\py\\python.EXE', '-m', 'pip', 'install', '--ignore-installed', '--disable-pip-version-check', '--no-index', '--find-links', 'C:\\Users\\AAEE1B~1.FED\\AppData\\Local\\Temp\\mes_libs\\3b23028afc3f0a84ab899e10238acce99c6dbde62d1c8a4c9ccdd1e467ac512720260909', '--force-reinstall', 'anyio==4.14.2', 'openai==1.50.0', 'pydantic==2.9.2'

]
result = subprocess.run(args, capture_output=True, encoding="utf-8", text=True, errors='replace')
print(result.stdout)
print(result.stderr)