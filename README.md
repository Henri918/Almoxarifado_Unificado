# Almoxarifado Unificado

Este pacote reúne a interface web original (`templates/` e `static/`), o aplicativo Expo (`mobile/`) e uma única API Flask (`app.py`) conectada ao mesmo banco MySQL.

## Estrutura
- `app.py`: API `/api/...` usada pelo aplicativo e rotas web (`/login`, `/adm`, `/dps`, etc.).
- `database.sql`: esquema único compartilhado.
- `templates/` e `static/`: site original adaptado para o esquema unificado.
- `mobile/`: aplicativo Expo.

## Executar backend + MySQL
Na pasta raiz:
```bash
docker compose up --build
```
API: `http://localhost:5000/api/health`
Site: `http://localhost:5000/`

Configuração padrão do Docker:
- MySQL: porta `3307` no computador (porta `3306` dentro do Docker)
- Flask: porta `5000`
- Banco: `login`

## Executar o app no celular
Na pasta `mobile/`, ajuste `mobile/.env` para o IP local do computador:
```env
EXPO_PUBLIC_API_URL=http://SEU_IP_LOCAL:5000/api
```
Depois:
```bash
npm install
npx expo start
```
O celular e o computador precisam estar na mesma rede Wi-Fi. Não use `localhost` no celular: use o IPv4 do computador.

## Banco já existente
O Docker executa `database.sql` automaticamente apenas quando o volume MySQL é criado pela primeira vez. Se você já tinha um volume antigo, o script não será reaplicado. Faça backup antes de qualquer migração. Não execute `docker compose down -v` se quiser preservar os dados existentes.

## Observações
- A API móvel usa tokens Bearer; o site usa sessão Flask. Os dois autenticam contra a mesma tabela `usuario`.
- Senhas são armazenadas com bcrypt.
- O esquema unificado usa `movimentacoes(produto_id, usuario_id, quantidade, tipo, data_hora)` com chaves estrangeiras.
- Não coloque a chave secreta do Flask nem credenciais reais em repositório público.
