# Guia do backend por domínio

Um domínio é uma área de responsabilidade do produto. Neste projeto, perfil,
currículo, vaga e candidatura têm suas próprias pastas. Navegador e sistema são
módulos de apoio organizados com o mesmo padrão.

É um **monólito modular**: uma aplicação FastAPI, um processo e um banco, com
pastas separadas por assunto. Não são vários servidores nem microserviços.

## Como ler o código

```text
Requisição do React/Swagger
    → router.py: endpoint, parâmetros, dependências e resposta HTTP
    → schemas.py: FastAPI/Pydantic valida os dados recebidos
    → services.py: executa a operação e aplica as regras
        → models.py + sessão SQLAlchemy: consulta/persistência no banco
        → repository.py: persistência especializada, quando necessária
        → client.py / integrations: comunicação externa
        → extractors: leitura local de documentos
    → resposta para o React/Swagger
```

O schema é usado na assinatura da rota: a validação ocorre antes de executar
o corpo da função. O diagrama mostra responsabilidades, não uma cadeia literal
de chamadas entre arquivos.

`schemas.py` e `models.py` têm papéis diferentes. Um schema descreve e valida
um pedido/resposta, como os campos enviados para criar um perfil. Um model
descreve uma tabela, incluindo ID e data de criação gerados pelo backend.
Um arquivo não substitui o outro.

Os serviços recebem a sessão do banco ou o cliente de navegador como argumentos;
não recebem `Request` nem usam `Depends`. Para manter esta mudança focada,
alguns serviços ainda usam `HTTPException` para erros. Portanto, esta é uma
organização pragmática por domínio, sem isolamento completo do FastAPI.

Consultas simples ficam nos serviços. Não criamos um repository repetindo cada
consulta: o de vagas existe porque a deduplicação é compartilhada entre busca
automática e importação manual. Há dependências explícitas entre modelos de
domínios, como candidatura → perfil, vaga e currículo.

## Ponto de entrada e componentes compartilhados

| Arquivo | Responsabilidade |
| --- | --- |
| [`app/main.py`](../app/main.py) | Cria o FastAPI, registra os routers, configura CORS, limite de upload e respostas de erro. Na inicialização aplica migrações, interrompe buscas abandonadas e prepara o navegador; no encerramento cancela tarefas e fecha recursos. |
| [`app/models.py`](../app/models.py) | Importa os models de todos os domínios para registrar as nove tabelas em `Base.metadata`. Tanto a aplicação quanto o Alembic usam esse registro. Importar models não cria tabelas no banco. |
| [`app/core/config.py`](../app/core/config.py) | Lê `.env`, URL do banco, chaves, modelos de IA, diretório de dados, origens CORS e limites dos documentos. |
| [`app/core/database.py`](../app/core/database.py) | Configura engine e sessões SQLAlchemy. Define `Base`, geração de IDs/datas, `get_session` e conversão de registros em dicionários. Não concentra mais as tabelas. |
| [`app/core/security.py`](../app/core/security.py) | Valida `X-API-Key` nas operações protegidas. |
| [`app/core/schemas.py`](../app/core/schemas.py) | Define a base `Input` dos contratos: rejeita campos desconhecidos e remove espaços nas pontas dos textos. |
| [`app/core/repository.py`](../app/core/repository.py) | A função `require` procura um registro pelo ID e responde com erro 404 quando não existe. |
| [`app/integrations/ai.py`](../app/integrations/ai.py) | Faz chamadas HTTP a DeepSeek/Jev, trata indisponibilidade e valida respostas. Fica compartilhado porque perfil e vagas usam IA. A decisão de quando chamar continua nos serviços de cada domínio. |

`__init__.py` identifica os pacotes Python. Os arquivos desse nome em `app`,
`core`, `integrations`, `domains`, cada domínio e `resumes/extractors` não têm
regras de negócio: permitem organizar os imports.

## Perfis — `app/domains/profiles`

