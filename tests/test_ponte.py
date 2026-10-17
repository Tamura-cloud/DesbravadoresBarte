import io
from datetime import date, datetime
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path

import openpyxl
import pytest

from tarvo.cli import CONFIG_PADRAO, carregar_padroes, localizar_arquivos
from tarvo.leitores.comum import dinheiro
from tarvo.leitores.ponte import ler_ponte

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "2026-09"

CABECALHO = [
    "Nº Operação", "Data Contratação", "Data Liquidação", "CNPJ Cliente", "Cliente", "Moeda",
    "Valor ME", "Taxa Cliente", "PTAX Ref.", "Valor R$", "Spread R$", "Spread %",
    "Spread Estimado R$ (D-1)", "IOF R$", "Status Compliance", "Observação",
]


@pytest.fixture(scope="module")
def setembro():
    eml = localizar_arquivos(ENTRADA, carregar_padroes(CONFIG_PADRAO))["ponte_eml"]
    return eml, *ler_ponte(eml)


# --- setembro (valores de referência) ---

def test_setembro_quantidade_de_linhas(setembro):
    _, df, meta = setembro
    assert len(df) == 233
    assert meta["total_operacoes_rodape"] == 233


def test_setembro_spread_total_fecha_com_rodape(setembro):
    _, df, meta = setembro
    assert meta["spread_total_rodape"] == Decimal("78073.59")
    assert sum(df["spread_brl"], Decimal("0")) == Decimal("78073.59")


def test_setembro_duplicata_mantida(setembro):
    _, df, _ = setembro
    assert (df["ref_origem"] == "PC-0926-0162").sum() == 2


def test_setembro_spreads_negativos(setembro):
    _, df, _ = setembro
    assert sum(1 for v in df["spread_brl"] if v < 0) == 4


def test_setembro_status_com_ressalva(setembro):
    _, df, _ = setembro
    assert (df["status_compliance"] == "APROVADO C/ RESSALVA").sum() == 16


def test_setembro_valor_brl_igual_valor_me_vezes_taxa(setembro):
    _, df, _ = setembro
    for r in df.itertuples():
        assert abs(r.valor_brl - dinheiro(r.valor_me * r.taxa_cliente)) <= Decimal("0.01"), r.ref_origem


def test_setembro_cnpj_14_digitos(setembro):
    _, df, _ = setembro
    assert all(isinstance(c, str) and len(c) == 14 and c.isdigit() for c in df["cnpj"])


def test_setembro_tipos_e_origem(setembro):
    eml, df, _ = setembro
    assert df["arquivo_origem"].str.startswith(eml.name + "#").all()
    assert df["arquivo_origem"].str.endswith(".xlsx").all()
    assert df["ref_origem"].str.len().gt(0).all()
    for c in ("data_contratacao", "data_liquidacao"):
        assert all(type(v) is date for v in df[c])
    for c in ("valor_me", "taxa_cliente", "ptax_ref", "valor_brl", "spread_brl", "spread_pct",
              "spread_estimado_d1_brl", "iof_brl"):
        assert all(isinstance(v, Decimal) for v in df[c]), c
    for c in ("valor_me", "valor_brl", "spread_brl", "spread_estimado_d1_brl", "iof_brl"):
        assert all(v.as_tuple().exponent == -2 for v in df[c]), c
    # spread_pct em pontos percentuais (a planilha traz fração ~0,015)
    assert all(Decimal("-10") < v < Decimal("10") for v in df["spread_pct"])
    assert df["spread_pct"].map(abs).max() > 1
    assert df["linha_planilha"].is_unique
    obs = list(df["observacao"])
    assert all(v is None or (isinstance(v, str) and v) for v in obs)
    assert sum(v is None for v in obs) == 228


def test_setembro_metadados(setembro):
    _, _, meta = setembro
    assert "pontecambio" in meta["remetente"]
    assert type(meta["data_email"]) is date
    assert meta["assunto"]
    assert "spread" in meta["corpo"]


