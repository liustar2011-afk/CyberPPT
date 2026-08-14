#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import os, platform, shutil, subprocess, sys, urllib.request, zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'runtime'
THIRD = ROOT / 'third_party'

NCNN_URLS = {
    'Windows': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip',
    'Linux': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip',
    'Darwin': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip',
}
REPOS = {
    'realesrgan': ('https://github.com/xinntao/Real-ESRGAN.git', THIRD / 'Real-ESRGAN'),
    'swinir': ('https://github.com/JingyunLiang/SwinIR.git', THIRD / 'SwinIR'),
}

def run(cmd, cwd=None):
    print('+', ' '.join(map(str, cmd)))
    subprocess.run(list(map(str, cmd)), cwd=str(cwd) if cwd else None, check=True)

def install_base():
    req = ROOT / 'requirements.txt'
    run([sys.executable, '-m', 'pip', 'install', '-r', req])

def download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent':'ppt-image-enhancer-skill/1.0'})
    with urllib.request.urlopen(req) as r, dest.open('wb') as f:
        total = int(r.headers.get('Content-Length') or 0); got = 0
        while True:
            chunk = r.read(1024*1024)
            if not chunk: break
            f.write(chunk); got += len(chunk)
            if total: print(f'  {got/1024/1024:.1f}/{total/1024/1024:.1f} MB', end='\r')
    print()

def install_ncnn(force=False):
    system = platform.system()
    if system not in NCNN_URLS:
        raise RuntimeError(f'No official portable NCNN package configured for {system}')
    target = RUNTIME / 'realesrgan-ncnn-vulkan'
    names = ['realesrgan-ncnn-vulkan.exe','realesrgan-ncnn-vulkan']
    if target.exists() and not force:
        for name in names:
            hits = list(target.rglob(name))
            if hits:
                print('NCNN already installed:', hits[0]); return hits[0]
    if force and target.exists(): shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    archive = RUNTIME / 'downloads' / f'realesrgan-ncnn-{system.lower()}.zip'
    print('Downloading official Real-ESRGAN NCNN portable package...')
    download(NCNN_URLS[system], archive)
    with zipfile.ZipFile(archive) as zf: zf.extractall(target)
    for name in names:
        hits = list(target.rglob(name))
        if hits:
            if system != 'Windows': hits[0].chmod(hits[0].stat().st_mode | 0o111)
            print('Installed:', hits[0]); return hits[0]
    raise RuntimeError('NCNN package extracted but executable was not found')

def clone_backend(name: str):
    url, dest = REPOS[name]
    git = shutil.which('git')
    if not git: raise RuntimeError('git is required for Python backends')
    if (dest/'.git').exists():
        print(name, 'already cloned:', dest); return dest
    if dest.exists() and any(dest.iterdir()): raise RuntimeError(f'Non-empty destination: {dest}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    run([git,'clone','--depth','1',url,dest])
    return dest

def install_realesrgan_python():
    repo = clone_backend('realesrgan')
    run([sys.executable,'-m','pip','install','-r',repo/'requirements.txt'])
    run([sys.executable,'-m','pip','install','-e',repo])

def install_swinir_python():
    clone_backend('swinir')
    run([sys.executable,'-m','pip','install','requests','timm'])
    print('SwinIR source installed. Install an appropriate PyTorch build separately if torch is not already present.')

def main():
    ap=argparse.ArgumentParser(description='Bootstrap optional AI SR backends for the Skill')
    ap.add_argument('--backend', choices=['auto','ncnn','realesrgan','swinir','all'], default='auto')
    ap.add_argument('--skip-base', action='store_true')
    ap.add_argument('--force', action='store_true')
    args=ap.parse_args()
    if not args.skip_base: install_base()
    b=args.backend
    if b=='auto':
        # Portable NCNN is the least fragile path for normal desktop use.
        try: install_ncnn(args.force)
        except Exception as e: print('NCNN setup failed:', e)
    elif b=='ncnn': install_ncnn(args.force)
    elif b=='realesrgan': install_realesrgan_python()
    elif b=='swinir': install_swinir_python()
    elif b=='all':
        install_ncnn(args.force); install_realesrgan_python(); install_swinir_python()
    print('Bootstrap complete. Run: python tools/doctor.py')

if __name__=='__main__': main()