| Arquivo | O que você encontra |
| --- | --- |
| [`router.py`](../app/domains/profiles/router.py) | Endpoints para criar, listar, consultar, atualizar perfil e conversar na entrevista. Recebe os dados e chama o serviço correspondente. |
| [`services.py`](../app/domains/profiles/services.py) | Criação e confirmação do perfil, histórico da conversa e montagem do contexto enviado à IA. Exige pelo menos um cargo para confirmar. A proposta da IA precisa ser revisada; não sobrescreve automaticamente o perfil. |
| [`schemas.py`](../app/domains/profiles/schemas.py) | `ProfileData`, `ProfileUpdate`, `ChatInput` e `InterviewResult`: contato, competências, objetivos, mensagens e proposta estruturada. |
| [`models.py`](../app/domains/profiles/models.py) | Tabelas `profiles` e `messages`: perfil salvo e histórico da entrevista. |

Exemplo: `PUT /api/v1/profiles/{id}` → valida `ProfileUpdate` → chama
`services.update` → verifica cargos se `confirmed` for verdadeiro → atualiza
`Profile` → `db.commit()` → devolve o perfil salvo.

## Currículos — `app/domains/resumes`

| Arquivo | O que você encontra |
| --- | --- |
| [`router.py`](../app/domains/resumes/router.py) | Recebe `UploadFile`, limita a leitura e fecha o arquivo HTTP. Encaminha nome e bytes ao serviço. Também lista currículos e transforma o original em resposta de download. |
| [`services.py`](../app/domains/resumes/services.py) | Valida nome, extensão, tamanho e texto; escolhe extrator PDF/DOCX. Salva o original e seu registro, lista documentos e verifica se o arquivo de download existe. A leitura pesada roda fora do loop assíncrono. |
| [`schemas.py`](../app/domains/resumes/schemas.py) | `ResumeTextResponse`: nome, formato, texto e avisos da extração. Também declara `ErrorResponse`, um formato de erro simples; os handlers globais montam os erros atuais. |
| [`models.py`](../app/domains/resumes/models.py) | Tabela `resumes`: relação com perfil, nome, caminho local, texto extraído, avisos e data. O caminho interno não entra no dicionário público. |
| [`errors.py`](../app/domains/resumes/errors.py) | Erros específicos: documento vazio/inválido, grande, protegido, formato não suportado ou sem texto. `main.py` os converte em respostas HTTP. |
| [`extractors/pdf.py`](../app/domains/resumes/extractors/pdf.py) | Extrai texto com pypdf e verifica proteção, estrutura e limite de páginas. Não faz OCR. |
| [`extractors/docx.py`](../app/domains/resumes/extractors/docx.py) | Valida o ZIP interno do DOCX e lê parágrafos/tabelas na ordem do corpo, com limites de descompressão e aninhamento. |

Exemplo: upload → bytes → `services.upload` → `extract_resume_text` → extrator
→ arquivo em `.data/resumes` + registro em `resumes` → JSON com texto e avisos.

## Vagas — `app/domains/jobs`

Fontes, execução de buscas e avaliação permanecem juntas porque fazem parte da
descoberta de vagas. Se crescerem, podem virar domínios próprios mais tarde.

| Arquivo | O que você encontra |
| --- | --- |
| [`router.py`](../app/domains/jobs/router.py) | Endpoints de fontes, buscas, vagas, importação e avaliação. Mantém as URLs existentes. |
| [`services.py`](../app/domains/jobs/services.py) | Cadastra fontes, exige perfil confirmado, inicia a tarefa de busca, consulta resultados e coordena avaliação por regras, DeepSeek ou Jev. Persiste avaliações com uma cópia do perfil usado. |
| [`schemas.py`](../app/domains/jobs/schemas.py) | Contratos de fonte, pesquisa, importação, pedido de avaliação e resposta estruturada da avaliação. Define limites e valores aceitos. |
| [`models.py`](../app/domains/jobs/models.py) | `Source` (fontes), `Job` (vagas), `SearchRun` (execuções), `Evaluation` (avaliações) e `Cache` (cache das fontes). |
| [`search.py`](../app/domains/jobs/search.py) | Executa buscas em segundo plano, consulta fontes com concorrência limitada, filtra termos/mercados, guarda progresso e registra falhas parciais. Gera também links para busca assistida no navegador. |
| [`repository.py`](../app/domains/jobs/repository.py) | Normaliza a URL, remove parâmetros de rastreamento e calcula a identificação usada para evitar duplicar uma vaga. Salva/atualiza a vaga na sessão; o serviço/tarefa confirma a transação. |
| [`client.py`](../app/domains/jobs/client.py) | Acessa as APIs Remotive, Greenhouse e Lever, normaliza as respostas e mantém o cache da Remotive. Não escolhe quais vagas interessam ao perfil. |

