"""
scripts/convert.py — CLI para conversão RVC de um ou mais takes.

Uso:
    # Converter um take com um modelo
    python scripts/convert.py --input input/take_06.wav --model DeAndre --out output/solo.wav

    # Converter um take com todos os modelos disponíveis (comparativo)
    python scripts/convert.py --input input/take_09.wav --all-models --prefix crowd_

    # Carregar config de projeto
    python scripts/convert.py --project projects/colonia_cecilia/config.yaml
"""

import argparse
import os
import sys
import pathlib

# Garantir que o pacote core seja encontrado
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

MODELS_DIR = pathlib.Path('models')


def get_all_models() -> list[str]:
    return [d.name for d in MODELS_DIR.iterdir() if d.is_dir()]


def main():
    parser = argparse.ArgumentParser(description='voci-studio — Conversão RVC')
    parser.add_argument('--input',      required=True,  help='WAV de entrada')
    parser.add_argument('--model',      default=None,   help='Nome da pasta em models/')
    parser.add_argument('--all-models', action='store_true', help='Testar todos os modelos')
    parser.add_argument('--prefix',     default='',     help='Prefixo do arquivo de saída')
    parser.add_argument('--out',        default=None,   help='Caminho do WAV de saída (single model)')
    parser.add_argument('--pitch',      type=int, default=0, help='Ajuste de pitch em semitons')
    parser.add_argument('--device',     default='cuda:1')
    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    if not input_path.exists():
        print(f'[ERRO] Arquivo não encontrado: {input_path}')
        sys.exit(1)

    from core.converter import VoiceConverter, find_model_files
    print('Carregando VoiceConverter...')
    vc = VoiceConverter()
    print('OK\n')

    models_to_run = get_all_models() if args.all_models else [args.model]

    output_dir = pathlib.Path('output')
    output_dir.mkdir(exist_ok=True)

    results = []
    for model_name in models_to_run:
        if not model_name:
            print('[ERRO] Informe --model ou use --all-models')
            sys.exit(1)

        try:
            pth, idx = find_model_files(MODELS_DIR, model_name)
        except FileNotFoundError as e:
            print(f'[{model_name}] ERRO: {e}')
            results.append((model_name, 'MODELO NÃO ENCONTRADO'))
            continue

        if args.out and not args.all_models:
            out_path = pathlib.Path(args.out)
        else:
            take_stem = input_path.stem
            out_path = output_dir / f'{args.prefix}{model_name}_{take_stem}.wav'

        print(f'[{model_name}]')
        print(f'  PTH:   {pth.name}')
        print(f'  INDEX: {idx.name if idx else "(nenhum)"}')
        print(f'  OUT:   {out_path}')

        ok = vc.convert(
            input_path=input_path,
            output_path=out_path,
            model_pth=pth,
            model_index=idx,
            pitch=args.pitch,
            device=args.device,
        )
        status = f'OK ({out_path.stat().st_size // 1024}KB)' if ok else 'FALHOU'
        print(f'  {status}\n')
        results.append((model_name, status))

    if len(results) > 1:
        print('─' * 40)
        print('RESUMO:')
        for name, status in results:
            print(f'  {name:20s} → {status}')


if __name__ == '__main__':
    main()
