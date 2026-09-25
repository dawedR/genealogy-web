import sys
import time

from gedcom.parser import Parser
from gedcom.element.individual import IndividualElement
from gedcom.element.family import FamilyElement


def main(path: str) -> None:
    start = time.perf_counter()

    parser = Parser()
    parser.parse_file(path)

    root = parser.get_root_child_elements()

    individuals = [
        element
        for element in root
        if isinstance(element, IndividualElement)
    ]

    families = [
        element
        for element in root
        if isinstance(element, FamilyElement)
    ]

    elapsed = time.perf_counter() - start

    print(f"Fichier   : {path}")
    print(f"Temps     : {elapsed:.4f} s")
    print(f"Individus : {len(individuals)}")
    print(f"Familles  : {len(families)}")

    print()
    print("=== Premiers individus ===")

    for person in individuals[:10]:
        print()
        print("Pointer :", person.get_pointer())
        print("Name    :", person.get_name())
        print("Gender  :", person.get_gender())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {sys.argv[0]} fichier.ged")

    main(sys.argv[1])
