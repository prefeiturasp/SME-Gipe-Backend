# Changelog

Todas as mudanças relevantes deste projeto serão documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [0.2.0] - 2026-05-07

### Removed
- Removidos os arquivos `carga_unidades_viewset` e `carga_unidade_service`
- Removida a rota relacionada à carga de unidades das URLs

---

## [0.1.0] - 2026-05-06

### Added
- Configuração inicial do Django e Django REST Framework
- Integração com banco de dados PostgreSQL
- Emissão de tokens de acesso
- Controle de permissões
- Sistema de autenticação (login/logout)
- Alteração e recuperação de senha
- Implementação da gestão de perfis (Assistente de Diretor, Diretor de escola, Ponto focal DRE, GIPE)
- Implementação da gestão de usuários
- Implementação da gestão de unidades
- Estrutura inicial de CI/CD