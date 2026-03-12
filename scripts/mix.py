"""
scripts/mix.py — CLI de composição final a partir de um config de projeto.

Uso:
    python scripts/mix.py --project projects/colonia_cecilia/config.yaml
    python scripts/mix.py --project projects/colonia_cecilia/config.yaml --dry-run
"""

import argparse
import sys
import pathlib

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from core.mixer import process_solo, process_crowd_voice, compose


def load_config(path: pathlib.Path) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description='voci-studio — Composição final')
    parser.add_argument('--project', required=True, help='Caminho para config.yaml do projeto')
    parser.add_argument('--dry-run', action='store_true', help='Mostrar plano sem processar')
    args = parser.parse_args()

    cfg_path = pathlib.Path(args.project)
    if not cfg_path.exists():
        print(f'[ERRO] Config não encontrado: {cfg_path}')
        sys.exit(1)

    cfg = load_config(cfg_path)
    output_dir = pathlib.Path('output')
    output_dir.mkdir(exist_ok=True)

    mixing  = cfg['mixing']
    solo_cfg  = cfg['solo']
    crowd_cfg = cfg['crowd']

    solo_wav  = output_dir / solo_cfg['converted_wav']
    out_final = output_dir / cfg.get('output_file', 'final.wav')

    print(f'Projeto: {cfg["project"]}')
    print(f'  Solo:   {solo_wav.name}')
    print(f'  Vozes:  {len(crowd_cfg["voices"])} cantores')
    print(f'  Pausa:  {mixing["pause_ms"]}ms')
    print(f'  Stagger:{mixing["stagger_ms"]}ms')
    print(f'  Output: {out_final.name}')

    if args.dry_run:
        print('\n[dry-run] Nenhum arquivo gerado.')
        return

    # ── Solo ─────────────────────────────────────────────────────
    print('\n[1/3] Processando solo...')
    solo_seg = process_solo(
        wav_path=solo_wav,
        reverb=mixing['solo_reverb'],
        output_sr=mixing['output_sr'],
    )
    print(f'  {len(solo_seg)/1000:.2f}s')

    # ── Multidão ─────────────────────────────────────────────────
    print(f'\n[2/3] Carregando {len(crowd_cfg["voices"])} vozes...')
    crowd_segs = []
    for v in crowd_cfg['voices']:
        wav = output_dir / v['converted_wav']
        print(f'  {v["model"]:15s} pitch={v["pitch_fine"]:+.1f}st  wet={v["reverb_wet"]:.2f}')
        seg = process_crowd_voice(
            wav_path=wav,
            pitch_fine=v['pitch_fine'],
            reverb_wet=v['reverb_wet'],
            crowd_room=mixing['crowd_reverb']['room_size'],
            crowd_damp=mixing['crowd_reverb']['damping'],
            output_sr=mixing['output_sr'],
        )
        crowd_segs.append(seg)

    # ── Composição ───────────────────────────────────────────────
    print('\n[3/3] Montando composição...')
    final = compose(
        solo_seg=solo_seg,
        crowd_segs=crowd_segs,
        pause_ms=mixing['pause_ms'],
        stagger_ms=mixing['stagger_ms'],
        output_sr=mixing['output_sr'],
    )
    final.export(str(out_final), format='wav')

    print(f'\n{"─"*50}')
    print(f'CONCLUÍDO → {out_final}')
    print(f'Duração:    {len(final)/1000:.2f}s')


if __name__ == '__main__':
    main()
