"""
core/converter.py — Wrapper sobre a inferência RVC do Applio.

Responsabilidade única: receber um WAV de entrada + modelo RVC
e devolver um WAV convertido. Agnóstico ao projeto.
"""

import os
import sys
import pathlib
import shutil


# Localização do Applio — configurar via variável de ambiente APPLIO_DIR
# Exemplo: export APPLIO_DIR=/caminho/para/Applio
DEFAULT_APPLIO_DIR = pathlib.Path(
    os.environ.get('APPLIO_DIR', './Applio')
)


class VoiceConverter:
    """
    Encapsula o VoiceConverter do Applio.
    Instanciar uma vez por sessão (carregamento de modelo é caro).
    """

    def __init__(self, applio_dir: pathlib.Path = DEFAULT_APPLIO_DIR):
        self.applio_dir = applio_dir
        self._infer_fn = None
        self._setup()

    def _setup(self):
        """Configura sys.path e importa run_infer_script do Applio."""
        applio_str = str(self.applio_dir)
        if applio_str not in sys.path:
            sys.path.insert(0, applio_str)
        os.chdir(self.applio_dir)

        from core import run_infer_script  # Applio's core.py
        self._infer_fn = run_infer_script

    def convert(
        self,
        input_path: str | pathlib.Path,
        output_path: str | pathlib.Path,
        model_pth: str | pathlib.Path,
        model_index: str | pathlib.Path | None = None,
        pitch: int = 0,
        index_rate: float = 0.75,
        volume_envelope: float = 0.25,
        protect: float = 0.33,
        f0_method: str = 'rmvpe',
        device: str = 'cuda:1',
    ) -> bool:
        """
        Executa conversão RVC.

        Args:
            input_path:    WAV de entrada (sua gravação).
            output_path:   WAV de saída (voz convertida).
            model_pth:     Caminho para o arquivo .pth do modelo.
            model_index:   Caminho para o .index (opcional, melhora timbre).
            pitch:         Ajuste em semitons (0 = sem mudança).
            index_rate:    Influência do timbre do modelo (0.0–1.0).
            volume_envelope: Mix com envelope original (0.0–1.0).
            protect:       Proteção de fonemas sem voz (0.0–0.5).
            f0_method:     Algoritmo de pitch: 'rmvpe' | 'harvest' | 'crepe'.
            device:        Dispositivo CUDA.

        Returns:
            True se conversão bem-sucedida.
        """
        output_path = pathlib.Path(output_path)

        self._infer_fn(
            pitch=pitch,
            index_rate=index_rate,
            volume_envelope=volume_envelope,
            protect=protect,
            f0_method=f0_method,
            input_path=str(input_path),
            output_path=str(output_path),
            pth_path=str(model_pth),
            index_path=str(model_index) if model_index else '',
            split_audio=False,
            f0_autotune=False,
            f0_autotune_strength=1.0,
            proposed_pitch=False,
            proposed_pitch_threshold=155.0,
            clean_audio=False,
            clean_strength=0.7,
            export_format='WAV',
            embedder_model='contentvec',
            post_process=False,
        )

        return output_path.exists() and output_path.stat().st_size > 0


def find_model_files(
    models_dir: pathlib.Path,
    model_name: str,
) -> tuple[pathlib.Path, pathlib.Path | None]:
    """
    Localiza .pth e .index dentro de models_dir/model_name/.

    Returns:
        (pth_path, index_path)  — index_path pode ser None.
    """
    folder = models_dir / model_name
    if not folder.exists():
        raise FileNotFoundError(
            f"Pasta do modelo não encontrada: {folder}\n"
            f"Baixe o modelo e coloque em: {folder}/"
        )

    pths = list(folder.glob('*.pth'))
    idxs = list(folder.glob('*.index'))

    if not pths:
        raise FileNotFoundError(f"Nenhum arquivo .pth em {folder}")

    return pths[0], idxs[0] if idxs else None
