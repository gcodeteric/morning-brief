# SimulaNewsMachine — Guia de Instalação

## O que é

Sistema automático que todas as manhãs te entrega um ficheiro no Desktop com as 15 notícias mais importantes de sim racing, motorsport, hardware, racing games e simuladores, prontas a transformar em posts para redes sociais.

**O que faz:**
- Inclui 57 feeds RSS prontos a usar + suporte para ~22 canais YouTube adicionais (correr channel_id_extractor.py para activar)
- Filtra, pontua e seleciona as 15 notícias mais relevantes
- Gera um ficheiro `SIMULA_BRIEF_HOJE.md` no teu Desktop
- Gera 6 blocos operacionais para redes sociais no brief final
- Instagram funciona como 2 carrosséis editoriais por dia: manhã (sim racing / nostalgia / racing games / PT) e tarde (motorsport)
- Se os agentes MiniMax estiverem configurados, acrescenta packs estruturados, prompt de imagem, script de voz e QA ao brief
- Pode enviar um email digest mobile-friendly com a seleção final resolvida

---

## Instalação (10 minutos)

### 1. Instalar Python

- Ir a **python.org/downloads**
- Fazer download de **Python 3.11 ou superior**
- **IMPORTANTE:** Marcar ✅ **"Add Python to PATH"** durante a instalação
- Clicar "Install Now"

### 2. Abrir o terminal na pasta do projeto

Abre o **Explorador de Ficheiros**, navega até à pasta do projeto, clica na **barra de endereço** (onde aparece o caminho), escreve **cmd** e carrega **Enter**.

Isto abre o terminal já na pasta certa.

### 3. Instalar dependências

```
pip install -r requirements.txt
```

Deves ver mensagens a dizer "Successfully installed...". Se der erro, tenta:
```
python -m pip install -r requirements.txt
```

### 4. Extrair YouTube Channel IDs (só uma vez)

```
python channel_id_extractor.py
```

Isto vai buscar os IDs dos canais YouTube. Demora ~1 minuto. Vais ver OK ou FALHOU para cada canal.

### 5. Testar que os feeds funcionam (só uma vez)

```
python feed_validator.py
```

Isto testa todos os feeds. É normal alguns falharem — o sistema funciona na mesma sem eles.

### 6. Testar o sistema

```
python main.py
```

Deves ver mensagens como:
```
=== SimulaNewsMachine v2.2 iniciada ===
Passo 1: Scanning feeds...
Passo 2: Curating...
Passo 3: Planning...
Passo 3.5: Instagram digest pipeline...
Passo 4: Formatting...
=== Concluido com sucesso ===
```

### 7. Verificar resultado

Abrir o ficheiro **SIMULA_BRIEF_HOJE.md** no Desktop. Podes abrir com qualquer editor de texto (Notepad, VS Code, etc.)

### 8. Agendar para correr automaticamente

**Duplo-clique** no ficheiro `setup_scheduler.bat`

Se pedir permissão de administrador, clicar "Sim".

---

## Uso Diário

1. ☀️ Acordar
2. 📄 Abrir **SIMULA_BRIEF_HOJE.md** no Desktop
3. 🎛️ Rever os blocos editoriais: Instagram manhã, Instagram tarde, X, YouTube, Reddit e Discord
4. 🧠 Se os agentes estiverem activos, usar os packs gerados, o prompt de imagem e o script de voz já renderizados no brief
5. 📬 Se o email digest estiver activo, podes trabalhar directamente a partir do email no telemóvel
6. ✅ **15 minutos. Feito.**

---

## Modelo de conteúdo actual

O sistema continua a gerar um brief diário, mas o modelo actual do Instagram já não é:

- 1 notícia = 1 post

Agora é:

- **Morning Digest Carousel**
  - sim_racing
  - nostalgia
  - racing_games
  - histórias PT / Portugal-related quando existirem
- **Afternoon Digest Carousel**
  - motorsport

Tamanho ideal:

- **5 a 7 histórias por carrossel**

O objectivo é editorial:

- um fio condutor por carrossel
- uma história por slide
- caption que resume o conjunto
- pergunta final à comunidade

---

## Fluxo actual de execução

Execução real do pipeline:

1. **Step 1: Scanning**
2. **Step 2: Curating**
3. **Step 3: Planning**
4. **Step 3.5: Instagram digest pipeline** (opcional, se houver agentes configurados)
5. **Step 4: Formatting**
6. **Entrega opcional**:
   - email digest
   - social cards

Se qualquer etapa opcional falhar, o brief continua a ser gerado normalmente.

---

## Se algo correr mal

