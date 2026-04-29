import math
import pandas as pd
from dataclasses import dataclass
from django.db import transaction

import logging

from apps.unidades.models.unidades import (
    Unidade,
    TipoUnidadeChoices,
    TipoGestaoChoices,
)

logger = logging.getLogger(__name__)

DIR_EDUC = "DIR EDUC"

COLUNAS_VALIDAS = [
    "CODESC", "TIPOESC", "NOMESC",
    "SIGLA", "DIRETORIA", "CODDRE",
    "SITUACAO", "REDE"
]

VALID_TIPOS = {c[0] for c in TipoUnidadeChoices.choices}
VALID_TIPOS.add(DIR_EDUC)

VALID_REDES = {"DIR", "CON"}


def build_error(type_, message, **extra):
    return {
        "type": type_,
        "message": message,
        **extra
    }

def clean_nan(obj):
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    return obj

@dataclass
class UnidadeImportDTO:
    codigo_eol: str
    nome: str
    tipo_unidade: str
    rede: object
    sigla: str
    ativa: bool
    dre: str | None

    def validate(self):
        if not self.codigo_eol:
            raise ValueError("CODESC obrigatório")

        if len(self.codigo_eol) != 6:
            raise ValueError("codigo_eol deve ter 6 dígitos")

        if not self.nome:
            raise ValueError("nome obrigatório")

        if not self.tipo_unidade:
            raise ValueError("tipo_unidade obrigatório")

        if self.sigla is None:
            self.sigla = ""

        return self

def validar_dados_detalhado(rows):
    logger.info("Iniciando validação detalhada dos dados do arquivo de carga de unidades")

    erros = []

    for i, row in enumerate(rows):
        linha = i + 1

        tipo = str(row.get("TIPOESC") or "").strip()
        rede = str(row.get("REDE") or "").strip()

        if tipo not in VALID_TIPOS:
            erros.append(build_error(
                type_="validacao_tipo",
                message="Tipo de unidade inválido",
                linha=linha,
                campo="TIPOESC",
                valor=tipo
            ))

        if tipo != DIR_EDUC and rede not in VALID_REDES:
            erros.append(build_error(
                type_="validacao_rede",
                message="Valor inválido para REDE",
                linha=linha,
                campo="REDE",
                valor=rede
            ))

    return erros


def validar_estrutura(df):
    logger.info("Validando estrutura do arquivo")
    return [col for col in COLUNAS_VALIDAS if col not in df.columns]

class UnidadeImportNormalizer:

    @staticmethod
    def normalize(row):
        tipo_original = str(row.get("TIPOESC") or "").strip()
        rede_original = str(row.get("REDE") or "").strip()

        codigo = row.get("CODESC")
        if not codigo:
            raise ValueError("CODESC obrigatório")

        codigo_eol = str(codigo).zfill(6)

        if tipo_original == DIR_EDUC:
            tipo_unidade = TipoUnidadeChoices.DRE
        else:
            tipo_unidade = tipo_original

        if tipo_unidade != TipoUnidadeChoices.DRE and tipo_unidade not in VALID_TIPOS:
            raise ValueError(f"Tipo de unidade inválido: {tipo_unidade}")

        if tipo_original == DIR_EDUC:
            rede = TipoGestaoChoices.DIRETA
        else:
            rede_map = {
                "DIR": TipoGestaoChoices.DIRETA,
                "CON": TipoGestaoChoices.INDIRETA,
            }

            if rede_original not in rede_map:
                raise ValueError(f"Valor inválido para REDE: {rede_original}")

            rede = rede_map[rede_original]

        dre_raw = row.get("CODDRE")
        dre = str(dre_raw).zfill(6) if dre_raw else None

        return {
            "codigo_eol": codigo_eol,
            "nome": row.get("NOMESC"),
            "tipo_unidade": tipo_unidade,
            "rede": rede,
            "sigla": row.get("SIGLA") or "",
            "dre": dre,
            "ativa": True,
        }

def parse_file(file):
    logger.info("Iniciando parsing do arquivo de carga de unidades")

    df = pd.read_excel(file, dtype=str, engine="openpyxl")

    erros_cols = validar_estrutura(df)
    if erros_cols:
        return {
            "success": False,
            "error": build_error(
                type_="estrutura_arquivo",
                message="Colunas obrigatórias ausentes no arquivo",
                faltantes=erros_cols,
                recebidas=list(df.columns)
            )
        }

    df = df.replace(r'^\s*$', None, regex=True)
    df = df.where(pd.notnull(df), None)
    df = df[COLUNAS_VALIDAS]

    rows = df.to_dict(orient="records")

    erros = validar_dados_detalhado(rows)

    return {
        "success": True,
        "rows": rows,
        "errors": erros,
        "valid": len(erros) == 0
    }

