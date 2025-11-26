# CNC Telemetry Box v1 - Pacotes Comerciais Iniciais

Este documento registra os **pacotes comerciais de referencia** para o
lançamento do CNC Telemetry Box v1. Os valores aqui descritos sao
**placeholders** e devem ser ajustados pelo Vinicius conforme:

- custo real de hardware
- impostos e frete
- margem desejada
- nivel de servico prestado (SLA, suporte, deslocamento)

## Pacotes

### Tabela Resumida

| Pacote | Capacidade | Inclusoes principais                                   | Faixa de preco sugerida (R$) |
|--------|------------|---------------------------------------------------------|-------------------------------|
| Box-5  | Ate 5 CNC  | Box + instalacao + 12 meses de Telemetry basico (5x)   | 4.500 – 6.000                |
| Box-10 | Ate 10 CNC | Box + instalacao + 12 meses de Telemetry basico (10x)  | 7.000 – 10.000               |

### Box-5 (ate 5 maquinas)

**Escopo alvo:** celula pequena ou setor com ate 5 maquinas CNC.

**Inclui:**

1. 1x **CNC Telemetry Box** (hardware homologado para ate 5 maquinas).
2. Instalacao e configuracao da rede e das CNC (ate 5 maquinas) para coleta
   de telemetria.
3. **12 meses** de Telemetry basico para ate 5 maquinas, incluindo:
   - coleta continua de estado/RPM/feed
   - dashboard local no Box
   - armazenamento local em banco Postgres

**Faixa de preco sugerida (placeholder):**

- Custo estimado de hardware: ~R$ 1.800 – 2.500
- Venda total do pacote (hardware + servico + 12 meses Telemetry basico):
  **R$ 4.500 – 6.000**

> Observacao: estes numeros sao apenas referenciais. Devem ser recalibrados
> por oportunidade concreta, custo real do hardware e nivel de servico.

### Box-10 (ate 10 maquinas)

**Escopo alvo:** celula/setor com parque ate 10 maquinas CNC.

**Inclui:**

1. 1x **CNC Telemetry Box** (hardware igual ou levemente mais forte que o Box-5,
   dimensionado para ate 10 maquinas).
2. Instalacao e configuracao de rede e das CNC para ate 10 maquinas.
3. **12 meses** de Telemetry basico para ate 10 maquinas.

**Faixa de preco sugerida (placeholder):**

- Venda total do pacote (hardware + servico + 12 meses Telemetry basico):
  **R$ 7.000 – 10.000**

> Observacao: tambem aqui os valores sao estruturais, servindo apenas para
> dar ordem de grandeza em propostas iniciais.

## Consideracoes Comerciais Importantes

- Os valores acima **nao incluem** a mensalidade Telemetry/máquina **apos o
  1o ano**. A recorrencia deve ser precificada separadamente (ex.: plano por
  maquina/mês) conforme a estrategia comercial.
- Deslocamentos longos, hospedagem e despesas de viagem podem ser cobrados
  a parte, conforme combinado com o cliente.
- Upgrades de capacidade (de Box-5 para Box-10 ou mais maquinas por Box)
  devem considerar:
  - limite de CPU/RAM do hardware
  - volume de dados por maquina
  - requisitos de SLA

Este documento deve ser revisado periodicamente conforme os custos reais de
campo e feedback dos primeiros clientes.
