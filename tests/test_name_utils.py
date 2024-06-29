"""Test cases for the name_utils module."""

from __future__ import annotations

import pytest
from atcapp.name_utils import capitaliza_nombre, parse_name, to_no_accents


@pytest.mark.parametrize(
    ("name", "expected_nombre", "expected_apellidos"),
    [
        ("CASTILLO PINTO JAIME", "JAIME", "CASTILLO PINTO"),
        (
            "DE ANDRES GONZALEZ CANO IRENE ENRIQUETA",
            "IRENE ENRIQUETA",
            "DE ANDRES GONZALEZ CANO",
        ),
        ("DE LA MARTA PRADA PAULA", "PAULA", "DE LA MARTA PRADA"),
        (
            "MOUTINHO DA SILVA FERREIRA DE FREITAS JOAO",
            "JOAO",
            "MOUTINHO DA SILVA FERREIRA DE FREITAS",
        ),
        (
            "GIMENEZ DE ARAGON SERRA MARIA CRISTINA",
            "MARIA CRISTINA",
            "GIMENEZ DE ARAGON SERRA",
        ),
        ("GARCIA RUIZ DE CASTRO CARLOS", "CARLOS", "GARCIA RUIZ DE CASTRO"),
        (
            "MARTINEZ MORALES MARIA VIRGINIA",
            "MARIA VIRGINIA",
            "MARTINEZ MORALES",
        ),
        ("DE ANDRES RICO MARIO", "MARIO", "DE ANDRES RICO"),
        ("DE LA FUENTE GARCIA JUAN", "JUAN", "DE LA FUENTE GARCIA"),
        ("SANCHEZ DE LA TORRE ANA", "ANA", "SANCHEZ DE LA TORRE"),
        ("LA PAZ GARCIA JUAN", "JUAN", "LA PAZ GARCIA"),
        ("DE LOS SANTOS VELEZ-MALAGA MARIA", "MARIA", "DE LOS SANTOS VELEZ-MALAGA"),
        ("DEL RIO NUEVO FERNANDO", "FERNANDO", "DEL RIO NUEVO"),
        ("GARCIA DUQUE DE ESTRADA FERNANDO", "FERNANDO", "GARCIA DUQUE DE ESTRADA"),
        ("PEREZ RUIZ JUAN", "JUAN", "PEREZ RUIZ"),
    ],
)
def test_parse_name(name: str, expected_nombre: str, expected_apellidos: str) -> None:
    """Test the parse_name function."""
    nombre, apellidos = parse_name(name)
    assert nombre == expected_nombre
    assert apellidos == expected_apellidos


@pytest.mark.parametrize(
    ("nombre", "apellidos", "expected_full_name"),
    [
        ("JAIME", "CASTILLO PINTO", "Jaime Castillo Pinto"),
        (
            "MARIA VIRGINIA",
            "MARTINEZ MORALES",
            "Maria Virginia Martínez Morales",
        ),
        ("MARIO", "DE ANDRES RICO", "Mario de Andrés Rico"),
        ("JUAN", "DE LA FUENTE GARCIA", "Juan de la Fuente García"),
        ("ANA", "SANCHEZ DE LA TORRE", "Ana Sánchez de la Torre"),
        ("JUAN", "LA PAZ GARCIA", "Juan La Paz García"),
        ("MARIA", "DE LOS SANTOS", "Maria de los Santos"),
        ("FERNANDO", "DEL RIO", "Fernando del Río"),
        (
            "FERNANDO",
            "GARCIA DUQUE DE ESTRADA",
            "Fernando García Duque de Estrada",
        ),
        ("josé maría", "de la fuente", "José María de la Fuente"),
    ],
)
def test_capitaliza_nombre(
    nombre: str,
    apellidos: str,
    expected_full_name: str,
) -> None:
    """Test the capitaliza_nombre function."""
    nombre, apellidos = capitaliza_nombre(nombre, apellidos)
    assert to_no_accents(f"{nombre} {apellidos}") == to_no_accents(expected_full_name)
