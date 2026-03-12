#!/bin/bash
# setup/install.sh — Instala Applio + dependências do voci-studio no servidor
# Testado em Ubuntu 22.04, CUDA 12.2, Python 3.10

set -e
BASE=/opt/cogep-lab/data/RVC
LOG=$BASE/install.log

echo "=== voci-studio setup ===" | tee $LOG

# 1. Dependências do sistema
echo "[1/4] Dependências do sistema..." | tee -a $LOG
sudo apt-get update -q
sudo apt-get install -y python3.10-venv ffmpeg git | tee -a $LOG

# 2. Clonar Applio
echo "[2/4] Clonando Applio..." | tee -a $LOG
mkdir -p $BASE
if [ ! -d "$BASE/Applio" ]; then
    git clone --depth=1 https://github.com/IAHispano/Applio.git $BASE/Applio
else
    echo "  Applio já existe, pulando clone."
fi

# 3. Criar venv e instalar PyTorch cu121
echo "[3/4] Criando venv e instalando PyTorch cu121..." | tee -a $LOG
python3.10 -m venv $BASE/Applio/env
$BASE/Applio/env/bin/pip install --upgrade pip
$BASE/Applio/env/bin/pip install \
    torch==2.5.1+cu121 torchaudio==2.5.1+cu121 \
    --index-url https://download.pytorch.org/whl/cu121 | tee -a $LOG

# 4. Instalar dependências do Applio e voci-studio
echo "[4/4] Instalando dependências..." | tee -a $LOG
$BASE/Applio/env/bin/pip install -r $BASE/Applio/requirements_cu121.txt | tee -a $LOG

# 5. Baixar modelos base (rmvpe + contentvec)
echo "[5/5] Baixando modelos base RVC..." | tee -a $LOG
ASSETS_BASE="https://huggingface.co/IAHispano/Applio/resolve/main/Resources"
mkdir -p $BASE/Applio/rvc/models/{predictors,embedders/contentvec}

wget -qc "$ASSETS_BASE/predictors/rmvpe.pt" \
    -O $BASE/Applio/rvc/models/predictors/rmvpe.pt
wget -qc "$ASSETS_BASE/predictors/fcpe.pt" \
    -O $BASE/Applio/rvc/models/predictors/fcpe.pt
wget -qc "$ASSETS_BASE/embedders/contentvec/pytorch_model.bin" \
    -O $BASE/Applio/rvc/models/embedders/contentvec/pytorch_model.bin
wget -qc "$ASSETS_BASE/embedders/contentvec/config.json" \
    -O $BASE/Applio/rvc/models/embedders/contentvec/config.json

echo "" | tee -a $LOG
echo "INSTALL_DONE" | tee -a $LOG
echo ""
echo "Setup concluído! Próximos passos:"
echo "  1. Adicione modelos RVC em: $BASE/models/<nome>/"
echo "  2. Coloque gravações em:    $BASE/input/"
echo "  3. Execute: python scripts/test_models.py --input input/meu_audio.wav"