# --- arquivo sintético: cabeçalho fora da linha 5, rodapé, CNPJ misto, nada gravado em disco ---

def _eml_sintetico(pasta: Path) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Operações"
    ws.append(["Relatório de teste"])
    ws.append(CABECALHO)  # linha 2
    ws.append(["OP-1", datetime(2030, 1, 2), datetime(2030, 1, 3), "11.222.333/0001-81", "CLIENTE Á",
               "USD", 100, 5.1234, 5.0, 512.34, 12.34, 0.0247, 10, 1.95, "APROVADO", None])
    ws.append(["OP-1", datetime(2030, 1, 2), datetime(2030, 1, 3), "1222333000181", "CLIENTE B",
               "EUR", 10.5, 6.0, 6.1, 63.0, -1.05, -0.0164, 0.5, 0.24, "APROVADO C/ RESSALVA", "  "])
    ws.append([None] * len(CABECALHO))
    ws.append(["Total de operações:", 2])
    ws.append(["Spread total R$:", 11.29])
    buf = io.BytesIO()
    wb.save(buf)

    msg = EmailMessage()
    msg["From"] = "Teste <teste@exemplo.com>"
    msg["To"] = "financeiro@exemplo.com"
    msg["Subject"] = "Relatório de teste"
    msg["Date"] = "Wed, 02 Jan 2030 08:00:00 -0300"
    msg.set_content("Corpo de teste.\n")
    msg.add_attachment(buf.getvalue(), maintype="application",
                       subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       filename="relatorio.xlsx")
    caminho = pasta / "teste.eml"
    with open(caminho, "wb") as f:
        f.write(msg.as_bytes())
    return caminho


def test_sintetico(tmp_path):
    eml = _eml_sintetico(tmp_path)
    antes = sorted(tmp_path.iterdir())

    df, meta = ler_ponte(eml)

    assert sorted(tmp_path.iterdir()) == antes  # anexo lido em memória
    assert list(df["ref_origem"]) == ["OP-1", "OP-1"]
    assert list(df["linha_planilha"]) == [3, 4]
    assert set(df["arquivo_origem"]) == {"teste.eml#relatorio.xlsx"}
    assert list(df["cnpj"]) == ["11222333000181", "01222333000181"]
    assert list(df["cliente"]) == ["CLIENTE Á", "CLIENTE B"]
    assert list(df["spread_pct"]) == [Decimal("2.47"), Decimal("-1.64")]
    assert list(df["spread_brl"]) == [Decimal("12.34"), Decimal("-1.05")]
    assert df["valor_me"][0] == Decimal("100.00")
    assert df["taxa_cliente"][0] == Decimal("5.1234")
    assert df["data_contratacao"][0] == date(2030, 1, 2)
    assert list(df["observacao"]) == [None, None]

    assert meta["total_operacoes_rodape"] == 2
    assert meta["spread_total_rodape"] == Decimal("11.29")
    assert meta["remetente"] == "Teste <teste@exemplo.com>"
    assert meta["assunto"] == "Relatório de teste"
    assert meta["data_email"] == date(2030, 1, 2)
    assert meta["corpo"].strip() == "Corpo de teste."


def test_sem_cabecalho_falha(tmp_path):
    wb = openpyxl.Workbook()
    wb.active.title = "Operações"
    wb.active.append(["nada aqui"])
    buf = io.BytesIO()
    wb.save(buf)
    msg = EmailMessage()
    msg.set_content("x")
    msg.add_attachment(buf.getvalue(), maintype="application", subtype="octet-stream", filename="a.xlsx")
    eml = tmp_path / "x.eml"
    with open(eml, "wb") as f:
        f.write(msg.as_bytes())
    with pytest.raises(ValueError, match="Nº Operação"):
        ler_ponte(eml)
