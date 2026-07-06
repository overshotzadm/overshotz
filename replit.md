# OverShotz Landing Page — A/B Test

Reconstrução 100% fiel de overshotz.com.br/lp1/ como site estático no Replit, com estrutura A/B.

## Versões

| URL   | Versão | Seção de oferta |
|-------|--------|-----------------|
| `/`   | V2     | Nova (cards interativos + imagem dinâmica) |
| `/v1` | V1     | Original (Elementor, layout antigo) |
| `/v2` | V2     | Nova (cards interativos + imagem dinâmica) |

## Estrutura de arquivos

```
v1/index.html          ← V1: oferta original (backup pré-reestruturação)
v2/index.html          ← V2: oferta nova (versão atual)
index.html             ← alias/referência (legado)
overshotz.com.br/      ← assets estáticos compartilhados (141 arquivos, 6.5MB)
server.py              ← servidor HTTP com roteamento A/B
```

## Rodando

O workflow "Start application" inicia o servidor na porta 5000.

```
python3 server.py
```

## Regras A/B

- Quando citar **"Alterar V1"** → editar `v1/index.html`
- Quando citar **"Alterar V2"** → editar `v2/index.html`
- Quando citar **"Preview V1"** → abrir `/v1`
- Quando citar **"Preview V2"** → abrir `/v2`
- Assets em `overshotz.com.br/` são **compartilhados** entre as duas versões

## Estrutura de assets locais

```
overshotz.com.br/
├── cdn-cgi/scripts/         # Cloudflare email-decode
├── wp-content/
│   ├── cache/min/1/         # CSS minificados pelo WP Rocket
│   ├── plugins/
│   │   ├── elementor/       # CSS/JS Elementor 4.0.6
│   │   └── elementor-pro/   # CSS/JS Elementor Pro 3.33.2
│   └── uploads/
│       ├── elementor/css/   # CSS gerado pelo Elementor
│       ├── 2025/09/         # Fontes: BunkenTechSansPro, ColdWarm
│       ├── 2025/11-12/      # Imagens de produto e seções
│       └── 2026/02-04/      # Imagens de depoimentos e hero mobile
└── wp-includes/js/          # jQuery 3.7.1 + Migrate 3.4.1
```

## Tecnologias preservadas

- HTML renderizado do WordPress/Elementor Pro, convertido para estático
- Elementor 4.0.6 + Elementor Pro 3.33.2 (JS frontend completo)
- Swiper.js v8 (carrosseis de depoimentos, steps e vídeos YouTube)
- Fontes custom: BunkenTechSansPro (Bold, Book, LightIt) + ColdWarm
- VTurb player (vídeos de VSL)
- Animações CSS: fadeIn, fadeInUp, fadeInLeft, fadeInRight
- Animação neon SVG no logo
- Carrossel infinito de palavras (Energia, Foco, Performance, Treino)
- FAQ accordion interativo
- V2: seção de oferta com cards interativos, imagem dinâmica e badge de desconto

## Cache (server.py)

- CSS/JS/fontes: `max-age=31536000, immutable` (1 ano)
- Imagens: `max-age=86400` (1 dia)
- HTML: `no-cache`

## User preferences

- Preservar fidelidade visual ao original (HTML do site ao vivo como fonte de verdade)
- Sem WordPress/Elementor como dependência de servidor
- Tudo rodando localmente no Replit
- Zero dependências externas de runtime
- V1 = seção de oferta original; V2 = nova seção de oferta
- Alterações em V1 e V2 são sempre independentes
