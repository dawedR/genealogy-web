import sys

from gedcom.parser import Parser
from gedcom.element.individual import IndividualElement


def main(path: str) -> None:
    parser = Parser()
    parser.parse_file(path)

    individuals = [
        element
        for element in parser.get_root_child_elements()
        if isinstance(element, IndividualElement)
    ]

    person = individuals[0]

    print("=== PERSONNE ===")
    print("Pointer :", person.get_pointer())
    print("Name    :", person.get_name())
    print()

    print("=== ENFANTS DIRECTS ===")

    for child in person.get_child_elements():
        print(
            "tag     =", repr(child.get_tag()),
            "| value =", repr(child.get_value()),
            "| type  =", type(child).__name__,
        )

        for sub in child.get_child_elements():
            print(
                "   tag     =", repr(sub.get_tag()),
                "| value =", repr(sub.get_value()),
                "| type  =", type(sub).__name__,
            )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {sys.argv[0]} fichier.ged")

    main(sys.argv[1])
