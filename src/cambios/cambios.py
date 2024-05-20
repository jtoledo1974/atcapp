"""Business logic for the cambios app."""

from __future__ import annotations

from .models import User

BASIC_SHIFTS = ["M", "T", "N", "im", "it", "in"]

SHIFT_TYPES = {
    "SUP": "SUPERVISIÓN",
    "A1": "TRABAJO EN FRECUENCIA",
    "A2": "INSTRUCTOR IMPARTIENDO OJT O SIENDO EVALUADO",
    "A2e": "INSTRUCTOR EVALUANDO OJT",
    "A3": "CONTROLADOR EN OJT (FPT) I EVALUANDO",
    "A4": "CONTROLADOR SIENDO EVALUADO EN COMPETENCIA OPERACIONAL",
    "A5": "IMAGINARIAS",
    "B00": "AUSENCIA JUSTIFICADA POR ENFERMEDAD QUE NO DA LUGAR A IT",
    "B01": "MOTIVO MÉDICO: BAJA CON PARTE IT",
    "B01v": "VACUNACION COVID19",
    "B02": "MOTIVO MÉDICO: AVISA ENFERMO",
    "B03": "MOTIVO MÉDICO: ASISTE PERO NO PRESTA SERVICIO OPERATIVO",
    "B04": "SALIDA DE FRECUENCIA: EMBARAZO SEMANA 35",
    "B05": "CIMA: ACUDIR A REVISIÓN",
    "B06": "BAJA CIMA",
    "B07": "AUSENCIA CERTIFICADO CIMA",
    "B09": "PERMISOS DE CONVENIO",
    "B10": "LICENCIAS MATERNIDAD/PATERNIDAD/OTRAS",
    "B11": "REDUCCIÓN POR GUARDA LEGAL, POR CUIDADO DE FAMILIAR",
    "B12": "SUSPENSION DE EMPLEO POR CAUSAS DISCIPLINARIAS",
    "B13": "PÉRDIDA DE VALIDEZ DE UNIDAD POR ESTAR SIN CONTROLAR MÁS TIEMPO DEL ESTABLECIDO",  # noqa: E501
    "B14": "ACTIVIDAD SINDICAL",
    "C01": "INSTRUCTOR IMPARTIENDO FORMACIÓN TEÓRICA",
    "C02": "INSTRUCTOR EN SIMULADORES O SIENDO EVALUADO",
    "C03": "INSTRUIDO EN TEORÍA (PRE OJT)",
    "C04": "INSTRUIDO EN SIMULADOR (PRE OJT)",
    "C05": "EVALUADOR DE COMPETENCIA OPERACIONAL",
    "C06": "EVALUADOR DEL INSTRUCTOR OJT O SIENDO EVALUADO",
    "C07": "EVALUADOR DEL EVALUADOR",
    "CS1": "Desprogramación por Comisión de Servicio",
    "CS2": "Comisión de Servicio carácter Sindical",
    "CS3": "Compensación por días libres afectados por Comisión de Servicio",
    "CS4": "Compensación por días libres afectados por CS actividad sindical",
    "EX": "EXCEDENCIA",
    "FC03": "FORMACION ON LINE CONTINUA - INSTRUYENDO",
    "FCO1": "FORMACION TEORIA FC - INSTRUYENDO",
    "FCO2": "FORMACION SIMULADOR DE FC - INSTRUYENDO",
    "FCP1": "INSTRUYENDO EN CARRERA PROFESIONAL",
    "FCP2": "INSTRUYENDO EN CARRERA PROFESIONAL - ON LINE",
    "FCP3": "FORMACIÓN CARRERA PROFESIONAL INSTRUCTOR EN SIMULADOR",
    "FCP4": "FORMACION CARRERA PROFESIONAL EVALUADOR EN SIMULADOR",
    "BD1": "Desprogramación por reunión",
    "BD2": "Desprogramación por Asuntos Propios",
    "BD3": "Desprogramación por Formación",
    "BD4": "Desprogramación por Comisión de Servicio",
    "BD5": "Desprogramación por Tráfico",
    "BDZ": "Desprogramación por Zulú",
    "BDHE": "DESPROGRAMACION POR HE A COMPENSAR",
    "BDHEFM": "DESPROGRAMACION POR HEFM A COMPENSAR",
    "LP": "LICENCIA DE ASUNTOS PROPIOS",
    "P": "ASUNTOS PROPIOS CONVENIO CONTROL",
    "PJS": "ASUNTO PROPIO 12H",
    "PICGA": "ASUNTOS PROPIOS CONVENIO GRUPO AENA",
    "APANT": "ASUNTOS PROPIOS AÑO ANTERIOR CONVENIO GRUPO AENA",
    "OTROS": "OTROS CONVENIO GRUPO AENA",
    "V": "VACACIONES (anuales, del año anterior)",
    "Va": "VACACION DE ANTIGÜEDAD",
    "JM": "JORNADA MIXTA",
    "MSM": "MAÑANA SIMULADOR",
    "TSM": "TARDE SIMULADOR",
    "ME": "MAÑANA OFICINA TÉCNICA",
    "TE": "TARDE OFICINA TÉCNICA",
    "MR": "MAÑANA REUNION",
    "TR": "TARDE REUNION",
    "FORM": "FORMACION NO REALIZADA",
}

ATC_ROLES = {"TS", "IS", "TI", "INS", "PTD", "CON", "SUP", "N/A"}


def is_admin(email: str) -> bool:
    """Check if the user is an admin.

    Checks the is_admin column in Users.
    If no users have the is_admin flag set, the first user to log in becomes the admin.

    """
    user = User.query.filter_by(email=email).first()
    if user:
        # The user was found
        return user.is_admin

    # User is not an admin. Check whether anyone is an admin.
    return not User.query.filter_by(is_admin=True).first()
