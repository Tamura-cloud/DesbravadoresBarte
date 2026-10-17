from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from tarvo.cli import localizar_pela_config
from tarvo.leitores.meridiano import COLUNAS, ler_meridiano

ENTRADA = Path(__file__).resolve().parents[1] / "dados" / "2026-09"


@pytest.fixture(scope="module")
def meridiano():
    caminho = localizar_pela_config(ENTRADA)["meridiano"]
    return ler_meridiano(caminho)


def _memo(df, fitid):
    return df.loc[df["ref_origem"] == fitid, "memo"].item()


def test_colunas_e_quantidade(meridiano):
    df, _ = meridiano
    assert list(df.columns) == COLUNAS
    assert len(df) == 100


def test_fitid_unico(meridiano):
    df, _ = meridiano
    assert df["ref_origem"].is_unique


def test_soma_dos_valores(meridiano):
    df, _ = meridiano
    assert sum(df["valor"]) == Decimal("1116335.23")


def test_tipos(meridiano):
    df, _ = meridiano
    assert all(type(d) is date for d in df["data"])
    assert all(isinstance(v, Decimal) and v.as_tuple().exponent == -2 for v in df["valor"])
    primeiro = df.iloc[0]
    assert primeiro["ref_origem"] == "MRD2026090003"
    assert primeiro["data"] == date(2026, 9, 1)
    assert primeiro["valor"] == Decimal("207215.87")
    assert primeiro["tipo"] == "CREDIT"
    assert primeiro["checknum"] == "288643"


def test_metadados(meridiano):
    _, meta = meridiano
    assert meta["bankid"] == "0477"
    assert meta["branchid"] == "0091"
    assert meta["acctid"] == "90233-5"
    assert meta["dtstart"] == date(2026, 9, 1)
    assert meta["dtend"] == date(2026, 9, 30)
    assert meta["saldo_ledger"] == Decimal("1320453.26")
    assert meta["charset"] == "cp1252"


def test_acentos_cp1252(meridiano):
    df, _ = meridiano
    assert _memo(df, "MRD2026090008") == "PIX RECEB MUNDO ABERTO INTERCÂMBIO"
    assert "AÉREA" in _memo(df, "MRD2026090082")
    assert not df["memo"].str.contains("�").any()


def test_memo_sem_espacos_nas_pontas_e_memo_norm(meridiano):
    df, _ = meridiano
    assert all(m == m.strip() for m in df["memo"])
    assert _memo(df, "MRD2026090003") == "PIX RECEB LISBOA CURSOS E VIAGENS"
    norm = df.loc[df["ref_origem"] == "MRD2026090008", "memo_norm"].item()
    assert norm == "PIX RECEB MUNDO ABERTO INTERCAMBIO"


OFX_SINTETICO = (
    "OFXHEADER:100\r\nDATA:OFXSGML\r\nVERSION:102\r\n{charset}\r\n\r\n"
    "<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS>\r\n"
    "<BANKACCTFROM>\r\n<BANKID>1\r\n<BRANCHID>2\r\n<ACCTID>3\r\n</BANKACCTFROM>\r\n"
    "<BANKTRANLIST>\r\n<DTSTART>20260901\r\n<DTEND>20260930\r\n"
    "<STMTTRN>\r\n<TRNTYPE>DEBIT\r\n<DTPOSTED>20260915120000[-3:BRT]\r\n<TRNAMT>-10.5\r\n"
    "<FITID>A1\r\n<MEMO>  TARIFA CÂMBIO  \r\n</STMTTRN>\r\n"
    "</BANKTRANLIST>\r\n<LEDGERBAL>\r\n<BALAMT>99.90\r\n</LEDGERBAL>\r\n"
    "</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>\r\n"
)


def _grava(tmp_path, charset_linha, encoding):
    arquivo = tmp_path / "extrato.ofx"
    arquivo.write_bytes(OFX_SINTETICO.format(charset=charset_linha).encode(encoding))
    return arquivo


@pytest.mark.parametrize("encoding", ["utf-8", "cp1252"])
def test_sem_charset_tenta_utf8_e_cai_para_cp1252(tmp_path, encoding):
    df, meta = ler_meridiano(_grava(tmp_path, "COMPRESSION:NONE", encoding))
    assert meta["charset"] == encoding
    assert df.iloc[0]["memo"] == "TARIFA CÂMBIO"
    assert df.iloc[0]["valor"] == Decimal("-10.50")
    assert df.iloc[0]["checknum"] is None
    assert meta["saldo_ledger"] == Decimal("99.90")


def test_charset_declarado_que_nao_decodifica_gera_erro(tmp_path):
    arquivo = tmp_path / "extrato.ofx"
    arquivo.write_bytes(OFX_SINTETICO.format(charset="CHARSET:UTF-8").encode("cp1252"))
    with pytest.raises(UnicodeDecodeError):
        ler_meridiano(arquivo)


def test_fitid_repetido_gera_erro(tmp_path):
    bloco = "<STMTTRN>\r\n<TRNTYPE>DEBIT\r\n<DTPOSTED>20260915\r\n<TRNAMT>-1.00\r\n<FITID>A1\r\n</STMTTRN>\r\n"
    texto = OFX_SINTETICO.format(charset="CHARSET:1252").replace("</BANKTRANLIST>", bloco + "</BANKTRANLIST>")
    arquivo = tmp_path / "extrato.ofx"
    arquivo.write_bytes(texto.encode("cp1252"))
    with pytest.raises(ValueError, match="FITID repetido"):
        ler_meridiano(arquivo)
