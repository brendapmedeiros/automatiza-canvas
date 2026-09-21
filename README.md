# Automacao Academica: Canvas LMS -> NotebookLM & Google Calendar

Criei essa automacao em Python para resolver dois problemas reais da minha rotina na faculdade (ADS - Termo 5):

1. **Estudar com IA sem retrabalho manual:** Extrair todo o conteudo das aulas e apostilas do Canvas em Markdown limpo para subir direto no Google NotebookLM (Gemini) e ter um tutor que realmente conhece a materia.
2. **Nao perder prazos:** Puxar automaticamente as entregas e questionarios do Canvas e cruzar com os meus blocos de trabalho e foco academico no Google Calendar.

---

## O Desafio Tecnico: O "Markdown Vazio"

No inicio, ao extrair o HTML das paginas pela API do Canvas, os arquivos `.md` gerados ficavam praticamente vazios (apenas com o titulo e o link). 

O motivo: a instituicao (UNIFESO) nao guarda o texto da apostila no corpo da pagina do Canvas. Ela embute uma plataforma externa (**Liviu**) via `<iframe>`. Como o NotebookLM nao faz login na faculdade, subir apenas o link do Canvas nao servia para nada.

### Como resolvi (Engenharia Reversa):
- Inspecionei as chamadas de rede do player da Liviu e localizei o endpoint publico da API: `GET https://api.liviu.com.br/public-link/{uuid}`.
- Escrevi um parser recursivo em Python que le a arvore JSON do material, extrai topicos, secoes, quadros conceituais, tabelas e blocos de codigo formatados.
- Integrei essa extracao no pipeline principal. O resultado foi a geracao de **53 arquivos Markdown** totalizando mais de **700 KB** de conteudo academico estruturado.

---

## Disciplinas Monitoradas

- `EADCSTAD05 - Arquitetura e Aplicacoes para Mobile`
- `EADCSTAD05 - Desenvolvimento de Aplicacoes Hibridas`
- `EADCSTAD05 - Desenvolvimento de Aplicacoes Web-Mobile`
- `EADCSTAD05 - Design Thinking e Gestao da Inovacao`
- `EADCSTAD05 - MVP Mobile Development`

---

## Como Rodar

### 1. Clonar e Instalar Dependencias

```powershell
git clone https://github.com/brendapmedeiros/canvas-academic-automation.git
cd canvas-academic-automation

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configurar as Variaveis (.env)

Copie o `.env.example` para `.env` e preencha suas credenciais:

```ini
CANVAS_API_URL=https://unifeso.instructure.com
CANVAS_API_TOKEN=seu_token_gerado_no_canvas
CALENDAR_ID=primary
```

*(Para gerar o token no Canvas: Conta > Configuracoes > Tokens de Acesso Aprovados > Novo Token de Acesso).*

### 3. Executar

- **Rodar tudo (conteudo para o NotebookLM + agenda .ics):**
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
3. Pronto. A IA tera o texto integral das aulas, teorias e codigos para responder suas duvidas.

### No Google Calendar
1. O script gera o arquivo `agenda_academica.ics` na raiz do projeto.
2. No Google Calendar Web, va em **Configuracoes > Importar e exportar**.
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
