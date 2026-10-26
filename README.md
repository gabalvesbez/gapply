# Assistente de candidaturas — backend pessoal

FastAPI + uv. Fluxo completo de currículo, perfil, entrevista, pesquisa de vagas,
avaliação e preenchimento assistido de candidaturas. O frontend React fica para você.

## Executar

Na pasta do projeto, com Python 3.12+ e uv:

```powershell
uv sync --locked
# Apenas se ainda não existir .env:
Copy-Item .env.example .env
uv run --locked playwright install chromium
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
```

A preparação deste projeto já criou um `.env` com uma chave local aleatória.
**Preserve-o**. Em outro computador, copie o exemplo e troque `API_KEY`.
Não coloque chaves DeepSeek/Jev no frontend nem no Git.

Abra [Swagger](http://127.0.0.1:8000/docs), clique em **Authorize** e use
o valor de `API_KEY` do seu `.env`. A saúde fica em
[health](http://127.0.0.1:8000/health). Rotas de dados usam `X-API-Key`.

Use **um worker**. O navegador pertence ao processo local.
`--reload` pode ser usado durante desenvolvimento, mas reiniciar fecha sessões
do navegador e marca buscas em andamento como interrompidas; nunca reenvia candidaturas.

## O que está implementado

- Upload PDF/DOCX até 10 MiB; texto extraído, avisos e original salvos.
- Perfis editáveis e confirmação explícita antes de buscar/candidatar.
- Entrevista contextual e proposta de perfil pelo DeepSeek, quando configurado.
- Histórico de mensagens, vagas, pesquisas, avaliações e candidaturas persistidos.
- Remotive como fonte inicial; Greenhouse/Lever por empresa cadastrada.
- Pesquisa por termos e mercados, com progresso por fonte e erros parciais.
- Links de busca LinkedIn/Indeed; navegador local para login e intervenção humana.
- Coleta de links de vagas da página carregada e importação revisada.
- Avaliação por correspondência textual, DeepSeek ou Jev.
- Identificação de campos, sugestões de contato, preenchimento escolhido e anexo.
- Envio somente após revisão explícita, com proteção contra repetição.
- CORS para React local, Swagger/OpenAPI e migrações Alembic.

## Primeiro fluxo no Swagger

1. `POST /api/v1/profiles`: crie perfil, mesmo inicialmente vazio.
2. `POST /api/v1/profiles/{id}/resumes`: envie currículo no campo `file`.
3. Configure DeepSeek e use `POST /profiles/{id}/messages` para conversar.
   Sem chave, edite o perfil diretamente.
4. Revise `proposed_profile`; use `PUT /profiles/{id}` com `data` completo e
   `confirmed: true`. Uma resposta da IA **não** altera automaticamente seu perfil.
5. `POST /searches`: informe perfil, termos, mercados e fontes.
6. Consulte `GET /searches/{id}` enquanto `queued/running`.
7. Avalie vagas com `POST /jobs/{id}/evaluate`.
8. Crie candidatura com perfil, vaga e currículo em `POST /applications`.
9. Abra-a com `POST /applications/{id}/open`; conclua login/CAPTCHA na janela.
10. Inspecione `GET /applications/{id}/form`, revise sugestões, envie campos para
    `POST /applications/{id}/fill`.
11. Inspecione de novo e envie `button_id`, `review_token` e `confirmed: true`
    para `POST /applications/{id}/submit`, escolhendo o botão final correto.
12. Confira a mensagem real do site e registre o resultado em
    `PATCH /applications/{id}/status`.

Depois da primeira ocorrência, as URLs abreviadas acima mantêm o prefixo `/api/v1`.
Consulte [o guia do React](docs/react-integration.md) para contratos e exemplos.

## Banco e arquivos

SQLite é o padrão local, em `.data/app.db`. Para PostgreSQL:

```powershell
docker compose up -d
# No .env, configure:
# DATABASE_URL=postgresql+psycopg://career:career_local@localhost:5432/career
uv run --locked alembic upgrade head
uv run --locked uvicorn app.main:app --host 127.0.0.1
```

O servidor também aplica migrações ao iniciar. PostgreSQL e Docker precisam estar
instalados para essa opção; não foram encontrados neste computador.
Trocar a URL cria/usa outro banco: **não transfere dados** de SQLite para PostgreSQL.
Senhas do compose são apenas para desenvolvimento local.

Arquivos originais ficam em `.data/resumes`, usando UUIDs; o banco guarda os
metadados. Cookies do navegador ficam em `.data/browser`.
Faça backup do banco e dos originais juntos. A chave protege a API; dados locais
não são criptografados pelo aplicativo.

## Fontes e cobertura

- **Remotive**: vagas remotas, atribuição e link original preservados; cache de 6h,
  sem nova chamada para cada clique. Exiba `attribution` no React. O feed pode
  ter atraso e não cobre todo o mercado.
- **Greenhouse/Lever**: cadastre o identificador público de cada empresa em
  `POST /sources`. Greenhouse: `board` do endereço da página; Lever:
  nome do site e região `global/eu`. Não são APIs globais de pesquisa.
- **LinkedIn/Indeed**: o programa gera a pesquisa; você abre a página pelo endpoint
  de navegador, resolve verificações e solicita os links visíveis. Não contorna
  CAPTCHA, login, bloqueios nem garante coleta completa.
- Mercados são filtros textuais de localização; aceita texto escolhido pelo usuário.
  Use variantes como `Portugal`, `Lisbon`, `Lisboa`, conforme as fontes.
  `Worldwide/Anywhere/Global` são considerados globais. Isso não verifica autorização
  de trabalho, visto ou elegibilidade. `remote` do perfil informa a avaliação, mas
  o filtro automático de mercado não é um classificador de trabalho remoto.
- Vagas são deduplicadas por URL normalizada; anúncios da mesma vaga em URLs
  diferentes ainda podem aparecer separadamente.

## Navegador e envio

O navegador abre **no computador do backend**. Esta versão é para uso pessoal
local, não um serviço multiusuário hospedado. React local usa a chave compartilhada;
não publique essa chave em um site acessível a outras pessoas.

Domínios de navegação suportados: LinkedIn, Indeed, Greenhouse, Lever e Remotive.
Se Remotive apontar para outro sistema, importe o endereço Greenhouse/Lever da
vaga quando existir ou complete a candidatura manualmente.
Os formulários padrão HTML são detectados, inclusive em frames suportados.
Widgets personalizados, etapas adicionais e perguntas não mapeadas podem exigir
preenchimento na própria janela.

A inspeção retorna valores e opções; sugestões são apenas de contato. Respostas
sobre qualificações, vistos, salários, consentimentos e dados sensíveis são suas.
O arquivo é anexado ao site escolhido; sites podem enviar dados ao preencher,
antes do botão final.

`submission_unknown` significa que o clique foi tentado, não que houve sucesso.
Não há retry automático de envio. Confirme o resultado olhando a janela e registre
uma nota. Se comprovar que o envio não ocorreu, registre `not_submitted` para
permitir uma nova tentativa revisada. Nenhuma candidatura real foi enviada durante a implementação.

## IA

Configure `DEEPSEEK_API_KEY`/`DEEPSEEK_MODEL` e, opcionalmente,
`JEV_API_KEY`/`JEV_MODEL` no `.env`, depois reinicie.
As chamadas podem consumir créditos. O currículo e o contexto são enviados ao
provedor somente ao pedir entrevista/avaliação; a extração de arquivo é local.
Sem chave, esses endpoints retornam 503, sem respostas fictícias.

A regra textual local só encontra termos e não usa IA.
Jev classifica, mas não entrega justificativas em prosa. Suas probabilidades
não representam a chance de contratação. A classificação não envia candidaturas.

## Arquitetura

```text
app/
  main.py                 # aplicação, CORS, limites e ciclo de vida
  config.py               # .env e limites
  security.py             # chave local
  database.py             # modelos SQLAlchemy
  repository.py           # consultas compartilhadas e deduplicação
  contracts.py            # entradas e respostas da IA
  browser.py              # Playwright em thread dedicada no Windows
  clients/
    ai.py                 # DeepSeek e Jev
    jobs.py               # Remotive, Greenhouse e Lever
  modules/
    resumes/              # upload, validação, PDF e DOCX
    profiles/             # perfil e entrevista
    jobs/                 # busca, progresso, importação e avaliação
    applications/         # formulários e histórico de candidaturas
migrations/               # migração inicial versionada
docs/                     # contrato e roteiro do frontend
```

Os TODOs foram substituídos por implementação. Não há pytest nem suite de testes
adicionada: mantivemos essa parte para seu aprendizado.

## Limites atuais

Sem OCR ou leitura de .doc. DOCX cobre o corpo (inclusive tabelas), não todos os
cabeçalhos/caixas de texto. PDF com colunas pode ter ordem textual imperfeita.
Limites de upload e ZIP reduzem abuso; o parser de documentos não é uma sandbox
de CPU/memória para hospedar publicamente.

Buscas em execução são interrompidas em reinício; resultados já salvos permanecem.
As tarefas não usam fila distribuída. Entrevistas usam as últimas 20 mensagens e
até 45 mil caracteres do currículo. O texto enviado não inclui todo documento
arbitrariamente grande.

## Documentação oficial

- [FastAPI uploads](https://fastapi.tiangolo.com/tutorial/request-files/)
- [uv projects](https://docs.astral.sh/uv/guides/projects/)
- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html)
- [Lever Postings API](https://github.com/lever/postings-api)
- [Remotive API e condições](https://github.com/remotive-com/remote-jobs-api)
- [DeepSeek](https://api-docs.deepseek.com/)
- [Jev decisões](https://jev-ai.org/docs/decisions/)
