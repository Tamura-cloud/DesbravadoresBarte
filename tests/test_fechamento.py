"""fechar(): lê as entradas reais, roda módulos sintéticos, grava e valida. Sem valores de referência."""

from decimal import Decimal
from pathlib import Path

import pytest

from tarvo.bancos import bancos
from tarvo.checkout import checkout
from tarvo.fechamento import MODULOS, Entradas, fechar
from tarvo.remessa import remessa
from tarvo.saida import ARQUIVOS, PENDENCIAS, ErroSaida, ItemSaida, validar_saida

ENTRADA = Path(__file__).resolve().parents[1] / "dados" / "2026-09"


def test_sem_modulos_grava_os_6_arquivos_validos(tmp_path):
    resultado = fechar(ENTRADA, tmp_path, "2026-09", modulos=[])
    assert resultado.itens == 0
    assert set(resultado.arquivos_saida) == {e.nome for e in ARQUIVOS}
    assert len(resultado.arquivos_entrada) == 6
    assert validar_saida(tmp_path) == []


def test_grava_direto_na_pasta_de_saida_sem_subpasta_da_competencia(tmp_path):
    resultado = fechar(ENTRADA, tmp_path, "2026-09")
    assert resultado.arquivos_saida == {e.nome: tmp_path / e.nome for e in ARQUIVOS}
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(e.nome for e in ARQUIVOS)
    assert not any(p.is_dir() for p in tmp_path.iterdir())


def test_modulos_registrados():
    assert MODULOS == [checkout, remessa, bancos]


def test_modulo_recebe_entradas_e_seus_itens_sao_gravados(tmp_path):
    recebidas = []

    def modulo(entradas):
        recebidas.append(entradas)
        yield ItemSaida("PEN-TESTE-1", PENDENCIAS.nome,
                        {"tipo": "TESTE", "ref_origem": "R1", "motivo": "sintético", "quem_decide": "Ninguém"},
                        Decimal("1.00"), [("x.csv", "R1", Decimal("1.00"))])

    resultado = fechar(ENTRADA, tmp_path, "2026-09", modulos=[modulo])
    assert resultado.itens == 1
    assert isinstance(recebidas[0], Entradas) and recebidas[0].competencia == "2026-09"
    assert "PEN-TESTE-1" in (tmp_path / PENDENCIAS.nome).read_text(encoding="utf-8")


def test_ids_repetidos_entre_modulos_falham(tmp_path):
    def modulo(_):
        return [ItemSaida("PEN-X", PENDENCIAS.nome, {}, Decimal("0.00"), [])]

    with pytest.raises(ErroSaida, match="duplicado"):
        fechar(ENTRADA, tmp_path, "2026-09", modulos=[modulo, modulo])


@pytest.mark.parametrize("competencia", ["2026-9", "2026-13", "09/2026", ""])
def test_competencia_invalida(tmp_path, competencia):
    with pytest.raises(ValueError, match="AAAA-MM"):
        fechar(ENTRADA, tmp_path, competencia, modulos=[])
