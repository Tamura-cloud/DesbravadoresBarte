"""Orquestra o fechamento: lê as entradas, junta os itens dos módulos registrados, grava e valida a saída."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from tarvo.bancos import bancos
from tarvo.checkout import checkout
from tarvo.cli import CONFIG_PADRAO, arquivos_ignorados, carregar_padroes, localizar_pela_config
from tarvo.contestacao import carregar_config as carregar_config_contestacao
from tarvo.contestacao import gerar_contestacoes, pasta_padrao
from tarvo.leitores.aurora import ler_aurora
from tarvo.leitores.meridiano import ler_meridiano
from tarvo.leitores.orbe import Repetida, ler_orbe_arquivos
from tarvo.leitores.plano_contas import ler_plano
from tarvo.leitores.ponte import ler_ponte
from tarvo.leitores.taxas import ler_taxas
from tarvo.remessa import remessa
from tarvo.saida import ItemSaida, gravar_saida, validar_saida

RE_COMPETENCIA = re.compile(r"[0-9]{4}-(0[1-9]|1[0-2])")
PREFIXO_PREPARO = ".tarvo-fechamento-"  # pasta temporária ao lado da saída, apagada ao fim de toda execução


@dataclass(frozen=True)
class Entradas:
    """Tudo o que os leitores devolveram, entregue a cada módulo."""

    competencia: str
    arquivos: dict[str, Path]
    orbe: pd.DataFrame
    taxas: pd.DataFrame
    ponte: pd.DataFrame
    ponte_rodape: dict
    plano_contas: pd.DataFrame
    aurora: pd.DataFrame
    aurora_meta: dict
    meridiano: pd.DataFrame
    meridiano_meta: dict
    usar_ia: bool = True  # opção da execução: False com --sem-ia (fallback de IA dos extratos, P14)
    orbe_repetidas: tuple[Repetida, ...] = ()  # id_transacao igual em dois arquivos da Orbe, contado uma vez (P27)


Modulo = Callable[[Entradas], Iterable[ItemSaida]]

# Módulos que geram itens de saída. Cada um recebe as Entradas e devolve ItemSaida.
MODULOS: list[Modulo] = [checkout, remessa, bancos]


class ErroFechamento(Exception):
    """A saída gravada não passou em validar_saida."""

    def __init__(self, problemas: list[str]):
        self.problemas = list(problemas)
        super().__init__("\n".join(self.problemas))


@dataclass(frozen=True)
class ResultadoFechamento:
    arquivos_entrada: dict[str, Path]
    arquivos_saida: dict[str, Path]
    itens: int
    arquivos_contestacao: dict[str, Path] = field(default_factory=dict)  # R29; vazio com contestacoes=False
    arquivos_ignorados: list[tuple[Path, str]] = field(default_factory=list)  # na entrada, não lidos (só aviso)


def ler_entradas(entrada, competencia: str, config=CONFIG_PADRAO, usar_ia: bool = True) -> Entradas:
    arquivos = localizar_pela_config(entrada, config)
    orbe, orbe_repetidas = ler_orbe_arquivos(arquivos["orbe"])  # relatório e ajustes da Orbe (O05)
    ponte, ponte_rodape = ler_ponte(arquivos["ponte_eml"])
    aurora, aurora_meta = ler_aurora(arquivos["aurora"])
    meridiano, meridiano_meta = ler_meridiano(arquivos["meridiano"])
    return Entradas(
        competencia=competencia,
        arquivos=arquivos,
        orbe=orbe,
        taxas=ler_taxas(arquivos["taxas"]),
        ponte=ponte,
        ponte_rodape=ponte_rodape,
        plano_contas=ler_plano(arquivos["plano_de_contas"]),
        aurora=aurora,
        aurora_meta=aurora_meta,
        meridiano=meridiano,
        meridiano_meta=meridiano_meta,
        usar_ia=usar_ia,
        orbe_repetidas=tuple(orbe_repetidas),
    )


def _publicar(preparados: dict[str, Path], destino: Path) -> dict[str, Path]:
    """Põe cada arquivo preparado no destino, por cima do anterior (os.replace: troca atômica por arquivo)."""
    destino.mkdir(parents=True, exist_ok=True)
    publicados = {}
    for nome, origem in preparados.items():
        alvo = destino / nome
        try:
            os.replace(origem, alvo)
        except OSError:  # outra unidade de disco: os.replace não atravessa volumes
            shutil.copyfile(origem, alvo)
        publicados[nome] = alvo
    return publicados


def fechar(entrada, saida, competencia: str, *, config=CONFIG_PADRAO,
           modulos: Iterable[Modulo] | None = None, usar_ia: bool = True,
           contestacoes: Path | str | bool | None = None) -> ResultadoFechamento:
    """Lê as entradas, roda os módulos, valida os 6 CSVs e só então os grava em saida.

    Tudo é gravado antes numa pasta temporária ao lado de saida e validado lá (validar_saida). Se a validação
    falhar (ErroFechamento) ou qualquer passo der erro, saida e a pasta de contestações ficam como estavam.
    usar_ia=False força o fluxo sem IA nos extratos (P09 em vez de P14).
    Os rascunhos de contestação (R29) vão para uma pasta irmã de saida (config/contestacao.yaml);
    contestacoes=<pasta> escolhe outra, contestacoes=False não grava.
    """
    if not isinstance(competencia, str) or not RE_COMPETENCIA.fullmatch(competencia):
        raise ValueError(f"competência deve ser AAAA-MM, veio {competencia!r}")
    entradas = ler_entradas(entrada, competencia, config, usar_ia)
    ignorados = arquivos_ignorados(Path(entrada), carregar_padroes(Path(config)))
    itens: list[ItemSaida] = []
    for modulo in MODULOS if modulos is None else modulos:
        itens.extend(modulo(entradas))

    saida = Path(saida).resolve()
    saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=PREFIXO_PREPARO, dir=saida.parent) as preparo:
        preparo = Path(preparo)
        preparados = gravar_saida(preparo / "saida", itens)
        problemas = validar_saida(preparo / "saida")
        if problemas:
            raise ErroFechamento(problemas)
        rascunhos_preparados, destino_contestacoes = {}, None
        if contestacoes is not False:
            cfg = carregar_config_contestacao()
            destino_contestacoes = Path(contestacoes or pasta_padrao(saida, cfg)).resolve()
            rascunhos_preparados = gerar_contestacoes(itens, entradas, preparo / "contestacoes", cfg)
        gravados = _publicar(preparados, saida)
        rascunhos = _publicar(rascunhos_preparados, destino_contestacoes) if destino_contestacoes else {}
    return ResultadoFechamento(entradas.arquivos, gravados, len(itens), rascunhos, ignorados)
