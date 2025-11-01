set -e
echo "PWD: $(pwd)"
for d in /app /usr/src/app /code /workspace /; do 
  echo "== $d"
  ls -la "$d" 2>/dev/null || echo "not found"
done
python3 - << 'PY'
import sys, pkgutil, site
print('sys.path=', sys.path)
print('site=', getattr(site,'getsitepackages', lambda:[])())
print('mods:', [m.name for m in pkgutil.iter_modules() if m.name.startswith('campaign_')])
PY
