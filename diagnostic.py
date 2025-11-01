import sys, os, site, pkgutil
print('sys.path=', sys.path)
print('site=', getattr(site, 'getsitepackages', lambda: [])())
print('has_/app=', os.path.exists('/app'))
print('ls_/app=', os.listdir('/app') if os.path.exists('/app') else [])
mods = [m.name for m in pkgutil.iter_modules()]
print('mods_like_campaign=', [m for m in mods if m.startswith('campaign_')])
