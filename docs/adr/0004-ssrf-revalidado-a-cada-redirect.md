# 0004 — Validação SSRF a cada salto de redirect

- Status: aceita
- Data: 2026-11-03

## Contexto

`_check_ssrf` validava só a URL enviada pelo usuário. Depois disso, `requests` seguia redirects sozinho. Uma página pública podia responder `302 Location: http://169.254.169.254/...` (metadata de nuvem) ou `http://127.0.0.1:...`, e o servidor buscava o destino interno. Outros caminhos também baixavam conteúdo sem passar pela checagem: o `newspaper4k` (fallback de extração) baixava a URL de novo, e o snapshot do Wayback aceitava qualquer host. Endereços que não eram parseáveis eram ignorados em vez de bloqueados, e faltavam faixas como `0.0.0.0/8`, multicast, NAT64 e IPv4 embutido em IPv6.

## Decisão

- `WebScraper._fetch_once` usa `allow_redirects=False` e segue até `SCRAPING_MAX_REDIRECTS` saltos manualmente, chamando `_check_ssrf` antes de cada requisição.
- `_check_ssrf` bloqueia, além das faixas configuradas, qualquer IP `is_private`, `is_loopback`, `is_link_local`, `is_multicast`, `is_reserved` ou `is_unspecified`, e avalia o IPv4 embutido em endereços IPv6 (`::ffff:`, 6to4, Teredo). Resolução vazia ou IP não parseável bloqueiam.
- `newspaper4k` recebe o HTML já baixado (`download(input_html=...)`).
- Wayback: a URL do artigo é codificada na query, o snapshot precisa ser de `archive.org` e é baixado pelo mesmo `_fetch` (SSRF, limite de tamanho, retry).

## Consequências

- Redirect para endereço interno falha com `ValueError` e não é re-tentado.
- Resta a janela de *DNS rebinding*: a checagem resolve o nome e o `requests` resolve de novo ao conectar. Fechar isso exige fixar o IP validado na conexão (adapter próprio) ou um proxy de saída. Isso fica registrado como limitação.
