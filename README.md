# Automacao Academica: Canvas LMS -> Gemini Notebook (NotebookLM) & Google Calendar

Solucao de automacao em Python desenvolvida para centralizar a rotina academica, extrair e converter materiais de estudo para bases de conhecimento no NotebookLM (Gemini) e sincronizar prazos e blocos de tempo no Google Calendar.

---

## Visao Geral do Projeto

O sistema resolve dois gargalos operacionais comuns na vida academica:
1. **Dispersao de Conteudo:** Converte o conteudo HTML de modulos e aulas do Canvas LMS em arquivos Markdown limpos e semanticos, alem de baixar PDFs oficiais organizados por disciplina para ingestao direta como fontes no NotebookLM.
2. **Gestao de Tempo e Prazos:** Coleta todas as tarefas e questionarios avaliativos do Canvas e os integra ao Google Calendar (via API OAuth2 e/ou exportacao universal `.ics`), combinando com blocos fixos de trabalho e foco academico.

---

## Disciplinas Monitoradas (Termo Ativo)

O script realiza o mapeamento inteligente das seguintes disciplinas:
- `EADCSTAD05 - Arquitetura e Aplicações para Mobile`
- `EADCSTAD05 - Desenvolvimento de Aplicações Híbridas`
- `EADCSTAD05 - Desenvolvimento de Aplicações Web-Mobile`
- `EADCSTAD05 - Design Thinking e Gestão da Inovação`
- `EADCSTAD05 - MVP Mobile Development`

---

## Estrutura do Repositorio

```text
Organização acadêmica/
│
├── .env.example              # Modelo de configuracao de variaveis de ambiente
├── requirements.txt          # Dependencias do projeto
├── README.md                 # Documentacao e instrucoes de uso
├── main.py                   # Ponto de entrada CLI (execucao completa ou modular)
│
├── src/
│   ├── __init__.py
│   ├── config.py             # Configuracoes de rotina, fuso horario e disciplinas
│   ├── canvas_client.py      # Cliente de conexao com Canvas LMS e paginacao automatica
│   ├── content_extractor.py  # Modulo 1: Extracao HTML -> Markdown e download de PDFs
│   ├── calendar_sync.py      # Modulo 2: Sincronizacao Google Calendar API e gerador .ics
│   └── utils.py              # Limpeza Windows-safe de caminhos, logger e parser Markdown
│
└── estudos_canvas/           # [Gerado automaticamente] Estrutura de materiais
    └── [Nome_Da_Disciplina]/
        ├── Unidade_01_[Titulo].md
        ├── Unidade_02_[Titulo].md
        └── arquivos/
            └── apostila_oficial.pdf
```

---

## Pre-requisitos & Instalacao

### 1. Acessar a Pasta do Projeto
Abra o terminal na pasta do projeto:
```powershell
cd "c:\Users\brend\Desktop\Organização acadêmica"
```

### 2. Criar e Ativar Ambiente Virtual (Recomendado)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Instalar as Dependencias
```powershell
pip install -r requirements.txt
```

---

## Configuracao de Credenciais (.env)

Copie o arquivo `.env.example` para `.env`:
```powershell
Copy-Item .env.example .env
```

Abra o arquivo `.env` e preencha suas chaves:

```ini
# 1. URL base do Canvas da sua faculdade (ex: https://canvas.instructure.com ou o dominio da sua instituicao)
CANVAS_API_URL=https://canvas.instructure.com

# 2. Seu Token de Acesso do Canvas
# Como gerar: Acesse o Canvas > Clique na foto de perfil (Conta) > Configuracoes > Tokens de Acesso Aprovados > + Novo Token de Acesso
CANVAS_API_TOKEN=seu_token_gerado_aqui

# 3. Identificador do Google Calendar
CALENDAR_ID=primary
```

---

## Como Executar

### 1. Diagnostico e Validacao Rapida (`--dry-run`)
Valida as credenciais do Canvas, testa a conectividade e lista todas as disciplinas encontradas sem realizar downloads pesados:
```powershell
python main.py --dry-run
```

### 2. Execucao Completa (Extracao + Calendario)
Executa a extracao completa dos materiais para o NotebookLM e gera a agenda com todos os prazos e rotinas:
```powershell
python main.py
```

### 3. Execucao Modular
Se desejar executar apenas um dos modulos:

- **Apenas extracao de materiais (Markdown + PDFs):**
  ```powershell
  python main.py --extract-only
  ```

- **Apenas sincronizacao de prazos e calendario:**
  ```powershell
  python main.py --calendar-only
  ```

- **Gerar apenas o arquivo de integracao `.ics` (sem solicitar login OAuth do Google):**
  ```powershell
  python main.py --calendar-only --ics-only
  ```

---

## Especificacoes da Rotina e Calendario

O modulo de calendario gera os seguintes blocos e prazos:

| Tipo | Dias | Horario | Descricao |
| :--- | :--- | :--- | :--- |
| **Trabalho** | Segunda a Sexta | `09:00 - 18:00` | Bloco fixo de expediente |
| **Intervalo / Descompressao** | Segunda a Sexta | `18:00 - 19:00` | Descompressao e transicao |
| **Foco Academico** | Segunda a Sexta | `19:00 - 20:15` | Estudo das disciplinas e tarefas |
| **MVP Mobile Development** | Sabado | `10:00 - 12:00` | Bloco dedicado ao MVP Mobile |
| **Domingo Livre** | Domingo | *Sem eventos* | 100% livre de demandas academicas |
| **Avaliacoes U1 a U3** | 03 de Outubro | *Dia inteiro* | Prazo limite das Unidades 1 a 3 |
| **Avaliacoes Finais** | 31 de Outubro | *Dia inteiro* | Avaliacoes presenciais/finais |
| **Tarefas e Questionarios** | Conforme Canvas | *Dia inteiro* | Sincronizados com link e pontuacao |

### Como Importar o Arquivo de Integracao `.ics` no Google Calendar
1. Acesse o Google Calendar Web (calendar.google.com).
2. No canto superior direito, clique no icone de Configuracoes.
3. No menu lateral esquerdo, clique em Importar e exportar.
4. Em Importar, selecione o arquivo `agenda_academica.ics` gerado na pasta do projeto.
5. Selecione a agenda de destino e clique em Importar.

---

## Como Ingerir os Materiais no Gemini Notebook (NotebookLM)

1. Acesse o NotebookLM (notebooklm.google.com).
2. Crie um novo caderno para o termo ou um caderno especifico para cada disciplina (ex: `Notebook: Arquitetura Mobile`).
3. Clique em Adicionar Fontes -> Fazer upload de arquivos.
4. Navegue ate a pasta correspondente em `estudos_canvas/[Nome_Da_Disciplina]/` e selecione todos os arquivos `.md` e os arquivos `.pdf` da pasta `arquivos/`.
5. O NotebookLM indexara instantaneamente todo o conteudo com cabecalhos e metadados semanticos para gerar resumos, flashcards e simulacoes de prova.