| Problema | Solução |
|----------|---------|
| O ficheiro não aparece no Desktop | Abrir cmd na pasta do projeto, correr `python main.py` |
| Erro "Python not found" | Reinstalar Python com "Add to PATH" marcado |
| Alguns feeds falharam | Normal! O sistema continua com os outros |
| Quero ver que feeds falharam | Correr `python feed_validator.py` |
| Quero ver os logs | Abrir pasta `logs\` dentro do projeto |
| Quero re-testar tudo | Correr `python main.py` |
| Quero ver o resumo da última execução | Abrir `data\run_summary.json` dentro do projeto |

---

## Estrutura de Pastas

```
morning-brief\
├── main.py                  ← Script principal
├── config.py                ← Configurações
├── scanner.py               ← Lê os feeds RSS
├── curator.py               ← Filtra e pontua artigos
├── formatter.py             ← Gera o ficheiro .md
├── feeds.py                 ← Lista de todos os feeds
├── channel_id_extractor.py  ← Extrai IDs do YouTube
├── feed_validator.py        ← Testa se os feeds funcionam
├── requirements.txt         ← Dependências Python
├── setup_scheduler.bat      ← Agenda execução diária
├── data\                    ← Dados internos
│   ├── seen_links.json      ← Links já mostrados (evita repetir)
│   ├── run_summary.json     ← Resumo da última execução
│   └── extracted_channel_ids.json  ← IDs YouTube (gerado após correr channel_id_extractor.py)
├── logs\                    ← Logs diários
└── archive\                 ← Arquivo de briefs anteriores
```

## Assets necessários para social cards

Pasta `assets/` já criada. Colocar antes de activar `GENERATE_IMAGES = True`:

| Ficheiro                  | Obrigatório | Uso                              |
|---------------------------|-------------|----------------------------------|
| logo-watermark.png        | ✅ Sim      | Watermark nos cards (PNG alpha)  |
| BarlowCondensed-Bold.ttf  | ✅ Sim      | Fonte headlines                  |
| Barlow-Regular.ttf        | ✅ Sim      | Fonte texto secundário           |

Os logos do projecto (logo-primary.png, etc.) estão em assets/ mas
não são necessários para os cards desta fase — apenas logo-watermark.png.

Fontes gratuitas: https://fonts.google.com/specimen/Barlow+Condensed

Quando pronto:
1. Colocar os 3 ficheiros obrigatórios em assets/
2. Definir GENERATE_IMAGES = True em config.py
3. pip install Pillow

Notas:
- o suporte actual a digests no `card_generator.py` é **mínimo e seguro**
- o cover pode reutilizar `cover_hook` e `notes_for_design` quando existirem
- não há redesign completo de carrosséis neste patch; se faltar pack, o sistema cai para fallback seguro

## Overrides manuais por canal

Podes forçar o sistema a usar alternativas diferentes criando:

`data/manual_overrides.json`

Formato:

- `0` = escolha principal
- `1` = alternativa 1
- `2` = alternativa 2

Exemplo:

```json
{
  "instagram_morning_digest": 0,
  "instagram_afternoon_digest": 1,
  "youtube_daily": 2
}
```

Se o ficheiro não existir, o sistema usa automaticamente as escolhas principais do planner.

Instagram:
- `instagram_morning_digest` controla o carrossel editorial da manhã
- `instagram_afternoon_digest` controla o carrossel editorial da tarde
- cada digest usa `0` principal, `1` alternativa 1, `2` alternativa 2
- estrutura atual: 5 a 7 histórias por carrossel

Também existe o ficheiro:

`abrir_overrides_json.bat`

Ao fazer duplo clique:
- cria o `manual_overrides.json` se ainda não existir
- abre o JSON para edição rápida no Windows

Compatibilidade:
- os overrides antigos continuam suportados quando fizer sentido
- o formato recomendado para Instagram é agora por digest, não por notícia individual

## Envio automático por email

O sistema pode enviar automaticamente o content pack diário por email após gerar o brief.

Configurar no `config.py`:

- `SEND_EMAIL_DIGEST = True`
- `EMAIL_SMTP_HOST`
- `EMAIL_SMTP_PORT`
- `EMAIL_SMTP_USER`
- `EMAIL_SMTP_PASSWORD`
- `EMAIL_FROM`
- `EMAIL_TO`

Opções:

- `EMAIL_ATTACH_MARKDOWN = True` → anexa o `.md`
- `EMAIL_ATTACH_CARDS = True` → anexa os social cards gerados

Recomendação:
usar SMTP do Gmail, Outlook ou outro fornecedor equivalente.

Se o envio falhar, o brief continua a ser gerado normalmente.

O email usa a **seleção final já resolvida** pelo planner + manual overrides.

Quando configurado, envia:
- corpo texto simples mobile-friendly
- corpo HTML mobile-friendly
- anexo do `.md` final
- social cards, se existirem e estiverem activados

## Onde vivem os prompts

- **Instagram digest packs e prompts editoriais estruturados**:
  - definidos em `agents.py`
  - renderizados no brief por `formatter.py`
- **Prompts X / YouTube / Reddit / Discord**:
  - renderizados no `formatter.py`
- **Prompt de imagem**:
  - gerado pelo agente `image_director` em `agents.py`
- **Script de voz**:
  - gerado pelo agente `voice_director` em `agents.py`
- **QA editorial**:
  - gerado em `agents.py`
  - mostrado no brief e reutilizado onde aplicável

Se os agentes falharem ou não estiverem configurados:
- o brief continua a ser gerado
- os digests de Instagram continuam com fallback seguro baseado no planner

## How to validate today's run

1. correr `python main.py --dry-run`
2. confirmar que o run chega a `=== Concluido com sucesso ===`
3. confirmar que existem **Instagram — Morning Digest** e **Instagram — Afternoon Digest**
4. se os agentes estiverem configurados, confirmar que aparecem:
   - digest packs
   - prompt de imagem
   - script de voz
5. se usares overrides, confirmar que `manual_overrides.json` foi aplicado no brief/log

## Internal Dashboard

Existe um dashboard interno opcional para operações diárias de conteúdo.

Lançar com:

```bash
streamlit run dashboard_app.py
```

O dashboard serve para:
- inspecionar o latest run
- navegar stories curadas com links directos
- controlar Morning/AFternoon Instagram digests
- rever prompts, image prompts, voice scripts, QA, cards e brief
- editar e guardar overrides

O dashboard usa o latest-run snapshot quando ele existe:
- `data/dashboard_latest_snapshot.json`

Se o snapshot não existir, cai em fallback gracioso com base no:
- brief
- `run_summary.json`
- overrides
- cards disponíveis

Não substitui o pipeline CLI.
É uma camada operacional por cima do sistema actual.
