# voci-studio

Framework de produção de áudio com conversão de voz (RVC) e composição multi-voz.
Pensado para criar recreações sonoras históricas, cenas dramáticas e coros sintéticos
com qualidade de estúdio — custo zero, rodando inteiramente em hardware local.

```
Sua gravação (qualquer voz)
        ↓
   RVC Inference          ←── modelo de voz (.pth + .index)
        ↓
  Voz convertida
        ↓
  Composição final   ←── N vozes em cascata + reverb + timing
        ↓
   WAV 44100Hz
```

---

## Capacidades

### 🎙️ Conversão de Voz (RVC)
- Transforma qualquer gravação de voz para o timbre de um modelo treinado
- Preserva emoção, entonação e intensidade da performance original
- Suporta ajuste de pitch, index rate e método de F0 (rmvpe, harvest, crepe)
- Wrapper limpo sobre o [Applio](https://github.com/IAHispano/Applio)

### 🎭 Multidão / Coro Sintético
- Gera N vozes distintas a partir de modelos diferentes ou do mesmo modelo com variações
- Cascata temporal configurável (stagger) — simula vozes chegando em ondas
- Micro pitch-shift por voz — evita cancelamento de fase, soa mais humano
- Reverb ambiental individual por voz

### 🎛️ Composição Config-Driven
- Cada projeto tem um `config.yaml` com todos os parâmetros de mixing
- Timing, reverb, stagger, pitch, modelos — tudo editável sem tocar no código
- Pipeline completo em dois comandos: `convert` + `mix`

### ⚡ Produção Local / Zero Custo
- Não depende de APIs externas ou serviços pagos
- Otimizado para rodar em servidor com GPU NVIDIA (CUDA 12.x)
- Gerenciamento de GPU inteligente (CUDA_VISIBLE_DEVICES)

---

## Estrutura

```
voci-studio/
├── core/
│   ├── converter.py     # Wrapper RVC — converte voz com qualquer modelo
│   ├── mixer.py         # Motor de composição — solo + cascata de vozes
│   └── utils.py         # Utilitários de áudio (load, normalize, reverb)
│
├── scripts/
│   ├── convert.py       # CLI: converter um take com um ou todos os modelos
│   ├── mix.py           # CLI: compor áudio final a partir de config.yaml
│   └── test_models.py   # CLI: testar todos os modelos num take (comparativo)
│
├── projects/
│   └── colonia_cecilia/ # Exemplo: recreação sonora histórica (1890)
│       ├── config.yaml
│       └── README.md
│
├── setup/
│   ├── install.sh       # Instala Applio + dependências no servidor
│   └── start_webui.sh   # Inicia Applio WebUI (porta 7897)
│
├── models/              # Modelos RVC (.pth + .index) — não versionados
├── input/               # Gravações brutas — não versionadas
└── output/              # Resultados — não versionados
```

---

## Início Rápido

### 1. Setup do Servidor

```bash
# Clonar e instalar (Ubuntu + GPU NVIDIA)
git clone https://github.com/Rlealbarili/voci-studio
cd voci-studio
bash setup/install.sh
```

### 2. Adicionar Modelo de Voz

Baixe um modelo RVC (`.pth` + `.index`) e coloque em:
```
models/<nome-do-modelo>/
├── model.pth
└── model.index
```

Fontes: [Hugging Face](https://huggingface.co/models?search=rvc) · [voice-models.com](https://voice-models.com)

### 3. Gravar e Converter

```bash
# Testar todos os modelos num take para escolher o melhor
CUDA_VISIBLE_DEVICES=1 python scripts/test_models.py --input input/meu_audio.wav

# Converter com o modelo escolhido
CUDA_VISIBLE_DEVICES=1 python scripts/convert.py \
    --input input/meu_audio.wav \
    --model NomeDoModelo \
    --out output/voz_convertida.wav
```

### 4. Compor Áudio Final

Crie seu `projects/meu_projeto/config.yaml` (use `projects/colonia_cecilia/config.yaml` como base) e rode:

```bash
CUDA_VISIBLE_DEVICES=1 python scripts/mix.py \
    --project projects/meu_projeto/config.yaml
```

### 5. WebUI Interativa (opcional)

Para ajustar parâmetros visualmente via navegador:

```bash
# No servidor:
bash setup/start_webui.sh

# No seu computador (tunnel SSH):
ssh -L 7897:localhost:7897 usuario@servidor
# Acessar: http://localhost:7897
```

---

## Criando um Novo Projeto

Copie o template e edite:

```bash
cp -r projects/colonia_cecilia projects/meu_novo_projeto
# Editar projects/meu_novo_projeto/config.yaml
```

Parâmetros principais do `config.yaml`:

```yaml
project: nome_do_projeto
output_file: resultado_final.wav

solo:
  converted_wav: meu_solo.wav     # gerado por scripts/convert.py

crowd:
  voices:
    - model: NomeModelo
      converted_wav: crowd_NomeModelo.wav
      pitch_fine: 0.0             # semitons: +/- para diferenciar vozes
      reverb_wet: 0.09            # 0.0–1.0: mais úmido = mais distante

mixing:
  pause_ms:   500                 # pausa entre solo e coro
  stagger_ms: 90                  # delay entre cada voz da cascata
  output_sr:  44100
```

---

## Requisitos

- Python 3.10+
- GPU NVIDIA com CUDA 12.x (mínimo 6GB VRAM)
- Ubuntu 20.04+ (servidor de produção)

---

## Projetos de Exemplo

| Projeto | Descrição | Modelos |
|---|---|---|
| [colonia_cecilia](projects/colonia_cecilia/) | Grito anarquista, Brasil 1890 | De André, Celentano, Tenco, Battiato, Morandi, Blanco |

---

## Licença

MIT — use, modifique e distribua livremente.
