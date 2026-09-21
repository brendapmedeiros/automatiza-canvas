# Automacao Academica: Canvas LMS -> NotebookLM & Google Calendar

Criei essa automacao em Python para resolver dois problemas da minha rotina na faculdade:

1. **Estudar com IA sem retrabalho manual:** Extrair todo o conteudo das aulas e apostilas do Canvas em Markdown limpo para subir direto no Google NotebookLM (Gemini) e ter um tutor que realmente conhece a materia.
2. **Nao perder prazos:** Puxar automaticamente as entregas e questionarios do Canvas e cruzar com os meus blocos de trabalho e foco academico no Google Calendar.

---

## Desafio Tecnico:

No inicio, extraindo o HTML das paginas pela API do Canvas, os arquivos gerados ficavam praticamente vazios apenas com o titulo e o link, porque o texto da apostila não ficava no no corpo da pagina do Canvas. Ela embute uma plataforma externa via <iframe>. Como o NotebookLM nao faz login na faculdade, subir apenas o link do Canvas nao servia para nada.

### Como resolvi:
- Inspecionei as chamadas de rede do player da plataforma e apontei para oo endpoint publico da API
- Implementei um parser em Python que lê a arvore JSON dos materiais, extrai tópicos, seções, quadros, tabelas e blocos de codigo formatados.
- Integrei essa extracao na pipeline principal. O resultado foi a geracao de 53 arquivos markdown com mais de 700 KB de conteudo estruturado.

---

## Como executar

### 1. Clonar e instalar dependências

```powershell
git clone https://github.com/brendapmedeiros/automatiza-canvas.git
cd canvas-academic-automation

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configurar as variáveis

Copie o `.env.example` para `.env` e preencha suas credenciais:

```ini
CANVAS_API_URL=https://unifeso.instructure.com
CANVAS_API_TOKEN=seu_token_gerado_no_canvas
CALENDAR_ID=primary
```

### 3. Executar

- **Rodar tudo (conteúdo para o NotebookLM + agenda ics):**
  ```powershell
  python app.py
  ```

- **Apenas extrair o conteudo das aulas:**
  ```powershell
  python app.py --extract-only
  ```

- **Apenas gerar a agenda:**
  ```powershell
  python app.py --calendar-only
  ```

- **Testar conexao com o Canvas:**
  ```powershell
  python app.py --dry-run
  ```

---

## Como Usar as Saidas

### No NotebookLM
1. Acesse `notebooklm.google.com` e crie um caderno.
2. Em **Adicionar fontes**, faca upload dos arquivos `.md` gerados na pasta `estudos_canvas/[Disciplina]/`.
3. Pronto. A IA vai ter acesso ao texto integral das aulas, teorias e códigos para responder suas dúvidas.

### No Google Calendar
1. O script gera o arquivo `agenda_academica.ics` na raiz do projeto.
2. No Google Calendar Web, Configuracoes > Importar e exportar
3. Selecione o arquivo `.ics` e importe na sua agenda.
4. Ele adiciona a rotina de expediente (09:00-18:00), intervalo (18:00-19:00), foco academico (19:00-20:15), bloco de MVP no sabado (10:00-12:00) e os prazos avaliativos do Canvas.

---

## Estrutura do Projeto

```text
.
├── .env.example
├── requirements.txt
├── README.md
├── app.py                   # Atalho de execucao
├── main.py                  # Ponto de entrada CLI
├── src/
│   ├── config.py            # Configuracoes, disciplinas e horarios
│   ├── canvas_client.py     # Integracao com a API do Canvas LMS
│   ├── content_extractor.py # Extracao dos modulos e scraping Liviu
│   ├── calendar_sync.py     # Coleta de tarefas e gerador .ics
│   └── utils.py             # Parser Liviu, conversor Markdown e limpeza de arquivos
└── estudos_canvas/          # Saida dos Markdowns organizada por disciplina
```
