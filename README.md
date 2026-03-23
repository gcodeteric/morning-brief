# SimulaNewsMachine — Guia de Instalação

## O que é

Sistema automático que todas as manhãs te entrega um ficheiro no Desktop com as 15 notícias mais importantes de sim racing, motorsport, hardware, racing games e simuladores, prontas a transformar em posts para redes sociais.

**O que faz:**
- Lê ~90 feeds RSS (sites + canais YouTube) todas as noites às 05:00
- Filtra, pontua e seleciona as 15 notícias mais relevantes
- Gera um ficheiro `SIMULA_BRIEF_HOJE.md` no teu Desktop
- Inclui 5 prompts prontos para copiar/colar no Claude e criar posts

---

## Instalação (10 minutos)

### 1. Instalar Python

- Ir a **python.org/downloads**
- Fazer download de **Python 3.11 ou superior**
- **IMPORTANTE:** Marcar ✅ **"Add Python to PATH"** durante a instalação
- Clicar "Install Now"

### 2. Abrir o terminal

- Carregar a tecla **Windows** no teclado
- Escrever **cmd** e pressionar **Enter**

### 3. Ir para a pasta do projeto

```
cd C:\Users\berna\SimulaNewsMachine
```

### 4. Instalar dependências

```
pip install -r requirements.txt
```

Deves ver mensagens a dizer "Successfully installed...". Se der erro, tenta:
```
python -m pip install -r requirements.txt
```

### 5. Extrair YouTube Channel IDs (só uma vez)

```
python channel_id_extractor.py
```

Isto vai buscar os IDs dos canais YouTube. Demora ~1 minuto. Vais ver OK ou FALHOU para cada canal.

### 6. Testar que os feeds funcionam (só uma vez)

```
python feed_validator.py
```

Isto testa todos os feeds. É normal alguns falharem — o sistema funciona na mesma sem eles.

### 7. Testar o sistema

```
python main.py
```

Deves ver mensagens como:
```
=== SimulaNewsMachine v2.1 iniciada ===
Passo 1: Scanning feeds...
Passo 2: Curating...
Passo 3: Formatting...
=== Concluído com sucesso ===
```

### 8. Verificar resultado

Abrir o ficheiro **SIMULA_BRIEF_HOJE.md** no Desktop. Podes abrir com qualquer editor de texto (Notepad, VS Code, etc.)

### 9. Agendar para correr automaticamente

**Duplo-clique** no ficheiro `setup_scheduler.bat`

Se pedir permissão de administrador, clicar "Sim".

---

## Uso Diário

1. ☀️ Acordar
2. 📄 Abrir **SIMULA_BRIEF_HOJE.md** no Desktop
3. 📋 Copiar cada prompt → colar no Claude → publicar
4. ✅ **15 minutos. Feito.**

---

## Se algo correr mal

| Problema | Solução |
|----------|---------|
| O ficheiro não aparece no Desktop | Abrir cmd, ir à pasta, correr `python main.py` |
| Erro "Python not found" | Reinstalar Python com "Add to PATH" marcado |
| Alguns feeds falharam | Normal! O sistema continua com os outros |
| Quero ver que feeds falharam | Correr `python feed_validator.py` |
| Quero ver os logs | Abrir pasta `SimulaNewsMachine\logs\` |
| Quero re-testar tudo | Correr `python main.py` |
| Quero ver o resumo da última execução | Abrir `SimulaNewsMachine\data\run_summary.json` |

---

## Estrutura de Pastas

```
SimulaNewsMachine\
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
│   └── extracted_channel_ids.json  ← IDs YouTube extraídos
├── logs\                    ← Logs diários
└── archive\                 ← Arquivo de briefs anteriores
```
