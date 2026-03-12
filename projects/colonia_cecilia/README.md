# Colônia Cecília — Exemplo de Projeto

Recreação sonora do grito anarquista da [Colônia Cecília](https://pt.wikipedia.org/wiki/Col%C3%B4nia_Cec%C3%ADlia),
comunidade libertária fundada por imigrantes italianos no Paraná em 1890.

## Áudio produzido

**"Viva l'Anarchia"** — grito solo seguido de coro em cascata.

```
[0.0s – ~2s]  Solo: voz italiana masculina (De André) — "Viva l'Anarchia!"
[~2s  – 2.5s] Pausa dramática
[2.5s – fim]  Coro em cascata: De André · Celentano · Tenco ·
              Battiato · Morandi · Blanco — "VIVA"
```

## Modelos usados

| Modelo | Papel | Timbre |
|---|---|---|
| Fabrizio De André | Solo + coro | Grave, dramático, político |
| Adriano Celentano | Coro | Potente, icônico |
| Luigi Tenco | Coro | Barítono intenso |
| Franco Battiato | Coro | Texturizado, marcante |
| Gianni Morandi | Coro | Leve, pop italiano |
| Blanco | Coro | Jovem, rasgado |

## Como reproduzir

```bash
# 1. Converter solo e vozes da multidão (modelos RVC necessários em models/)
python scripts/convert.py --input input/take_06.wav --model DeAndre --out output/solo_deandre.wav
python scripts/convert.py --input input/take_09.wav --all-models --prefix crowd_

# 2. Compor áudio final
python scripts/mix.py --project projects/colonia_cecilia/config.yaml
```

Output: `output/viva_anarchia_FINAL.wav`