Exemplo: `POST /api/v1/searches` → serviço valida o pedido e grava `SearchRun`
→ inicia `search.search` → clientes consultam APIs → filtro → repository salva
vagas → progresso fica disponível em `GET /api/v1/searches/{id}`.

## Candidaturas — `app/domains/applications`

| Arquivo | O que você encontra |
| --- | --- |
| [`router.py`](../app/domains/applications/router.py) | Endpoints de criação, listagem, consulta, abertura, inspeção, preenchimento, envio e atualização de estado. |
| [`services.py`](../app/domains/applications/services.py) | Verifica perfil confirmado, currículo do perfil e candidatura duplicada. Guarda cópia do perfil, sugere contatos, coordena formulário/revisão e registra histórico. Preserva o estado de envio incerto para não repetir uma candidatura automaticamente. |
| [`schemas.py`](../app/domains/applications/schemas.py) | `ApplicationInput`, `FieldValue`, `FillInput`, `SubmitInput` e `ApplicationStatus`: IDs, valores escolhidos, revisão e confirmação do usuário. |
| [`models.py`](../app/domains/applications/models.py) | Tabela `applications`, com vínculos a perfil/vaga/currículo, estado e dados do histórico. A restrição perfil + vaga impede duplicação. |

O serviço decide **se a operação é permitida**; o cliente do navegador executa
a interação com a página. A revisão e o envio continuam explícitos.

## Navegador — `app/domains/browser`

| Arquivo | O que você encontra |
| --- | --- |
| [`router.py`](../app/domains/browser/router.py) | Endpoints para abrir/fechar sessões e coletar links/texto da página. |
| [`services.py`](../app/domains/browser/services.py) | Encaminha operações de sessão ao cliente sem depender do objeto HTTP `Request`. É pequeno porque a coordenação das candidaturas está em seu próprio domínio. |
| [`schemas.py`](../app/domains/browser/schemas.py) | `OpenBrowser`, com a URL recebida para abrir uma sessão. |
| [`client.py`](../app/domains/browser/client.py) | Implementa `BrowserWorker` usando Playwright em uma thread dedicada. Controla páginas, navegação permitida, campos, anexos, token de revisão e clique. Login/CAPTCHA continuam manuais. |

Não há `models.py`: as sessões ativas pertencem ao processo. O histórico das
candidaturas é salvo em `applications`; cookies ficam no perfil local do navegador.

## Sistema — `app/domains/system`

| Arquivo | O que você encontra |
| --- | --- |
| [`router.py`](../app/domains/system/router.py) | Expõe `/health` e `/api/v1/capabilities`. A segunda rota exige a chave local. |
| [`services.py`](../app/domains/system/services.py) | Executa `SELECT 1` para verificar o banco e informa recursos configurados, formatos e limites, sem revelar chaves. |

Não precisa de schemas de entrada ou tabelas próprias nesta versão.

## Banco, configuração e documentação

