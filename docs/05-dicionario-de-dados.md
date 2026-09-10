# Dicionário de dados

Gerado por `python src/gerar_dicionario.py` a partir de
`data/processed/municipio_ano.csv`.

**55,700 instâncias · 70 atributos · município × ano ·
2014–2023**

A coluna **papel** indica como o atributo pode ser usado na modelagem:

- `atributo` — candidato a preditor nas duas etapas;
- `chave` / `rótulo` — identificador, **não entra no modelo**;
- `**ALVO 1**` / `**ALVO 2**` — variável a prever;
- `VAZAMENTO Etapa N` — **proibido** como preditor naquela etapa, porque
  carrega informação do alvo. Ver `docs/04-melhorias-tradeoffs-sensibilidades.md`, S2.

| Coluna | Tipo | Unidade | Fonte | Papel | Faixa | % ausente | Descrição |
|---|---|---|---|---|---|---|---|
| `cod_ibge7` | identificador | - | IBGE Localidades | chave | 1,100,015.00 a 5,300,108.00 | 0.00% | Codigo do municipio com digito verificador. |
| `cod_ibge6` | identificador | - | IBGE Localidades | chave | 110,001.00 a 530,010.00 | 0.00% | Codigo sem digito verificador -- e o que o DATASUS usa. |
| `municipio` | identificador | - | IBGE Localidades | rotulo | 5297 categorias | 0.00% | Nome do municipio. |
| `uf` | nominal | - | IBGE Localidades | atributo | 27 categorias | 0.00% | Sigla da unidade da federacao (27 categorias). |
| `regiao` | nominal | - | IBGE Localidades | atributo | 5 categorias | 0.00% | Grande regiao (5 categorias). |
| `mesorregiao` | nominal | - | IBGE Localidades | atributo | 137 categorias | 0.02% | Mesorregiao IBGE (137 categorias) -- one-hot inviavel. |
| `microrregiao` | nominal | - | IBGE Localidades | atributo | 553 categorias | 0.02% | Microrregiao IBGE (558 categorias) -- one-hot inviavel. |
| `ano` | temporal | ano | construido | atributo | 2,014.00 a 2,023.00 | 0.00% | Ano de referencia da observacao. |
| `capital` | binario | 0/1 | DATASUS TabNet | atributo | 0.00 a 1.00 | 0.00% | 1 se o municipio e capital estadual. |
| `populacao` | discreto | pessoas | IBGE/TCU via DATASUS | atributo | 771.00 a 12,396,372.00 | 0.02% | Populacao residente estimada. |
| `area_km2` | continuo | km2 | IBGE SIDRA 1301 | atributo | 3.60 a 159,533.40 | 0.11% | Area territorial (Censo 2010, fixa no periodo). |
| `densidade_demografica` | continuo | hab/km2 | derivado | atributo | 0.03 a 14,656.55 | 0.11% | populacao / area_km2. |
| `porte_populacional` | ordinal | - | derivado | atributo | 7 categorias | 0.02% | Faixa de populacao em 7 niveis ordenados. |
| `periodo_pandemia` | binario | 0/1 | derivado | atributo | 0.00 a 1.00 | 0.00% | 1 para 2020 e 2021. |
| `pib_mil_reais` | continuo | R$ mil | IBGE SIDRA 5938 | atributo | 11,501.00 a 1,066,825,105.00 | 0.02% | PIB municipal a precos correntes. |
| `pib_per_capita` | continuo | R$/hab | derivado | atributo | 3,081.72 a 920,828.36 | 0.02% | 1000 * pib_mil_reais / populacao. |
| `vab_total` | continuo | R$ mil | IBGE SIDRA 5938 | atributo | -227,726.00 a 660,796,712.00 | 20.01% | Valor adicionado bruto total. Redundante com o PIB (rho = 1,00). |
| `pct_vab_agropecuaria` | continuo | proporcao | derivado | atributo | -0.42 a 0.93 | 20.01% | Participacao da agropecuaria no VAB. Ausente em 2022-2023. |
| `pct_vab_industria` | continuo | proporcao | derivado | atributo | -1.55 a 2.10 | 20.01% | Participacao da industria no VAB. Ausente em 2022-2023. |
| `pct_vab_servicos` | continuo | proporcao | derivado | atributo | -0.42 a 2.24 | 20.01% | Participacao dos servicos (exclusive adm publica). Ausente em 2022-2023. |
| `pct_vab_adm_publica` | continuo | proporcao | derivado | atributo | -0.26 a 0.89 | 20.01% | Participacao da administracao publica. Ausente em 2022-2023. |
| `pct_esgoto_rede` | continuo | % | IBGE SIDRA 6805 (Censo 2022) | atributo | 0.03 a 99.95 | 0.47% | Domicilios com esgotamento por rede geral ou fossa ligada a rede. CONSTANTE no painel -- o Censo e foto unica. |
| `pct_agua_rede` | continuo | % | IBGE SIDRA 6803 (Censo 2022) | atributo | 0.25 a 100.00 | 0.16% | Domicilios com ligacao a rede geral de agua e que a utilizam. Constante no painel. |
| `pct_lixo_coletado` | continuo | % | IBGE SIDRA 6892 (Censo 2022) | atributo | 1.68 a 100.00 | 0.02% | Domicilios com lixo coletado. Constante no painel. |
| `estab_total` | discreto | unidades | CNES | atributo | 0.00 a 21,949.00 | 0.00% | Estabelecimentos de saude de todos os tipos. |
| `estab_atencao_basica` | discreto | unidades | CNES | atributo | 0.00 a 586.00 | 0.00% | Posto de saude + UBS + Unidade de Saude da Familia. |
| `estab_hospital` | discreto | unidades | CNES | VAZAMENTO Etapa 1 | 0.00 a 249.00 | 0.00% | Hospital geral + especializado. |
| `estab_urgencia` | discreto | unidades | CNES | atributo | 0.00 a 63.00 | 0.00% | Pronto socorro, pronto atendimento e unidade mista. |
| `estab_apoio_diagnose` | discreto | unidades | CNES | atributo | 0.00 a 998.00 | 0.00% | Unidade de apoio a diagnose e terapia (SADT isolado). |
| `estab_caps` | discreto | unidades | CNES | atributo | 0.00 a 106.00 | 0.00% | Centro de Atencao Psicossocial. |
| `estab_ab_por_10mil` | continuo | unid/10 mil hab | derivado | atributo | 0.00 a 40.16 | 0.02% | Densidade de atencao basica. |
| `equipes_esf` | discreto | equipes | CNES | atributo | 0.00 a 1,677.00 | 0.00% | Equipes de Saude da Familia cadastradas, incluindo ribeirinha e fluvial. |
| `equipes_ab_outras` | discreto | equipes | CNES | atributo | 0.00 a 443.00 | 0.00% | Equipes de Atencao Basica que nao sao ESF (modelo alternativo). |
| `cobertura_esf` | continuo | proporcao | derivado | atributo | 0.00 a 1.00 | 0.02% | PROXY: min(1, equipes_esf * 3.450 / populacao). Nao e o indicador oficial -- o CNES conta equipes cadastradas, o e-Gestor conta homologadas. Saturado: 91,6% em 2023, correlacao ~0 com taxa_icsap. |
| `equipes_ab_por_10mil` | continuo | equipes/10 mil hab | derivado | atributo | 0.00 a 28.49 | 0.02% | Densidade total de equipes de atencao primaria. |
| `equip_total` | discreto | equipamentos | CNES | atributo | 0.00 a 210,480.00 | 0.00% | Equipamentos em uso, todos os grupos. |
| `equip_imagem` | discreto | equipamentos | CNES | atributo | 0.00 a 13,867.00 | 0.00% | Equipamentos de diagnostico por imagem (raio-X, tomografo, mamografo). |
| `equip_manut_vida` | discreto | equipamentos | CNES | VAZAMENTO Etapa 1 | 0.00 a 108,556.00 | 0.00% | Equipamentos de manutencao da vida (respirador, monitor). Praticamente so existem dentro de UTI. |
| `equip_imagem_por_10mil` | continuo | equip/10 mil hab | derivado | atributo | 0.00 a 71.21 | 0.02% | Densidade de diagnostico por imagem. |
| `leitos_internacao` | discreto | leitos | CNES | VAZAMENTO Etapa 1 | 0.00 a 30,293.00 | 0.00% | Leitos de internacao existentes. |
| `leitos_internacao_sus` | discreto | leitos | CNES | VAZAMENTO Etapa 1 | 0.00 a 15,997.00 | 0.00% | Leitos de internacao disponiveis ao SUS. |
| `leitos_por_mil_hab` | continuo | leitos/mil hab | derivado | VAZAMENTO Etapa 1 | 0.00 a 32.10 | 0.02% | Oferta hospitalar normalizada. |
| `leitos_sus_por_mil_hab` | continuo | leitos/mil hab | derivado | VAZAMENTO Etapa 1 | 0.00 a 29.26 | 0.02% | Oferta hospitalar SUS normalizada. |
| `leitos_uti` | discreto | leitos | CNES | ALVO 1 (origem) | 0.00 a 7,427.00 | 0.00% | Leitos de UTI. tem_uti = (leitos_uti > 0). |
| `leitos_complementares` | discreto | leitos | CNES | VAZAMENTO Etapa 1 | 0.00 a 8,885.00 | 0.00% | UTI + unidades intermediarias + isolamento. |
| `lat` | continuo | graus | IBGE Malhas | auxiliar | -33.65 a 4.68 | 0.02% | Latitude do centroide de area do municipio. |
| `lon` | continuo | graus | IBGE Malhas | auxiliar | -73.44 a -34.84 | 0.02% | Longitude do centroide de area do municipio. |
| `dist_uti_km` | continuo | km | derivado (IBGE Malhas + CNES) | atributo | 0.00 a 864.71 | 0.02% | Distancia haversine ate o municipio mais proximo com leito de UTI; 0 se o proprio tem. UNICO atributo nao correlacionado com tamanho (rho = 0,078 com populacao). |
| `dist_uti_externa_km` | continuo | km | derivado | atributo | 1.29 a 864.71 | 0.02% | Idem, ignorando o proprio municipio: 'se a UTI daqui fechar, para onde vai o paciente?'. |
| `dist_hospital_km` | continuo | km | derivado | VAZAMENTO Etapa 1 | 0.00 a 109.79 | 0.02% | Distancia ate o leito de internacao mais proximo. Quase determina tem_uti. |
| `internacoes_total` | discreto | internacoes | SIH por residencia | ALVO 2 (denominador) | 0.00 a 608,371.00 | 0.00% | Internacoes SUS de residentes no ano. |
| `internacoes_icsap` | discreto | internacoes | SIH por residencia | ALVO 2 (numerador) | 0.00 a 112,543.00 | 0.00% | Internacoes sensiveis a atencao primaria (aproximadas). |
| `tx_internacao_por_mil` | continuo | intern/mil hab | derivado | VAZAMENTO Etapa 1 | 1.15 a 347.61 | 0.02% | Taxa geral de internacao. |
| `intern_menor5_total` | discreto | internacoes | SIH por residencia | ALVO 2b (denominador) | 0.00 a 67,520.00 | 0.00% | Internacoes de residentes menores de 5 anos. |
| `intern_menor5_icsap` | discreto | internacoes | SIH por residencia | ALVO 2b (numerador) | 0.00 a 28,180.00 | 0.00% | ICSAP em menores de 5 anos. |
| `intern_idoso_total` | discreto | internacoes | SIH por residencia | ALVO 2c (denominador) | 0.00 a 166,098.00 | 0.00% | Internacoes de residentes com 60 anos ou mais. |
| `intern_idoso_icsap` | discreto | internacoes | SIH por residencia | ALVO 2c (numerador) | 0.00 a 42,646.00 | 0.00% | ICSAP em idosos. |
| `nascidos_vivos` | discreto | nascimentos | SINASC | atributo | 0.00 a 176,313.00 | 0.00% | Nascidos vivos por residencia da mae. |
| `nasc_prenatal_7mais` | discreto | nascimentos | SINASC | atributo | 0.00 a 136,755.00 | 0.00% | Nascimentos com 7 ou mais consultas de pre-natal. |
| `nasc_prenatal_nenhuma` | discreto | nascimentos | SINASC | atributo | 0.00 a 4,783.00 | 0.00% | Nascimentos sem nenhuma consulta de pre-natal. |
| `nasc_prenatal_ignorado` | discreto | nascimentos | SINASC | atributo | 0.00 a 2,457.00 | 0.00% | Numero de consultas nao informado. |
| `pct_prenatal_7mais` | continuo | proporcao | derivado | atributo | 0.01 a 1.00 | 0.02% | Indicador de acesso a atencao primaria. |
| `obitos_menor1` | discreto | obitos | SIM | atributo | 0.00 a 1,954.00 | 0.00% | Obitos de menores de 1 ano por residencia. |
| `tx_mort_infantil` | continuo | por mil nasc. | derivado | atributo | 0.00 a 285.71 | 0.02% | Mortalidade infantil. Instavel onde ha poucos nascimentos. |
| `tem_uti` | binario | 0/1 | derivado do CNES | **ALVO 1** | 0.00 a 1.00 | 0.00% | 1 se o municipio tem ao menos um leito de UTI. |
| `taxa_icsap` | continuo | proporcao | derivado do SIH | **ALVO 2** | 0.00 a 0.81 | 0.02% | internacoes_icsap / internacoes_total. |
| `taxa_icsap_menor5` | continuo | proporcao | derivado do SIH | **ALVO 2b** | 0.00 a 1.00 | 0.16% | ICSAP infantil. E a taxa mais sensivel a qualidade da atencao primaria. |
| `taxa_icsap_idoso` | continuo | proporcao | derivado do SIH | **ALVO 2c** | 0.00 a 1.00 | 0.02% | ICSAP em idosos: diabetes, hipertensao e insuficiencia cardiaca. |
| `icsap_por_10mil` | continuo | intern/10 mil hab | derivado do SIH | VAZAMENTO Etapa 2 | 0.00 a 2,390.48 | 0.02% | Versao populacional do alvo 2. |
| `vazio_assistencial` | binario | 0/1 | derivado | atributo | 0.00 a 1.00 | 0.00% | 1 quando tem_uti=0 E populacao>=20 mil E dist_uti_km>=100. Interseccao entre 'porte justifica o servico' e 'longe demais para alcancar'. |
