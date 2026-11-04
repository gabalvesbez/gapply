# Verificação desta implementação

## Reorganização por domínio — 04/11/2026

Verificada com as dependências existentes do `uv.lock`, sem alterações de versões:

- OpenAPI gerado antes/depois idêntico, incluindo URLs, schemas e códigos de resposta.
- Definições das nove tabelas preservadas: colunas, tipos, nulabilidade, chaves
  primárias e referências. `alembic check` em SQLite isolado migrado também não
  detectou novas operações de schema.
- Fluxo local abaixo repetido após a mudança: upload, perfil, avaliação, busca,
  formulário sintético, proteção contra reenvio e persistência após reiniciar.
- Rotas de fontes, listagens e erros de validação verificadas separadamente.
- Entrevista com resposta controlada: histórico salvo e confirmação do perfil
  mantida sob controle do usuário.
- Rotas de sessões do navegador verificadas com cliente substituto, além da
  verificação de candidaturas com Chromium e formulário sintético.
- Nenhum import dos módulos antigos restante no código. Serviços não recebem
  `Request` nem usam `Depends`/`APIRouter`.
- Links locais do README e do guia de arquitetura verificados.

As verificações usaram bancos e documentos temporários em `.data`; nenhuma
candidatura real foi enviada. PostgreSQL e provedores reais de IA não foram
validados nesta refatoração. Nenhuma nova migração ou suíte pytest foi adicionada.

Os comandos de verificação pontual foram `uv run --locked --no-sync python
.data/verify_backend.py` e `uv run --locked --no-sync python .data/check_domains.py`.
Esses scripts locais são ignorados pelo Git; este registro descreve a execução,
não substitui a futura suíte de testes do projeto.

## Implementação inicial — 26/10/2026

Verificado em 26/10/2026, Python 3.14 no Windows, com dependências do uv.lock.

## Fluxo local

Validação executada em banco SQLite isolado e formulário sintético interceptado
pelo Playwright, sem envio de dados para empregadores:

- Saúde, autenticação, CORS e geração de OpenAPI.
- Upload e leitura de PDF selecionável e DOCX com tabela.
- Download do original e conteúdo preservado.
- Arquivos vazios, corrompidos, formatos não suportados e limites de upload/corpo.
- Criação/confirmação de perfil e deduplicação de vagas por URL.
- Avaliação textual e erro explícito para provedores sem chave.
- Busca em segundo plano com dados controlados e ações de navegador pendentes.
- Detecção de formulário, sugestões, preenchimento e upload de currículo.
- Revisão invalidada por token antigo e bloqueio de clique repetido.
- Registro de confirmação pelo usuário e persistência após reiniciar.

## Conectores reais, somente leitura

- Remotive: resposta válida, 10 vagas normalizadas na consulta realizada.
- Greenhouse: resposta válida, 717 vagas na página pública Stripe usada para verificação.
- Lever: resposta válida, zero vagas no site de exemplo `lever` consultado.

Esses números são apenas a observação daquele momento, não uma cobertura garantida.
As empresas consultadas não foram cadastradas como preferência do usuário.

## Não verificado com serviços reais

- DeepSeek e Jev: implementados conforme contratos documentados; faltam chaves
  para confirmar autenticação, saldo, modelos e qualidade das respostas reais.
- PostgreSQL: configuração e migração fornecidas; nenhum servidor local estava disponível.
- Login, CAPTCHA e candidatura em empregador real: exigem intervenção do usuário;
  a automação foi verificada somente no formulário sintético.

Não foi adicionada uma suite pytest. Os scripts pontuais de verificação ficam
na pasta local ignorada `.data`, separados do código de aplicação.
