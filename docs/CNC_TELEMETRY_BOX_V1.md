# CNC Telemetry Box v1 – gateway local de telemetria CNC

## Visao geral do produto

O **CNC Telemetry Box v1** e um mini-servidor dedicado para coleta de telemetria de maquinas CNC em uma fabrica. Ele roda de forma **headless** em um appliance Linux (ex.: mini-PC industrial) e concentra:

- Coleta de dados das CNC (via adapters/coletores dedicados).
- Armazenamento local em banco **PostgreSQL**.
- Exposicao de APIs HTTP para dashboards e integracoes.
- Dashboard web local para operadores e engenharia.
- Componente opcional de **sync** para enviar dados para uma Central/Cloud, quando disponivel.

A arquitetura alvo utiliza **Docker + Docker Compose + PostgreSQL**, com todos os componentes isolados em containers para facilitar instalacao, atualizacao e suporte em campo.

## Papel na fabrica

Na pratica, o CNC Telemetry Box funciona como um **gateway local de telemetria CNC**:

- Fica instalado na rede da fabrica, proximo das maquinas CNC.
- Recebe dados dos controladores (ex.: via MTConnect, adaptadores proprietarios ou simuladores).
- Consolida e normaliza as amostras em um banco de dados unico.
- Fornece um **dashboard local** acessivel via navegador (HTTP) na rede interna.
- Pode opcionalmente enviar um resumo ou espelho dos dados para uma **Central de Telemetry** fora da planta.

Isso permite que a fabrica tenha **visibilidade em tempo real** do parque de maquinas, mesmo sem internet, e prepara o terreno para analises mais avancadas na nuvem quando o link estiver disponivel.

## Capacidade alvo (Box v1)

Para a versao v1, o dimensionamento alvo considerado e:

- **Ate 10 maquinas CNC por Box.**
- Frequencia de coleta adequada para indicadores basicos (estado, RPM, avance, etc.).
- Foco em cenarios de **uma celula ou pequeno setor** da fabrica.

Nada impede que o software evolua para suportar mais maquinas por Box no futuro, mas as configuracoes, testes e expectativas iniciais sao otimizadas para o patamar **5–10 maquinas** por unidade.

## Comportamento online vs offline

O Box foi pensado para operar de forma **resiliente a quedas de internet**:

- **Conectado (online)**
  - Continua coletando dados das CNC normalmente.
  - Opcionalmente envia eventos/aggregados para uma **Telemetry Central** configurada (ex.: endpoint HTTPS externo).
  - Pode oferecer funcionalidades adicionais que dependem da Cloud (ex.: relatórios centralizados, comparacao multi-planta).

- **Sem internet (offline)**
  - **A coleta local continua normalmente**, sem interrupcao.
  - Os dados permanecem no banco Postgres do Box.
  - Quando a conexao com a Central voltar, o componente de **sync** pode retomar o envio (estrategia de buffer/retentativa sera detalhada em versoes futuras).

Com isso, o operador nao perde historico nem visibilidade local se o link externo cair temporariamente.

## O que o CNC Telemetry Box NAO faz

Para evitar expectativas erradas, e importante explicitar o que o Box **nao e** e **nao faz**:

- **Nao controla a maquina CNC.**
  - Ele apenas **lê** dados de estado/telemetria, nao envia comandos de movimento, partida/parada ou programa.

- **Nao e um sistema MES completo.**
  - O Box pode expor informacoes uteis para integracao com MES/ERP, mas **nao** cobre, por si so, todas as funcoes de planejamento de producao, apontamento de ordens, gestao de operadores, etc.

- **Nao e um software CAM.**
  - Ele nao gera trajetorias de usinagem, nao substitui ferramentas CAM existentes nem editores de programa.

- **Nao substitui o controle CNC ou o MTConnect Agent oficial do fabricante.**
  - O Box consome dados expostos pelo controle/agent, mas nao altera a logica interna de seguranca ou intertravamentos da maquina.

## Comportamento esperado em campo

Em um piloto ou instalacao inicial, o fluxo tipico e:

1. Instalar o mini-PC (Box) na rede da fabrica.
2. Conectar o Box aos controladores/agents das CNC (IP, portas, protocolos).
3. Subir o stack de containers (db, backend, adapter(s), sync, frontend) via Docker Compose.
4. Acessar o dashboard local (HTTP) a partir de um PC ou tablet na mesma rede.
5. Validar que os estados das maquinas estao sendo atualizados em tempo quase real.

A partir desse baseline, o cliente pode evoluir para integrações com sistemas existentes e para o uso do sync com uma Central de Telemetry.