class CargaUnidadeService:

    @staticmethod
    def preview(file):
        result = parse_file(file)

        if not result["success"]:
            return {"success": False, "error": result["error"]}

        if not result["valid"]:
            return CargaUnidadeService._erro_validacao(result["errors"])

        return {
            "success": True,
            "data": {
                "total": len(result["rows"]),
                "erros": result["errors"],
                "preview": clean_nan(result["rows"][:10])
            }
        }

    @staticmethod
    def confirm(file):
        result = parse_file(file)

        if not result["success"]:
            return {"success": False, "error": result["error"]}

        if not result["valid"]:
            return CargaUnidadeService._erro_validacao(result["errors"])

        return CargaUnidadeService.process_rows(result["rows"])

    @staticmethod
    def _erro_validacao(errors):
        return {
            "success": False,
            "error": build_error(
                type_="validacao_arquivo",
                message="Existem inconsistências no arquivo",
                detalhes=errors
            )
        }

    @staticmethod
    def process_rows(rows):
        logger.info("Iniciando processamento das linhas do arquivo de carga de unidades")

        erros = validar_dados_detalhado(rows)
        if erros:
            return {
                "success": False,
                "error": build_error(
                    type_="validacao_dados",
                    message="Erros de validação nos dados do arquivo",
                    detalhes=erros
                )
            }

        parsed = CargaUnidadeService._normalizar(rows)

        if isinstance(parsed, dict):
            return parsed

        dres, unidades = CargaUnidadeService._separar(parsed)

        existentes = CargaUnidadeService._buscar_existentes(parsed)
        dre_map = CargaUnidadeService._build_dre_map()

        return CargaUnidadeService._persistir(
            dres, unidades, existentes, dre_map, parsed
        )

    @staticmethod
    def _normalizar(rows):
        logger.info("Iniciando normalização dos dados do arquivo de carga de unidades")

        parsed = []

        for i, row in enumerate(rows):
            try:
                data = UnidadeImportNormalizer.normalize(row)

                dto = UnidadeImportDTO(
                    codigo_eol=data["codigo_eol"],
                    nome=data["nome"],
                    tipo_unidade=data["tipo_unidade"],
                    rede=data["rede"],
                    sigla=data["sigla"],
                    ativa=data["ativa"],
                    dre=data["dre"],
                ).validate()

                obj = Unidade(
                    codigo_eol=dto.codigo_eol,
                    nome=dto.nome,
                    tipo_unidade=dto.tipo_unidade,
                    rede=dto.rede,
                    sigla=dto.sigla,
                    ativa=dto.ativa,
                )

                parsed.append((obj, data, i + 1))

            except Exception as e:
                return {
                    "success": False,
                    "error": build_error(
                        type_="erro_normalizacao",
                        message=str(e)
                    )
                }

        return parsed

    @staticmethod
    def _separar(parsed):
        dres = []
        unidades = []

        logger.info("Iniciando separação das DREs e unidades")
        for obj, data, linha in parsed:
            if data["tipo_unidade"] == TipoUnidadeChoices.DRE:
                dres.append(obj)
            else:
                unidades.append((obj, data, linha))

        return dres, unidades

    @staticmethod
    def _buscar_existentes(parsed):
        codigos = [o.codigo_eol for o, _, _ in parsed]

        logger.info("Buscando unidades existentes no DB")
        return set(
            Unidade.objects.filter(
                codigo_eol__in=codigos
            ).values_list("codigo_eol", flat=True)
        )

    @staticmethod
    def _build_dre_map():
        logger.info("Construindo mapa de DREs")
        return {
            u.codigo_eol: u.codigo_eol
            for u in Unidade.objects.filter(
                tipo_unidade=TipoUnidadeChoices.DRE
            )
        }

    @staticmethod
    def _persistir(dres, unidades, existentes, dre_map, parsed):
        logger.info("Iniciando persistência dos dados no DB")

        criados = []
        atualizados = []

        with transaction.atomic():

            logger.info("Persistindo DREs")
            Unidade.objects.bulk_create(
                dres,
                update_conflicts=True,
                unique_fields=["codigo_eol"],
                update_fields=["nome", "tipo_unidade", "rede", "sigla", "ativa"],
                batch_size=1000
            )

            for d in dres:
                if d.codigo_eol in existentes:
                    atualizados.append(d)
                else:
                    criados.append(d)

            for d in dres:
                dre_map[d.codigo_eol] = d.codigo_eol

            final_unidades = []

            logger.info("Persistindo unidades")
            for obj, data, linha in unidades:

                if data["dre"] and data["dre"] not in dre_map:
                    return {
                        "success": False,
                        "error": build_error(
                            type_="dre_nao_encontrada",
                            message=f"DRE não encontrada: {data['dre']}",
                            dre=data["dre"],
                            linha=linha
                        )
                    }

                if data["dre"]:
                    obj.dre_id = data["dre"]

                if obj.codigo_eol in existentes:
                    atualizados.append(obj)
                else:
                    criados.append(obj)

                final_unidades.append(obj)

            Unidade.objects.bulk_create(
                final_unidades,
                update_conflicts=True,
                unique_fields=["codigo_eol"],
                update_fields=[
                    "nome", "tipo_unidade", "rede",
                    "sigla", "ativa", "dre"
                ],
                batch_size=1000
            )

        return {
            "success": True,
            "data": {
                "status": "importação realizada com sucesso",
                "criados": len(criados),
                "atualizados": len(atualizados),
                "total": len(parsed)
            }
        }