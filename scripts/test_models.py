"""
scripts/test_models.py — Testa todos os modelos disponíveis num take.
Útil para escolher qual modelo usar no solo ou na multidão.

Uso:
    python scripts/test_models.py --input input/take_05.wav
    python scripts/test_models.py --input input/take_05.wav --models DeAndre Celentano
"""

import argparse
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from core.converter import VoiceConverter, find_model_files

MODELS_DIR = pathlib.Path('models')


def main():
    parser = argparse.ArgumentParser(description='voci-studio — Teste de modelos')
    parser.add_argument('--input',   required=True, help='WAV de entrada')
    parser.add_argument('--models',  nargs='+', default=None,
                        help='Modelos a testar. Padrão: todos em models/')
    parser.add_argument('--pitch',   type=int, default=0)
    parser.add_argument('--device',  default='cuda:1')
    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    if not input_path.exists():
        print(f'[ERRO] {input_path} não encontrado')
        sys.exit(1)

    models = args.models or [d.name for d in MODELS_DIR.iterdir() if d.is_dir()]
    if not models:
        print(f'[ERRO] Nenhum modelo em {MODELS_DIR}/')
        sys.exit(1)

    output_dir = pathlib.Path('output')
    output_dir.mkdir(exist_ok=True)

    print(f'VoiceConverter carregando...')
    vc = VoiceConverter()
    print(f'OK — testando {len(models)} modelo(s) em {input_path.name}\n')

    results = []
    for name in models:
        try:
            pth, idx = find_model_files(MODELS_DIR, name)
        except FileNotFoundError as e:
            print(f'[{name}] ERRO: {e}\n')
            results.append((name, 'NÃO ENCONTRADO'))
            continue

        out = output_dir / f'test_{name}_{input_path.stem}.wav'
        print(f'[{name}]  →  {out.name}')

        ok = vc.convert(
            input_path=input_path,
            output_path=out,
            model_pth=pth,
            model_index=idx,
            pitch=args.pitch,
            device=args.device,
        )
        size = out.stat().st_size // 1024 if ok else 0
        status = f'OK ({size}KB)' if ok else 'FALHOU'
        print(f'  {status}\n')
        results.append((name, status))

    print('─' * 45)
    print('RESUMO:')
    for name, status in results:
        print(f'  {name:20s} → {status}')
    print(f'\nDownload:  scp servidor:{output_dir}/test_*.wav ./')


if __name__ == '__main__':
    main()
