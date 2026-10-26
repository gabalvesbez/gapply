# Seu frontend React

Backend: `http://127.0.0.1:8000`. Swagger em `/docs`, contrato em `/openapi.json`.
Tudo abaixo usa o prefixo `/api/v1`.
O backend deve permanecer local e usar um worker.

## Cabeçalhos e erros

`X-API-Key` é o valor de `API_KEY` no .env do backend. Durante desenvolvimento
local, use uma configuração local do React que não vá para o Git.
**Variáveis VITE_* são públicas no bundle**: esta chave só serve para uso pessoal local.
As chaves dos provedores nunca devem estar no React.

Para JSON, envie `Content-Type: application/json`.
Para upload, use FormData e **não** defina Content-Type; o navegador acrescenta
o boundary multipart.

Erros de domínio: `{ "detail": "mensagem" }`.
Validação pode incluir `errors: [{location, message}]`.
O limite global do corpo pode retornar texto puro em 413; o frontend deve tratar
respostas que não sejam JSON.

## Requisição de upload

Exemplo de chamada, sem implementar uma tela:

```javascript
const body = new FormData();
body.append("file", selectedFile);
const response = await fetch(
  `http://127.0.0.1:8000/api/v1/profiles/${profileId}/resumes`,
  { method: "POST", headers: { "X-API-Key": localApiKey }, body }
);
const payload = await response.json();
if (!response.ok) throw new Error(payload.detail ?? "Falha no upload");
```

A resposta contém `id`, `profile_id`, `filename`, `text`, `warnings`,
`created_at`. Guarde `id` como resume_id.
Para baixar o original, faça fetch autenticado em `/resumes/{id}/file` e use Blob;
um link comum não envia X-API-Key.

## Telas que você pode construir

| Tela | Endpoints | Comportamento |
| --- | --- | --- |
| Perfil | POST/GET /profiles; GET/PUT /profiles/{id} | Editar e confirmar |
| Currículo | POST/GET /profiles/{id}/resumes | Upload, texto e avisos |
| Entrevista | POST/GET /profiles/{id}/messages | Chat e proposta revisável |
| Fontes | GET/POST /sources; DELETE /sources/{id} | Empresas Greenhouse/Lever |
| Pesquisa | POST/GET /searches; GET /searches/{id} | Progresso, resultados e ações humanas |
| Vagas | GET /jobs; GET /jobs/{id}; POST /jobs/import | Lista, detalhes e importação |
| Avaliações | POST /jobs/{id}/evaluate; GET /profiles/{id}/evaluations | Prioridades e lacunas |
| Candidaturas | POST/GET /applications; GET /applications/{id} | Histórico e estado |
| Formulário | POST /applications/{id}/open; GET /applications/{id}/form | Navegador e campos |
| Preencher/enviar | POST /applications/{id}/fill e /submit | Revisão explícita |
| Resultado | PATCH /applications/{id}/status | Confirmar envio/entrevista/oferta |

## Perfil e entrevista

`POST /profiles` aceita {} ou campos:
name, email, phone, location, linkedin, portfolio, skills[], interests[], titles[],
markets[], languages[], remote, seniority e summary.
O retorno de perfil é `{id, data, confirmed, created_at}`.

`PUT /profiles/{id}` substitui o perfil completo:
```json
{"data":{"name":"Ana","skills":["Python"],"titles":["Backend Developer"],"markets":["Portugal"],"remote":true},"confirmed":true}
```

Campos omitidos assumem padrões; não envie apenas um campo esperando um PATCH.
Confirmar exige pelo menos um título. Após conversar com IA, mostre a proposta
para edição e envie-a ao PUT somente quando o usuário confirmar.

`POST /profiles/{id}/messages` recebe `{"message":"Quero trabalhar com backend"}`
e retorna `answer`, `proposed_profile`, `ready_for_search`,
`requires_profile_confirmation: true`.
No histórico, mensagens assistant contêm JSON serializado com esses campos.

## Pesquisa

Cadastrar fonte:
```json
{"provider":"lever","board":"nome-da-empresa","region":"global"}
```
Ou provider greenhouse. O usuário informa board real; não há catálogo global embutido.

Iniciar pesquisa:
```json
{
  "profile_id":"UUID",
  "keywords":["Python","Backend Developer"],
  "markets":["Portugal","Lisboa"],
  "include_remotive":true,
  "source_ids":[],
  "browser_sources":["linkedin","indeed"],
  "limit":100
}
```

Retorna 202 com o registro da execução. Consulte `GET /searches/{id}` a cada
1–2 segundos enquanto queued/running. O resultado contém:
- `jobs`: registros `{id, fingerprint, data, created_at}`.
- `result.sources`: contagem e erro por fonte.
- `result.browser_tasks`: links e instruções para verificação humana.
- `status`: queued, running, completed, partial, failed ou interrupted.

completed refere-se à fase das APIs. As tarefas de navegador são ações separadas
do usuário; não espere que login/CAPTCHA sejam resolvidos por polling.
Não faça polling de novas buscas; somente da execução já criada.

`job.data` contém title, company, location, description, url, apply_url, provider
e campos opcionais como attribution/salary. Renderize descrição como texto.
Mostre a atribuição Remotive e o link original quando presentes.

## Navegador para LinkedIn/Indeed

1. `POST /browser/sessions` com `{"url":"link retornado pela busca"}`.
2. Usuário conclui login/verificação na janela que abriu no computador do backend.
3. `GET /browser/sessions/{id}/jobs` lista links da página atual.
4. Usuário abre a vaga nessa mesma janela; `GET /browser/sessions/{id}/page`
   fornece título e texto. Revise: o texto pode conter menus e conteúdo alheio à vaga.
5. `POST /jobs/import` recebe title, company, location, description e url.
6. `DELETE /browser/sessions/{id}` fecha a aba.

Também é possível copiar a descrição manualmente para importar.

## Avaliar

```json
{"profile_id":"UUID","provider":"rules"}
```

Providers: rules (local), deepseek e jev (chaves necessárias).
Retorna registro com `data.priority` (prioritize/consider/low/unknown),
`reasons`, `missing_information`, provider e snapshot do perfil.
Jev pode retornar probabilidades, mas não justificativas em prosa.

## Candidatar

Crie:
```json
{"profile_id":"UUID","job_id":"UUID","resume_id":"UUID"}
```

Abra /applications/{id}/open. A resposta contém session_id.
Na janela, navegue para a etapa desejada antes de inspecionar.

GET /applications/{id}/form retorna:
- url, session_id, review_token.
- fields: field_id, label, type, tag, required, disabled, value, options, invalid.
- suggested_value, quando existir, é sugestão que você precisa mostrar para revisão.
- buttons: button_id, label, disabled.

Os identificadores só valem para a página inspecionada. Se navegar, inspecione de novo.
O frontend deve oferecer edição; não enviar todos os suggested_value sem revisão.

Preencher:
```json
{
  "fields":[{"field_id":"f0-e2","value":"Ana"},{"field_id":"f0-e3","value":"ana@example.com"}],
  "resume_field_id":"f0-e8"
}
```

Use booleanos para checkbox/radio e value da opção para selects.
A resposta inclui filled/skipped e nova inspeção. Campos não reconhecidos podem
ser preenchidos diretamente no navegador. Consents são escolhas explícitas.

Enviar:
```json
{"button_id":"f0-e10","review_token":"token-da-ultima-inspecao","confirmed":true}
```

Só chamar após mostrar a revisão e o usuário escolher o botão de envio final.
Mudanças na página invalidam o token. Nenhum envio é repetido automaticamente.
A resposta é submission_unknown mesmo após clicar: a API não inventa confirmação.

Após verificar o site:
```json
{"status":"submitted","note":"A página mostrou a confirmação de recebimento."}
```

Use PATCH /applications/{id}/status. Também aceita rejected, interview, offer,
withdrawn. Se você verificar que NÃO houve envio, use not_submitted com uma nota;
isso permite abrir uma nova sessão e tentar novamente com outra revisão explícita.
O histórico registra horário e notas; não envia nada ao site.
Candidatura duplicada para perfil+vaga retorna 409.

## Escopo de acesso

Esta API não tem contas/tenants. Todos os perfis pertencem à mesma instalação
pessoal. Hospedar para usuários diferentes exige autenticação e isolamento de
dados, além de separar o navegador local em um agente por usuário.