| Arquivo | Para que serve |
| --- | --- |
| [`pyproject.toml`](../pyproject.toml) | Nome do projeto Python, versão mínima, dependências e configuração de empacotamento. |
| [`uv.lock`](../uv.lock) | Versões resolvidas das dependências para instalações reproduzíveis com uv. Entra no Git; é gerenciado pelo uv. |
| `.env` | Configuração real deste computador e credenciais. É local e ignorado pelo Git. |
| [`.env.example`](../.env.example) | Exemplo das variáveis necessárias; não contém suas credenciais reais. |
| [`.gitignore`](../.gitignore) | Define o que não deve ser versionado: ambiente virtual, segredos, banco, arquivos locais e caches. |
| [`.editorconfig`](../.editorconfig) | Convenções de codificação/indentação/finais de linha para editores. |
| [`compose.yaml`](../compose.yaml) | Serviço PostgreSQL opcional para desenvolvimento. O padrão atual continua SQLite. |
| [`alembic.ini`](../alembic.ini) | Aponta a configuração do Alembic para a pasta de migrações. |
| [`migrations/env.py`](../migrations/env.py) | Liga o Alembic ao engine e à metadata. Importa `app.models` para conhecer todos os modelos, mesmo os que não aparecem em uma rota. |
| [`migrations/script.py.mako`](../migrations/script.py.mako) | Modelo de texto usado pelo Alembic para gerar novas migrações; não é uma migração executada. |
| [`migrations/versions/98c8b7839edb_initial_schema.py`](../migrations/versions/98c8b7839edb_initial_schema.py) | Migração inicial: `upgrade` cria as tabelas e `downgrade` desfaz essa estrutura. Preservada nesta reorganização. |
| [`README.md`](../README.md) | Como instalar, executar e usar o backend; descreve limitações e integrações. |
| [`docs/architecture.md`](architecture.md) | Este mapa dos arquivos e responsabilidades. |
| [`docs/react-integration.md`](react-integration.md) | Endpoints, exemplos de payload e estados que o futuro React precisa tratar. |
| [`docs/openapi.json`](openapi.json) | Cópia exportada do contrato da API. A versão servida pela aplicação fica em `/openapi.json` e alimenta o Swagger em `/docs`. |
| [`docs/verification.md`](verification.md) | Registra o que foi verificado e quais integrações ainda precisam de validação real. |

Pastas geradas não são novos domínios: `.venv` contém Python/dependências;
`*.egg-info` contém metadados de instalação; `__pycache__` contém cache do Python;
`.data` guarda o banco, originais, perfil do navegador e verificações locais.
Os arquivos nessas pastas são gerados em tempo de instalação/execução e não
devem ser editados para implementar regras do produto.

## O que mudou nesta reorganização

| Antes | Agora |
| --- | --- |
| `app/modules/*/router.py` com regras misturadas | `app/domains/*/router.py` delegando para `services.py` |
| `app/database.py` com todas as tabelas | `app/core/database.py` para conexão; `models.py` em cada domínio para tabelas |
| `app/contracts.py` | `schemas.py` dentro dos domínios e uma base comum em `core` |
| `app/browser.py` e rotas dentro de candidaturas | Domínio `browser` com cliente, serviços, schemas e rotas |
| `app/clients/jobs.py` | `app/domains/jobs/client.py` |
| `app/clients/ai.py` | `app/integrations/ai.py` |
| `app/repository.py` misturando consulta comum e vaga | Consulta comum em `core`; deduplicação em `domains/jobs/repository.py` |

As URLs, contratos HTTP e definições das tabelas foram preservados. Mover uma
classe Python de pasta não altera sua tabela, pois o `__tablename__` e as colunas
continuam iguais. Por isso não foi criada uma nova migração nem transferido o banco.
Imports Python internos antigos devem usar os novos caminhos.

Para adicionar uma tabela no futuro, crie o model no domínio e registre-o em
`app/models.py`; depois gere e revise a migração antes de aplicá-la.
Não se deve editar a migração inicial de um banco já utilizado para simular uma
nova mudança de estrutura.

## Ordem sugerida para estudar

1. `system/router.py` → `system/services.py`: acompanhe `/health`, o menor fluxo.
2. `profiles/schemas.py` → `router.py` → `services.py` → `models.py`: criação do perfil.
3. `core/database.py`: entenda sessão, consulta e `commit` usando o fluxo anterior.
4. `resumes`: siga um upload até o extrator e o armazenamento.
5. `jobs`: siga a criação da busca até progresso/resultados.
6. `applications` e `browser`: acompanhe revisão, estados e interação com formulário.
7. `main.py` e migrações: veja como os componentes são montados e inicializados.

Ao abrir uma função, tente responder: o que entra, qual regra aplica, de quem
depende e o que devolve? Isso ajuda a compreender uma operação por vez.
