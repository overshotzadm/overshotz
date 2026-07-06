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

## Deploy — GitHub + Hostinger (CI/CD)

- Hostinger hPanel → **Avançado → GIT**: conecta o repo público e faz deploy no diretório escolhido (ex.: `public_html/lp1`)
- Webhook do GitHub dispara auto-deploy a cada commit no `main`
- Site roda 100% estático no Apache: o `.htaccess` faz o roteamento A/B (`/` → v2, `/v1` → v1, `/v2` → v2) e mapeia `v1|v2/assets/` para a pasta compartilhada `assets/`
- CSS é inline no HTML; JS referenciado por nome exato de arquivo — sem dependência do `server.py` em produção

## Deploy alternativo — Railway

- Repositório: `https://github.com/overshotzadm/overshotz-lp` (branch `main`)
- Token: secret `GITHUB_PERSONAL_ACCESS_TOKEN`
- **Push via API do GitHub** (git CLI é bloqueado pela sandbox do Replit):
  - Push completo: `python3 github_push.py blobs` → `python3 github_push.py commit`
  - Push incremental (arquivos específicos): `python3 github_push.py files <arq1> <arq2> ...`
- Railway monitora o branch `main` → todo commit dispara redeploy automático
- Config Railway: `railway.json` (start: `python3 server.py`) + `Procfile`
- `server.py` usa `PORT` do ambiente (Railway injeta automaticamente)
- ZIPs, `github_push.py` e pastas do Replit ficam fora do repo (`.gitignore`)
- **Regra:** ao criar arquivo novo na raiz, adicionar em `INCLUDE_PATHS` no `github_push.py` OU enviar via `python3 github_push.py files <arquivo>` (o push completo só cobre a allowlist + `assets/`)

## Rastreamento (obrigatório em TODAS as versões)

- **Meta Pixel ID `1002705989178676`** instalado no `<head>` (antes de `</head>`) de **todas** as páginas: `index.html`, `v1/index.html`, `v2/index.html`
- **Regra:** ao criar qualquer versão nova (v3, v4, ...), copiar o bloco `<!-- Meta Pixel Code -->` existente para o `<head>` da nova página antes de publicar
- O bloco inclui: script `fbq('init', ...)` + `fbq('track', 'PageView', {}, {eventID})` + beacon pro `/capi` + tag `<noscript>`
- Verificação rápida: `grep -c "fbq('init'" <arquivo>` deve retornar 1

### API de Conversões (CAPI) — server.py

- Endpoint `POST /capi`: navegador envia `event_id` gerado por pageview; servidor repassa ao Meta (`graph.facebook.com`) com IP, user-agent e cookies `_fbp`/`_fbc` — deduplicação via `eventID` idêntico nos dois canais
- Token: secret `META_PIXEL_ACCESS_TOKEN` (Replit) — **precisa também ser adicionado como variável no Railway** para funcionar em produção; sem o token o servidor ignora o envio silenciosamente
- Proteções: allowlist de origem (`overshotz.com.br`, `*.up.railway.app`, `*.replit.dev`, localhost), só evento `PageView`, rate limit 20/min por IP, máx. 16 envios simultâneos
- Log de sucesso no servidor: `[CAPI] PageView enviado (events_received=1)`

## User preferences

- Preservar fidelidade visual ao original (HTML do site ao vivo como fonte de verdade)
- Sem WordPress/Elementor como dependência de servidor
- Tudo rodando localmente no Replit
- Zero dependências externas de runtime
- V1 = seção de oferta original; V2 = nova seção de oferta
- Alterações em V1 e V2 são sempre independentes

## Staging workspace (preview de atualizações sem afetar o site ativo)

```
staging/
  index.html          ← cópia editável da V2 para testes
  assets/             ← link/cópia dos assets (compartilhados)
staging_server.py     ← servidor de preview na porta 5001
```

**Como usar:**
1. Edite `staging/index.html` (ou adicione arquivos em `staging/`)
2. No Shell: `python3 staging_server.py`
3. O preview abre em `http://localhost:5001`
4. Quando aprovar: copie as alterações pra `v1/index.html` ou `v2/index.html` e envie via `python3 github_push.py files ...`
