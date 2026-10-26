# Verificação desta implementação

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
